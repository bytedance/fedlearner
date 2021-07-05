import os
from random import randint
import threading
import typing
import unittest
import math

import pyarrow as pa
import pyarrow.parquet as pq
from tensorflow import gfile

import fedlearner.common.common_pb2 as common_pb
import fedlearner.common.private_set_union_pb2 as psu_pb
import fedlearner.common.transmitter_service_pb2 as tsmt_pb
from fedlearner.data_join.private_set_union.data_union import SparkDataUnion
from fedlearner.data_join.private_set_union.data_reload import SparkDataReload
from fedlearner.data_join.private_set_union.keys import DHKeys
from fedlearner.data_join.private_set_union.utils import E2, E3, E4, Paths
from fedlearner.data_join.private_set_union import parquet_utils as pqu
from fedlearner.data_join.private_set_union.spark_utils import Keys

NUM_L_JOBS = 3
NUM_L_FILES = 3
NUM_R_JOBS = 2
NUM_R_FILES = 7
NUM_R_DIFF = 200

NUM_ROWS = 50
NUM_L = int(NUM_L_JOBS * NUM_L_FILES * NUM_ROWS)
NUM_R = int(NUM_R_JOBS * NUM_R_FILES * NUM_ROWS)
NUM_L_DIFF = max(0, math.ceil(NUM_R - NUM_L + NUM_R_DIFF))
NUM_L_ROW_PER_JOB = int(NUM_L_FILES * NUM_ROWS)
PART_SIZE = 60


def write_table(where: str,
                table: dict,
                schema: pa.Schema):
    pqu.make_dirs_if_not_exists(where)
    writer = pq.ParquetWriter(where, schema, flavor='spark')
    writer.write_table(pa.Table.from_pydict(mapping=table, schema=schema))
    writer.close()


class Addr:
    w1r = 10010  # worker1_remote
    w2r = 10086


class TestPSUSpark(unittest.TestCase):
    def setUp(self) -> None:
        self._test_root = './test_psu_spark'
        os.environ['STORAGE_ROOT_PATH'] = self._test_root
        # schema for union job
        union_sch = pa.schema([pa.field(E2, pa.string())])
        self._union_l_dir = os.path.join(self._test_root, 'l_u')
        self._union_r_dir = os.path.join(self._test_root, 'r_u')
        self._union_l_out = os.path.join(self._test_root, 'l_u_out')
        self._union_r_out = os.path.join(self._test_root, 'r_u_out')
        self._reload_dir = os.path.join(self._test_root, 'reload')
        self._reload_data_dir = os.path.join(self._test_root, 'reload', 'data')
        self._reload_e4_dir = os.path.join(self._test_root, 'reload', E4)

        # data for union
        for side, jobs, files in zip(('l', 'r'),
                                     (NUM_L_JOBS, NUM_R_JOBS),
                                     (NUM_L_FILES, NUM_R_FILES)):
            e2_start = 10000
            for i in range(jobs):
                for j in range(files):
                    if side == 'l':
                        table = {
                            E2: [str(i) for i in
                                 range(e2_start, e2_start + NUM_ROWS)]
                        }
                        path = os.path.join(self._union_l_dir,
                                            str(i), str(j) + '.parquet')
                    else:
                        table = {
                            E2: [str(i) for i in
                                 range(e2_start + NUM_R_DIFF,
                                       e2_start + NUM_ROWS + NUM_R_DIFF)]
                        }
                        path = os.path.join(self._union_r_dir,
                                            str(i), str(j) + '.parquet')
                    write_table(path, table, union_sch)
                    e2_start += NUM_ROWS

        # schemas for reload job
        data_sch = pa.schema([pa.field('x', pa.string()),
                              pa.field('_index', pa.int64()),
                              pa.field('_job_id', pa.int64())])
        e4_sch = pa.schema([pa.field(E4, pa.string()),
                            pa.field('_index', pa.int64()),
                            pa.field('_job_id', pa.int64())])
        diff_sch = pa.schema([pa.field(E4, pa.string())])
        # data for reload
        for i in range(NUM_L_JOBS):
            for j in range(NUM_L_FILES):
                # use `x` to identify if `E4` is correct
                data_table = {
                    'x': [str(i) for i in
                          range(i * NUM_L_ROW_PER_JOB + j * NUM_ROWS,
                                i * NUM_L_ROW_PER_JOB + (j + 1) * NUM_ROWS)],
                    '_index': list(range(j * NUM_ROWS, (j + 1) * NUM_ROWS)),
                    '_job_id': [i] * NUM_ROWS
                }
                e4_table = {
                    E4: [str(i) for i in
                         range(i * NUM_L_ROW_PER_JOB + j * NUM_ROWS,
                               i * NUM_L_ROW_PER_JOB + (j + 1) * NUM_ROWS)],
                    '_index': list(range(j * NUM_ROWS, (j + 1) * NUM_ROWS)),
                    '_job_id': [i] * NUM_ROWS
                }
                data_path = os.path.join(self._reload_data_dir,
                                         str(i),
                                         str(j) + '.parquet')
                e4_path = os.path.join(self._reload_e4_dir,
                                       str(i),
                                       str(j) + '.parquet')
                write_table(data_path, data_table, data_sch)
                write_table(e4_path, e4_table, e4_sch)

        diff_small = {E4: [str(i) for i in range(NUM_L, NUM_L + NUM_L // 3)]}
        diff_big = {E4: [str(i) for i in range(NUM_L, NUM_L + int(NUM_L * 2))]}
        self._diff_small_dir = os.path.join(self._reload_dir,
                                            'diff', 'small', '0.parquet')
        self._diff_big_dir = os.path.join(self._reload_dir,
                                          'diff', 'big', '0.parquet')
        write_table(self._diff_small_dir, diff_small, diff_sch)
        write_table(self._diff_big_dir, diff_big, diff_sch)

        self._keys = DHKeys(psu_pb.KeyInfo(type=psu_pb.DH,
                                           path=Paths.encode_keys_path('DH')))

    def test_data_union(self):
        cfg = {Keys.left_dir: self._union_l_dir,
               Keys.right_dir: self._union_r_dir,
               Keys.l_diff_output_dir: self._union_l_out,
               Keys.r_diff_output_dir: self._union_r_out,
               Keys.partition_size: PART_SIZE,
               Keys.partition_num: None,
               Keys.encryption_key_type: 'DH',
               Keys.encryption_key_path: Paths.encode_keys_path('DH')}
        union_job = SparkDataUnion(cfg)
        union_job.run()
        union_job.stop()

        l_original_p = [
            os.path.join(self._union_l_dir, job, f)
            for job in gfile.ListDirectory(self._union_l_dir)
            for f in gfile.ListDirectory(os.path.join(self._union_l_dir, job))
        ]
        r_original_p = [
            os.path.join(self._union_r_dir, job, f)
            for job in gfile.ListDirectory(self._union_r_dir)
            for f in gfile.ListDirectory(os.path.join(self._union_r_dir, job))
        ]
        l_diff_paths = [os.path.join(self._union_l_out, f)
                        for f in gfile.ListDirectory(self._union_l_out)
                        if f.endswith('.parquet')]
        r_diff_paths = [os.path.join(self._union_r_out, f)
                        for f in gfile.ListDirectory(self._union_r_out)
                        if f.endswith('.parquet')]
        self.assertEqual(math.ceil(NUM_R_DIFF / PART_SIZE), len(r_diff_paths))
        self.assertEqual(math.ceil(NUM_L_DIFF / PART_SIZE), len(l_diff_paths))
        l_diff = set(pq.ParquetDataset(l_diff_paths).read().to_pydict()[E2])
        r_diff = set(pq.ParquetDataset(r_diff_paths).read().to_pydict()[E3])
        self.assertEqual(NUM_L_DIFF, len(l_diff))
        self.assertEqual(NUM_R_DIFF, len(r_diff))
        l_original = set(pq.ParquetDataset(l_original_p).read().to_pydict()[E2])
        r_original = set(pq.ParquetDataset(r_original_p).read().to_pydict()[E2])
        l_diff_ = r_original - l_original
        r_diff_ = set(self._keys.encode(self._keys.encrypt_2(
            self._keys.decode(i))) for i in l_original - r_original)
        self.assertEqual(l_diff_, l_diff)
        self.assertEqual(r_diff_, r_diff)

    def test_data_reload(self):
        out_small = os.path.join(self._reload_dir, 'out_small')
        out_big = os.path.join(self._reload_dir, 'out_big')
        cfg = {Keys.e4_dir: self._reload_e4_dir,
               Keys.data_dir: self._reload_data_dir,
               Keys.diff_dir: self._diff_small_dir,
               Keys.output_path: out_small,
               Keys.partition_size: PART_SIZE,
               Keys.partition_num: None}
        reload_job = SparkDataReload(cfg)
        reload_job.run()
        reload_job.stop()

        cfg[Keys.diff_dir] = self._diff_big_dir
        cfg[Keys.output_path] = out_big
        reload_job = SparkDataReload(cfg)
        reload_job.run()
        reload_job.stop()

        small_paths = [os.path.join(out_small, f)
                       for f in gfile.ListDirectory(out_small)
                       if f.endswith('.parquet')]
        big_paths = [os.path.join(out_big, f)
                     for f in gfile.ListDirectory(out_big)
                     if f.endswith('.parquet')]
        small = pq.ParquetDataset(small_paths).read().to_pydict()
        big = pq.ParquetDataset(big_paths).read().to_pydict()
        for d in (small, big):
            for i in range(len(d['x'])):
                if int(d[E4][i]) < NUM_L:
                    # real data
                    self.assertEqual(d[E4][i], d['x'][i])
                else:
                    # fake data
                    self.assertLess(int(d['x'][i]), NUM_L)

    def tearDown(self) -> None:
        if gfile.Exists(self._test_root):
            gfile.DeleteRecursively(self._test_root)


if __name__ == '__main__':
    unittest.main()
