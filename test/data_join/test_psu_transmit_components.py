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
import fedlearner.common.transmitter_service_pb2_grpc as tsmt_grpc
from fedlearner.channel.channel import Channel
from fedlearner.data_join.private_set_union import transmit
from fedlearner.data_join.private_set_union.keys import DHKeys
from fedlearner.data_join.private_set_union.utils import E2, E3, E4, Paths
from fedlearner.data_join.transmitter.transmitter_worker import \
    TransmitterWorker

NUM_JOBS = 3
NUM_FILES = 5
NUM_ROWS = 50
SEND_ROW_NUM = 20


class Addr:
    w1r = 10010  # worker1_remote
    w2r = 10086


class MockMaster:
    def __init__(self, file_paths: typing.List[str], phase, keys: DHKeys):
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
        if not self._alloc:
            self._alloc = True
            return psu_pb.PSUAllocateTaskResponse(
                status=common_pb.Status(code=common_pb.STATUS_SUCCESS),
                file_info=[tsmt_pb.FileInfo(file_path=self._file_paths[i],
                                            idx=i)
                           for i in range(len(self._file_paths))]
            )
        return psu_pb.PSUAllocateTaskResponse(
            status=common_pb.Status(code=common_pb.STATUS_NO_MORE_DATA))

    def FinishFiles(self, request):
        return tsmt_pb.FinishFilesResponse(
            status=common_pb.Status(code=common_pb.STATUS_SUCCESS))

    def RecvFinishFiles(self, request):
        return tsmt_pb.FinishFilesResponse(
            status=common_pb.Status(code=common_pb.STATUS_SUCCESS))


class TestTransmitterWorker(TransmitterWorker):
    def start(self):
        if self._sender:
            self._sender.start()
        if self._receiver:
            self._receiver.start()

    def wait_for_finish(self):
        if self._sender:
            self._sender.wait_for_finish()
        if self._receiver:
            self._receiver.wait_for_finish()

    def new_sender_receiver(self, sender, receiver):
        self._sender = sender
        self._receiver = receiver


class TestPSUTransmitComponents(unittest.TestCase):
    def setUp(self) -> None:
        self._test_root = './test_psu_transmit_components'
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
        self._ch1 = Channel(f'[::]:{Addr.w1r}', f'[::]:{Addr.w2r}')
        self._ch2 = Channel(f'[::]:{Addr.w2r}', f'[::]:{Addr.w1r}')
        self._ch1.connect(False)
        self._ch2.connect(False)
        self._peer1 = tsmt_grpc.TransmitterWorkerServiceStub(self._ch1)
        self._peer2 = tsmt_grpc.TransmitterWorkerServiceStub(self._ch2)
        self._keys = DHKeys(psu_pb.KeyInfo(type=psu_pb.DH,
                                           path=Paths.encode_keys_path('DH')))
        self._manager1 = TestTransmitterWorker(None, None)
        self._manager2 = TestTransmitterWorker(None, None)
        tsmt_grpc.add_TransmitterWorkerServiceServicer_to_server(self._manager1,
                                                                 self._ch1)
        tsmt_grpc.add_TransmitterWorkerServiceServicer_to_server(self._manager2,
                                                                 self._ch2)

    def _build_master(self, phase):
        self._master1 = MockMaster(self._file_paths, phase, self._keys)
        self._master2 = MockMaster(self._file_paths, phase, self._keys)

    def _build_and_run(self,
                       sender1,
                       sender2,
                       receiver1,
                       receiver2):
        self._manager1.new_sender_receiver(sender1, receiver1)
        self._manager2.new_sender_receiver(sender2, receiver2)
        thread1 = threading.Thread(target=self._manager1.start)
        thread2 = threading.Thread(target=self._manager2.start)
        thread1.start()
        thread2.start()
        self._manager1.wait_for_finish()
        self._manager2.wait_for_finish()
        thread1.join()
        thread2.join()

    def test_encrypt_transmit(self):
        self._build_master(psu_pb.PSU_Encrypt)
        self._build_and_run(
            sender1=transmit.ParquetEncryptSender(
                rank_id=1,
                batch_size=SEND_ROW_NUM,
                join_key='x',
                master_client=self._master1,
                peer_client=self._peer1
            ),
            receiver1=None,
            sender2=None,
            receiver2=transmit.ParquetEncryptReceiver(
                peer_client=self._peer2,
                master_client=self._master2
            )
        )
        self._encrypt_sort_and_compare()

    def test_sync_transmit(self):
        self._build_master(psu_pb.PSU_Sync)
        self._build_and_run(
            sender1=transmit.ParquetSyncSender(
                rank_id=1,
                sync_columns=[E2],
                need_shuffle=True,
                master_client=self._master1,
                peer_client=self._peer1,
                batch_size=SEND_ROW_NUM
            ),
            receiver1=None,
            sender2=None,
            receiver2=transmit.ParquetSyncReceiver(
                peer_client=self._peer2,
            )
        )
        self._sync_sort_and_compare()

    def test_diff_transmit(self):
        self._build_master(psu_pb.PSU_L_Diff)
        self._build_and_run(
            sender1=transmit.ParquetSetDiffSender(
                rank_id=1,
                mode=transmit.SetDiffMode.L,
                peer_client=self._peer1,
                master_client=self._master1,
                batch_size=SEND_ROW_NUM
            ),
            receiver1=None,
            sender2=None,
            receiver2=transmit.ParquetSetDiffReceiver(
                mode=transmit.SetDiffMode.L,
                peer_client=self._peer2,
                master_client=self._master2
            )
        )
        self._l_diff_sort_and_compare()

        self._build_master(psu_pb.PSU_R_Diff)
        self._build_and_run(
            sender1=transmit.ParquetSetDiffSender(
                rank_id=1,
                mode=transmit.SetDiffMode.R,
                peer_client=self._peer1,
                master_client=self._master1,
                batch_size=SEND_ROW_NUM
            ),
            receiver1=None,
            sender2=None,
            receiver2=transmit.ParquetSetDiffReceiver(
                mode=transmit.SetDiffMode.R,
                peer_client=self._peer2,
                master_client=self._master2
            )
        )

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
        self._ch1.close(False)
        self._ch2.close()


if __name__ == '__main__':
    unittest.main()
