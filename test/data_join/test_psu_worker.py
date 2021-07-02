import os
import random
import threading
import typing
import unittest

import pyarrow as pa
import pyarrow.parquet as pq
from tensorflow import gfile

import fedlearner.common.common_pb2 as common_pb
import fedlearner.common.private_set_union_pb2 as psu_pb
import fedlearner.common.transmitter_service_pb2 as tsmt_pb
from fedlearner.data_join.private_set_union import transmit
from fedlearner.data_join.private_set_union.keys import DHKeys
from fedlearner.data_join.private_set_union.utils import E2, E3, E4, Paths

NUM_JOBS = 3
NUM_FILES = 5
NUM_ROWS = 50
SEND_ROW_NUM = 20


class Addr:
    w1r = 10010  # worker1_remote
    w2r = 10086


class MockMaster:
    def __init__(self,
                 trans_event: threading.Event,
                 file_paths: typing.List[str],
                 phase,
                 keys: DHKeys):
        self._eve = trans_event
        self._file_paths = file_paths
        self._phase = phase
        self._alloc = False
        self._keys = keys

    def GetPhase(self, request):
        return psu_pb.GetPhaseResponse(
            status=common_pb.Status(code=common_pb.STATUS_SUCCESS),
            phase=self._phase)

    def GetKeys(self, request):
        return psu_pb.GetKeysResponse(
            status=common_pb.Status(code=common_pb.STATUS_SUCCESS),
            key_info=self._keys.key_info)

    def AllocateTask(self, request):
        if not self._alloc and self._file_paths:
            self._alloc = True
            return psu_pb.PSUAllocateTaskResponse(
                status=common_pb.Status(code=common_pb.STATUS_SUCCESS),
                file_info=[tsmt_pb.FileInfo(file_path=self._file_paths[i],
                                            idx=i)
                           for i in range(len(self._file_paths))]
            )
        self._eve.set()
        return psu_pb.PSUAllocateTaskResponse(
            status=common_pb.Status(code=common_pb.STATUS_NO_MORE_DATA))

    def FinishFiles(self, request):
        return tsmt_pb.FinishFilesResponse(
            status=common_pb.Status(code=common_pb.STATUS_SUCCESS))

    def RecvFinishFiles(self, request):
        return tsmt_pb.FinishFilesResponse(
            status=common_pb.Status(code=common_pb.STATUS_SUCCESS))

    def enter_next_phase(self, phase, file_paths):
        self._phase = phase
        self._file_paths = file_paths
        self._alloc = False


class TestPSUWorker(unittest.TestCase):
    def setUp(self) -> None:
        self._test_root = './test_psu_transmit_worker'
        os.environ['STORAGE_ROOT_PATH'] = self._test_root
        schema = pa.schema([pa.field('x', pa.string()),
                            pa.field(E2, pa.string()),
                            pa.field(E3, pa.string()),
                            pa.field('_index', pa.int64()),
                            pa.field('_job_id', pa.int64())])
        self._file_paths = []
        for i in range(NUM_JOBS):
            for j in range(NUM_FILES):
                # doubly_encrypted is used for sync test
                table = {'x': [str(random.randint(10000, 99999)).encode()
                               for _ in range(NUM_ROWS)],
                         E2: [str(random.randint(10000, 99999)).encode()
                              for _ in range(NUM_ROWS)],
                         E3: [str(random.randint(10000, 99999)).encode()
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
        self._keys = DHKeys(psu_pb.KeyInfo(type=psu_pb.DH,
                                           path=Paths.encode_keys_path('DH')))
        self._eve1 = threading.Event()
        self._master1 = MockMaster(self._eve1, self._file_paths,
                                   psu_pb.PSU_Encrypt, self._keys)
        self._worker1 = transmit.PSUTransmitterWorker(
            role=psu_pb.Left,
            rank_id=1,
            listen_port=Addr.w2r,
            remote_address=f'[::]:{Addr.w1r}',
            master_client=self._master1,
            psu_options=psu_pb.PSUOptions(
                join_key='x'
            ),
            encrypt_options=psu_pb.EncryptOptions(
                batch_size=SEND_ROW_NUM,
                send_queue_len=5,
                recv_queue_len=5,
                resp_queue_len=5
            ),
            sync_options=psu_pb.SyncOptions(
                batch_size=SEND_ROW_NUM,
                send_queue_len=5,
                recv_queue_len=5,
                resp_queue_len=5,
            ),
            l_diff_options=psu_pb.LDiffOptions(
                batch_size=SEND_ROW_NUM,
                send_queue_len=5,
                recv_queue_len=5,
                resp_queue_len=5
            ),
            r_diff_options=psu_pb.RDiffOptions(
                batch_size=SEND_ROW_NUM,
                send_queue_len=5,
                recv_queue_len=5,
                resp_queue_len=5
            )
        )
        self._eve2 = threading.Event()
        self._master2 = MockMaster(self._eve2, [],
                                   psu_pb.PSU_Encrypt, self._keys)
        self._worker2 = transmit.PSUTransmitterWorker(
            role=psu_pb.Right,
            rank_id=1,
            listen_port=Addr.w1r,
            remote_address=f'[::]:{Addr.w2r}',
            master_client=self._master2,
            psu_options=psu_pb.PSUOptions(
                join_key='x'
            ),
            encrypt_options=psu_pb.EncryptOptions(
                batch_size=SEND_ROW_NUM,
                send_queue_len=5,
                recv_queue_len=5,
                resp_queue_len=5
            ),
            sync_options=psu_pb.SyncOptions(
                batch_size=SEND_ROW_NUM,
                send_queue_len=5,
                recv_queue_len=5,
                resp_queue_len=5,
            ),
            l_diff_options=psu_pb.LDiffOptions(
                batch_size=SEND_ROW_NUM,
                send_queue_len=5,
                recv_queue_len=5,
                resp_queue_len=5
            ),
            r_diff_options=psu_pb.RDiffOptions(
                batch_size=SEND_ROW_NUM,
                send_queue_len=5,
                recv_queue_len=5,
                resp_queue_len=5
            )
        )

    def test_psu_transmit_worker(self):
        th1 = threading.Thread(target=self._worker1.run)
        th2 = threading.Thread(target=self._worker2.run)
        th1.start()
        th2.start()
        self._wait_for_phase(self._eve1)
        self._encrypt_sort_and_compare()
        gfile.DeleteRecursively(Paths.encode_e4_dir())
        gfile.DeleteRecursively(Paths.encode_e2_dir())
        self._eve2.clear()
        self._master1.enter_next_phase(psu_pb.PSU_Sync, [])
        self._master2.enter_next_phase(psu_pb.PSU_Sync, self._file_paths)

        self._wait_for_phase(self._eve2)
        self._sync_sort_and_compare()
        gfile.DeleteRecursively(Paths.encode_e2_dir())
        self._master1.enter_next_phase(psu_pb.PSU_L_Diff, self._file_paths)
        self._master2.enter_next_phase(psu_pb.PSU_L_Diff, [])

        self._wait_for_phase(self._eve1)
        self._l_diff_sort_and_compare()
        gfile.DeleteRecursively(Paths.encode_e4_dir())
        self._master1.enter_next_phase(psu_pb.PSU_R_Diff, self._file_paths)
        self._master2.enter_next_phase(psu_pb.PSU_R_Diff, [])

        self._wait_for_phase(self._eve1)
        self._r_diff_sort_and_compare()
        self._master1.enter_next_phase(psu_pb.PSU_Reload, self._file_paths)
        self._master2.enter_next_phase(psu_pb.PSU_Reload, [])

    @staticmethod
    def _wait_for_phase(event: threading.Event):
        event.wait()
        event.clear()

    def _encrypt_sort_and_compare(self):
        for i in range(NUM_FILES * NUM_JOBS):
            # send1 pairs with recv2, send2 pairs with recv1
            sf = pq \
                .ParquetFile(Paths.encode_e4_file_path(i)) \
                .read(columns=['_index', E4]) \
                .to_pydict()
            rf = pq \
                .ParquetFile(Paths.encode_e2_file_path(i)) \
                .read(columns=[E2]) \
                .to_pydict()
            # d stands for double, q stands for quadruple
            unison = [[i, d.encode(), q.encode()] for i, d, q in
                      zip(sf['_index'], rf[E2], sf[E4])]
            unison.sort(key=lambda x: x[0])
            unison = [[item[1], item[2]] for item in unison]
            original = pq \
                .ParquetFile(self._file_paths[i]) \
                .read(columns=['x']) \
                .to_pydict()['x']

            o1 = [self._keys.encrypt_1(
                self._keys.encrypt_1(self._keys.hash(item)))
                for item in original]
            o1 = [[self._keys.encode(item),  # doubly encrypted
                   self._keys.encode(self._keys.encrypt_2
                                     (self._keys.encrypt_2(item)))]
                  for item in o1]
            self.assertEqual(o1, unison)

    def _sync_sort_and_compare(self):
        for i in range(NUM_JOBS * NUM_FILES):
            fp = Paths.encode_e2_file_path(i)
            rf = sorted(pq
                        .ParquetFile(fp)
                        .read(columns=[E2])
                        .to_pydict()[E2])
            original = sorted(pq
                              .ParquetFile(self._file_paths[i])
                              .read(columns=[E2])
                              .to_pydict()[E2])
            self.assertEqual(rf, original)

    def _l_diff_sort_and_compare(self):
        for i in range(NUM_JOBS * NUM_FILES):
            fp = Paths.encode_e4_file_path(i)
            rf = sorted(pq
                        .ParquetFile(fp)
                        .read(columns=[E4])
                        .to_pydict()[E4])
            original = pq \
                .ParquetFile(self._file_paths[i]) \
                .read(columns=[E2]) \
                .to_pydict()[E2]
            original = sorted(self._keys.encode(self._keys.encrypt_2(
                self._keys.encrypt_2(self._keys.decode(item))
            )).decode() for item in original)
            self.assertEqual(rf, original)

    def _r_diff_sort_and_compare(self):
        for i in range(NUM_JOBS * NUM_FILES):
            fp = Paths.encode_e4_file_path(i)
            rf = sorted(pq
                        .ParquetFile(fp)
                        .read(columns=[E4])
                        .to_pydict()[E4])
            original = pq \
                .ParquetFile(self._file_paths[i]) \
                .read(columns=[E3]) \
                .to_pydict()[E3]
            original = sorted(self._keys.encode(
                self._keys.encrypt_2(self._keys.decode(item))
            ).decode() for item in original)
            self.assertEqual(rf, original)

    def tearDown(self) -> None:
        if gfile.Exists(self._test_root):
            gfile.DeleteRecursively(self._test_root)


if __name__ == '__main__':
    unittest.main()
