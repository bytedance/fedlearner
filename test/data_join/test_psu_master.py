import os
import threading
import unittest

from google.protobuf.empty_pb2 import Empty
from tensorflow import gfile

import fedlearner.common.private_set_union_pb2 as psu_pb
import fedlearner.common.private_set_union_pb2_grpc as psu_grpc
from fedlearner.data_join.private_set_union import transmit
from fedlearner.data_join.private_set_union.keys import DHKeys
from fedlearner.data_join.private_set_union.transmit.psu_transmitter_master \
    import TRANS_FSM
from fedlearner.data_join.private_set_union.utils import Paths
from fedlearner.proxy.channel import make_insecure_channel, ChannelType

NUM_FILES = 50


class Addr:
    r1 = 10010  # worker1_remote
    r2 = 10086
    l1 = 10151
    l2 = 10152


class TestPSUMaster(unittest.TestCase):
    def setUp(self) -> None:
        self._test_root = './test_psu_transmit_master'
        os.environ['STORAGE_ROOT_PATH'] = self._test_root
        self._keys = DHKeys(psu_pb.KeyInfo(type=psu_pb.DH,
                                           path=Paths.encode_keys_path('DH')))
        self._file_paths = [str(i) for i in range(NUM_FILES)]

    def _build_master(self, worker_num, phase):
        self._master1 = transmit.PSUTransmitterMaster(
            remote_listen_port=Addr.r1,
            remote_address=f'[::]:{Addr.r2}',
            local_listen_port=Addr.l1,
            phase=phase,
            key_type='DH',
            file_paths=self._file_paths,
            worker_num=worker_num
        )
        self._master2 = transmit.PSUTransmitterMaster(
            remote_listen_port=Addr.r2,
            remote_address=f'[::]:{Addr.r1}',
            local_listen_port=Addr.l2,
            phase=phase,
            key_type='DH',
            file_paths=self._file_paths,
            worker_num=worker_num
        )
        ch1 = make_insecure_channel(
            f'[::]:{Addr.l1}', ChannelType.INTERNAL,
            options=[('grpc.max_send_message_length', 2 ** 31 - 1),
                     ('grpc.max_receive_message_length', 2 ** 31 - 1)]
        )
        ch2 = make_insecure_channel(
            f'[::]:{Addr.l2}', ChannelType.INTERNAL,
            options=[('grpc.max_send_message_length', 2 ** 31 - 1),
                     ('grpc.max_receive_message_length', 2 ** 31 - 1)]
        )
        self._lc1 = psu_grpc.PSUTransmitterMasterServiceStub(ch1)
        self._lc2 = psu_grpc.PSUTransmitterMasterServiceStub(ch2)

    def _run_master(self):
        self._th1 = threading.Thread(target=self._master1.run)
        self._th2 = threading.Thread(target=self._master2.run)
        self._th1.start()
        self._th2.start()

    def _stop_master(self):
        th1 = threading.Thread(target=self._master1.stop)
        th2 = threading.Thread(target=self._master2.stop)
        th1.start()
        th2.start()

    def test_get(self):
        self._build_master(1, psu_pb.PSU_Encrypt)
        self._run_master()
        res = self._lc1.GetPhase(Empty())
        self.assertEqual(res.phase, psu_pb.PSU_Encrypt)
        res = self._lc1.GetKeys(Empty())
        self.assertEqual(res.key_info, self._keys.key_info)

    def test_allocate_and_finish(self):
        rank_id = 3
        num_workers = 5
        all_files = list(range(rank_id, NUM_FILES, num_workers))
        self._build_master(num_workers, psu_pb.PSU_Encrypt)
        self._run_master()
        res = self._lc1.AllocateTask(
            psu_pb.PSUAllocateTaskRequest(phase=psu_pb.PSU_Encrypt,
                                          rank_id=rank_id))
        self.assertEqual(all_files, list(i.idx for i in res.file_infos))

        finished = list(range(10))
        self._lc1.FinishFiles(psu_pb.PSUFinishFilesRequest(
            phase=psu_pb.PSU_Encrypt, file_idx=finished))
        self.assertEqual([],
                         list(self._master1._local_servicer._meta['finished']))

        self._lc1.RecvFinishFiles(psu_pb.PSUFinishFilesRequest(
            phase=psu_pb.PSU_Encrypt, file_idx=finished[:-1]))
        self.assertEqual(finished[:-1],
                         list(self._master1._local_servicer._meta['finished']))

        self._lc1.FinishFiles(psu_pb.PSUFinishFilesRequest(
            phase=psu_pb.PSU_Encrypt, file_idx=finished))
        self.assertEqual(finished[:-1],
                         list(self._master1._local_servicer._meta['finished']))

        res = self._lc1.AllocateTask(
            psu_pb.PSUAllocateTaskRequest(phase=psu_pb.PSU_Encrypt,
                                          rank_id=rank_id))
        self.assertEqual(set(all_files) - set(finished[:-1]),
                         set(i.idx for i in res.file_infos))

        self._lc1.FinishFiles(psu_pb.PSUFinishFilesRequest(
            phase=psu_pb.PSU_Encrypt, file_idx=all_files))
        self._lc1.RecvFinishFiles(psu_pb.PSUFinishFilesRequest(
            phase=psu_pb.PSU_Encrypt, file_idx=all_files))
        res = self._lc1.AllocateTask(
            psu_pb.PSUAllocateTaskRequest(phase=psu_pb.PSU_Encrypt,
                                          rank_id=rank_id))
        self.assertEqual(0, len(res.file_infos))
        self.assertEqual(set(all_files) | set(finished[:-1]),
                         self._master1._local_servicer._meta['finished'])
        self.assertEqual({rank_id},
                         self._master1._local_servicer._finished_workers)

    def test_encrypt_to_sync_transition(self):
        self._transition(psu_pb.PSU_Encrypt)

    def test_sync_to_l_diff_transition(self):
        self._transition(psu_pb.PSU_Sync)

    def test_l_diff_to_r_diff_transition(self):
        self._transition(psu_pb.PSU_L_Diff)

    def test_r_diff_to_reload_transition(self):
        self._transition(psu_pb.PSU_R_Diff)

    def _transition(self, phase):
        self._build_master(1, phase)
        self._run_master()
        self._finish_all_files(self._lc1)
        self.assertFalse(
            self._master1._local_servicer._transition_ready.is_set())

        self._finish_all_files(self._lc2)
        trans1 = threading.Thread(target=self._master1.wait_to_enter_next_phase,
                                  args=(self._file_paths,))
        trans2 = threading.Thread(target=self._master2.wait_to_enter_next_phase,
                                  args=(self._file_paths,))
        trans1.start()
        trans2.start()
        trans1.join()
        trans2.join()
        self.assertEqual(TRANS_FSM[phase],
                         self._master1._local_servicer._phase)
        self.assertEqual(TRANS_FSM[phase],
                         self._master1._local_servicer._next_phase)
        self.assertEqual({'files': self._file_paths, 'finished': set()},
                         self._master1._local_servicer._meta)

    @staticmethod
    def _finish_all_files(client):
        client.FinishFiles(psu_pb.PSUFinishFilesRequest(
            phase=psu_pb.PSU_Encrypt, file_idx=list(range(NUM_FILES))))
        client.RecvFinishFiles(psu_pb.PSUFinishFilesRequest(
            phase=psu_pb.PSU_Encrypt, file_idx=list(range(NUM_FILES))))
        client.AllocateTask(
            psu_pb.PSUAllocateTaskRequest(phase=psu_pb.PSU_Encrypt,
                                          rank_id=0))

    def tearDown(self) -> None:
        if gfile.Exists(self._test_root):
            gfile.DeleteRecursively(self._test_root)
        self._stop_master()


if __name__ == '__main__':
    unittest.main()
