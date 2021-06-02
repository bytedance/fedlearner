import os
import random
import threading
import typing
import unittest

import pyarrow as pa
import pyarrow.parquet as pq
from tensorflow import gfile

import fedlearner.data_join.private_set_union.parquet_utils as pqu
from fedlearner.data_join.private_set_union.keys import DHKeys
from fedlearner.data_join.private_set_union.parquet_encrypt_components import \
    ParquetEncryptSender, ParquetEncryptReceiver
from fedlearner.data_join.transmitter.transmitter import Transmitter

NUM_JOBS = 3
NUM_FILES = 5
NUM_ROWS = 50
SEND_ROW_NUM = 20


class TestPSUEncryptComponents(unittest.TestCase):
    def setUp(self) -> None:
        self._test_root = './test_psu_encrypt_components'
        os.environ['STORAGE_ROOT_PATH'] = self._test_root
        schema = pa.schema([pa.field('x', pa.string()),
                            pa.field('_index', pa.int64()),
                            pa.field('_job_id', pa.int64())])
        self._keys1 = DHKeys(os.path.join('keys', 'dh1'))
        self._keys2 = DHKeys(os.path.join('keys', 'dh2'))
        self._file_paths = []
        for i in range(NUM_JOBS):
            for j in range(NUM_FILES):
                table = {'x': [str(random.randint(10000, 99999)).encode()
                               for _ in range(NUM_ROWS)],
                         '_index': [k + j * NUM_ROWS for k in range(NUM_ROWS)],
                         '_job_id': [i for _ in range(NUM_ROWS)]}
                file_path = os.path.join(self._test_root,
                                         'sample',
                                         str(i),
                                         str(j) + '.parquet')
                if not os.path.exists(os.path.dirname(file_path)):
                    os.makedirs(os.path.dirname(file_path))
                writer = pq.ParquetWriter(file_path, schema, flavor='spark')
                writer.write_table(pa.Table.from_pydict(mapping=table,
                                                        schema=schema))
                writer.close()
                self._file_paths.append(file_path)

    def test_encrypt_transmit(self):
        self._output_base = os.path.join(self._test_root, 'out')
        self._manager1 = Transmitter(
            listen_port=10086,
            remote_address='localhost:10010',
            receiver=ParquetEncryptReceiver(
                keys=self._keys1,
                meta_path='recv1',
                output_path=os.path.join(self._output_base, 'recv1')),
            sender=ParquetEncryptSender(
                keys=self._keys1,
                output_path=os.path.join(self._output_base, 'send1'),
                meta_path='send1',
                send_row_num=SEND_ROW_NUM,
                file_paths=self._file_paths,
                join_key='x')
        )
        self._manager2 = Transmitter(
            listen_port=10010,
            remote_address='localhost:10086',
            receiver=ParquetEncryptReceiver(
                keys=self._keys2,
                meta_path='recv2',
                output_path=os.path.join(self._output_base, 'recv2')),
            sender=ParquetEncryptSender(
                keys=self._keys2,
                output_path=os.path.join(self._output_base, 'send2'),
                meta_path='send2',
                send_row_num=SEND_ROW_NUM,
                file_paths=self._file_paths,
                join_key='x')
        )
        thread1 = threading.Thread(target=self._manager1.connect)
        thread2 = threading.Thread(target=self._manager2.connect)
        thread1.start()
        thread2.start()
        self._manager1.wait_for_finish()
        self._manager2.wait_for_finish()
        th1_stop = threading.Thread(target=self._manager1.terminate)
        th2_stop = threading.Thread(target=self._manager2.terminate)
        th1_stop.start()
        th2_stop.start()
        th1_stop.join()
        th2_stop.join()
        self._sort_and_compare()

    def _sort_and_compare(self):
        recv1_path = os.path.join(self._output_base, 'recv1')
        recv2_path = os.path.join(self._output_base, 'recv2')
        send1_path = os.path.join(self._output_base, 'send1')
        send2_path = os.path.join(self._output_base, 'send2')
        for i in range(NUM_FILES * NUM_JOBS):
            # send1 pairs with recv2, send2 pairs with recv1
            for s, r in [(send1_path, recv2_path), (send2_path, recv1_path)]:
                sf = pq.ParquetFile(
                    pqu.encode_quadruply_encrypted_file_path(s, i)
                ).read(columns=['_index', 'quadruply_encrypted']).to_pydict()
                rf = pq.ParquetFile(
                    pqu.encode_doubly_encrypted_file_path(r, i)
                ).read(columns=['doubly_encrypted']).to_pydict()
                # d stands for double, q stands for quadruple
                unison = [[i, d.encode(), q.encode()] for i, d, q in
                          zip(sf['_index'],
                              rf['doubly_encrypted'],
                              sf['quadruply_encrypted'])]
                unison.sort(key=lambda x: x[0])
                unison = [[item[1], item[2]] for item in unison]
                original = pq.ParquetFile(
                    self._file_paths[i]).read(columns=['x']).to_pydict()['x']
                self._compare(unison, original)

    def _compare(self,
                 d_q_unison: typing.List[typing.List[bytes]],
                 original: typing.List[bytes]):
        o1 = [
            self._keys2.encrypt_func1(
                self._keys1.encrypt_func1(
                    self._keys1.hash_func(item)))
            for item in original
        ]
        o1 = [[
            item,  # doubly encrypted
            self._keys2.encrypt_func2(
                self._keys1.encrypt_func2(item))  # quadruply encrypted
        ] for item in o1]
        self.assertEqual(o1, d_q_unison)

    def tearDown(self) -> None:
        gfile.DeleteRecursively(os.path.join(self._test_root, 'metadata'))
