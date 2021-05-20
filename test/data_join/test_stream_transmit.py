import json
import math
import os
import threading
import typing
import unittest

from tensorflow import gfile

import fedlearner.common.transmitter_service_pb2 as transmitter_pb
from fedlearner.common.db_client import DBClient
from fedlearner.data_join.transmitter.components import Sender, Receiver
from fedlearner.data_join.transmitter.transmitter import Transmitter
from fedlearner.data_join.transmitter.utils import IDX

FILE_NUM = 500
FILE_LEN = 100
SEND_ROW_NUM = 480


def _get_next_idx(start_idx: IDX,
                  row_num: int,
                  file_len: int,
                  file_num: int):
    remain_rows = row_num - file_len + start_idx.row_idx
    next_file = start_idx.file_idx + math.ceil(remain_rows / FILE_LEN)
    if next_file >= file_num:
        next_file = file_num - 1
        next_row = file_len
    else:
        if remain_rows <= 0:
            next_row = start_idx.row_idx + row_num
        else:
            next_row = (remain_rows - 1) % FILE_LEN + 1
    return IDX(next_file, next_row)


def _ground_truth_payload(start_idx: IDX,
                          row_num: int,
                          file_len: int,
                          file_num: int):
    res = ''
    current_idx = start_idx
    while current_idx.file_idx < file_num - 1 or current_idx.row_idx < file_len:
        next_idx = _get_next_idx(current_idx, row_num, file_len, file_num)
        res += '{}_{}-{}_{}'.format(current_idx.file_idx,
                                    current_idx.row_idx,
                                    next_idx.file_idx,
                                    next_idx.row_idx)
        current_idx = next_idx
    return res


class TestSender(Sender):
    def __init__(self,
                 output_path: str,
                 meta_path: str,
                 send_row_num: int,
                 file_paths: typing.List[str],
                 root_path: str = None,
                 pending_len: int = 10):
        self._output_path = output_path
        super().__init__(meta_path, send_row_num, file_paths,
                         root_path, pending_len)

    def _send_process(self,
                      root_path: str,
                      files: typing.List[str],
                      start_idx: IDX,
                      row_num: int) -> (bytes, IDX, bool):
        end_idx = _get_next_idx(start_idx, row_num, FILE_LEN, len(files))
        payload = '{}_{}-{}_{}'.format(start_idx.file_idx,
                                       start_idx.row_idx,
                                       end_idx.file_idx,
                                       end_idx.row_idx)
        send_ = os.path.join(self._output_path, 'send.txt')
        with gfile.GFile(send_, 'a') as f:
            f.write(payload)
        return payload.encode(), end_idx, end_idx.row_idx == FILE_LEN

    def _resp_process(self,
                      resp: transmitter_pb.Response,
                      current_idx: IDX) -> IDX:
        start_idx = IDX(resp.start_file_idx, resp.start_row_idx)
        end_idx = IDX(resp.end_file_idx, resp.end_row_idx)
        if end_idx <= current_idx or start_idx > current_idx:
            return None
        resp_ = os.path.join(self._output_path, 'resp.txt')
        with gfile.GFile(resp_, 'a') as f:
            f.write('{}_{}-{}_{}'.format(current_idx.file_idx,
                                         current_idx.row_idx,
                                         end_idx.file_idx,
                                         end_idx.row_idx))
        return end_idx


class TestReceiver(Receiver):
    def _recv_process(self,
                      req: transmitter_pb.Request,
                      current_idx: IDX) -> (bytes, IDX):
        start_idx = IDX(req.start_file_idx, req.start_row_idx)
        end_idx = IDX(req.end_file_idx, req.end_row_idx)
        if end_idx <= current_idx or start_idx > current_idx:
            return req.payload, None
        recv_ = os.path.join(self._output_path, 'recv.txt')
        with gfile.GFile(recv_, 'a') as f:
            f.write('{}_{}-{}_{}'.format(current_idx.file_idx,
                                         current_idx.row_idx,
                                         end_idx.file_idx,
                                         end_idx.row_idx))
        return req.payload, end_idx


class TestStreamTransmit(unittest.TestCase):
    def setUp(self) -> None:
        self.file_paths = [str(i) for i in range(FILE_NUM)]
        self._test_root = './test_stream_transmit'
        os.environ['STORAGE_ROOT_PATH'] = self._test_root
        self._db_client = DBClient('dfs')
        self._mgr1_path = os.path.join(self._test_root, '1')
        self._mgr2_path = os.path.join(self._test_root, '2')
        if gfile.Exists(self._test_root):
            gfile.DeleteRecursively(self._test_root)
        gfile.MakeDirs(self._mgr1_path)
        gfile.MakeDirs(self._mgr2_path)

    def _transmit(self):
        self._manager1 = Transmitter(
            listen_port=10086,
            remote_address='localhost:10010',
            receiver=TestReceiver(meta_path='1',
                                  output_path=self._mgr1_path),
            sender=TestSender(output_path=self._mgr1_path,
                              meta_path='1',
                              send_row_num=SEND_ROW_NUM,
                              file_paths=self.file_paths,
                              root_path=self._test_root)
        )
        self._manager2 = Transmitter(
            listen_port=10010,
            remote_address='localhost:10086',
            receiver=TestReceiver(meta_path='2',
                                  output_path=self._mgr2_path),
            sender=TestSender(output_path=self._mgr2_path,
                              meta_path='2',
                              send_row_num=SEND_ROW_NUM,
                              file_paths=self.file_paths,
                              root_path=self._test_root)
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
        recv1_meta = json.loads(self._db_client.get_data(
            self._manager1._receiver._meta_path))
        recv2_meta = json.loads(self._db_client.get_data(
            self._manager2._receiver._meta_path))
        send1_meta = json.loads(self._db_client.get_data(
            self._manager1._sender._meta_path))
        send2_meta = json.loads(self._db_client.get_data(
            self._manager2._sender._meta_path))
        del recv1_meta['output_path']
        del recv2_meta['output_path']
        del send1_meta['root']
        del send2_meta['root']
        return send1_meta, send2_meta, recv1_meta, recv2_meta

    def _meta_assert(self, send1_meta, send2_meta, recv1_meta, recv2_meta):
        self.assertEqual(send1_meta, {'file_idx': len(self.file_paths) - 1,
                                      'row_idx': FILE_LEN,
                                      'files': self.file_paths,
                                      'finished': True})
        self.assertEqual(recv1_meta, recv2_meta)
        self.assertEqual(send1_meta, send2_meta)
        self.assertEqual(send1_meta['file_idx'], recv1_meta['file_idx'])
        self.assertEqual(send1_meta['row_idx'], recv1_meta['row_idx'])

    def test_transmit(self):
        send1_meta, send2_meta, recv1_meta, recv2_meta = self._transmit()
        self._meta_assert(send1_meta, send2_meta, recv1_meta, recv2_meta)

        expected_content = _ground_truth_payload(IDX(0, 0), SEND_ROW_NUM,
                                                 FILE_LEN, FILE_NUM)
        for file in gfile.ListDirectory(self._mgr1_path):
            if file.endswith('txt'):
                with gfile.GFile(os.path.join(self._mgr1_path, file), 'r') as f:
                    self.assertEqual(f.read(), expected_content)
        for file in gfile.ListDirectory(self._mgr2_path):
            if file.endswith('txt'):
                with gfile.GFile(os.path.join(self._mgr2_path, file), 'r') as f:
                    self.assertEqual(f.read(), expected_content)

    def test_resume(self):
        send_meta = {'file_idx': 40,
                     'row_idx': 60,
                     'files': self.file_paths,
                     'finished': False,
                     'root': self._test_root}
        # behind send
        recv1_meta = {'file_idx': 20,
                      'row_idx': 70,
                      'finished': False,
                      'output_path': self._mgr1_path}
        # in front of send
        recv2_meta = {'file_idx': 60,
                      'row_idx': 80,
                      'finished': False,
                      'output_path': self._mgr2_path}
        self._db_client.set_data('1/send', json.dumps(send_meta).encode())
        self._db_client.set_data('2/send', json.dumps(send_meta).encode())
        self._db_client.set_data('1/recv', json.dumps(recv1_meta).encode())
        self._db_client.set_data('2/recv', json.dumps(recv2_meta).encode())
        send1_meta, send2_meta, recv1_meta, recv2_meta = self._transmit()
        self._meta_assert(send1_meta, send2_meta, recv1_meta, recv2_meta)
        # recv1 has a staler meta than send2
        recv1_expected = _ground_truth_payload(IDX(20, 70), SEND_ROW_NUM,
                                               FILE_LEN, FILE_NUM)
        # send1 has a staler meta than recv2
        send1_expected = _ground_truth_payload(IDX(40, 60), SEND_ROW_NUM,
                                               FILE_LEN, FILE_NUM)
        # send2 need to send from recv1's initial meta
        send2_expected = recv1_expected

        recv2_dup_row = (60 - 40) * FILE_LEN + (80 - 60)
        recv2_remain_row = recv2_dup_row % SEND_ROW_NUM
        recv2_overflow = SEND_ROW_NUM - recv2_remain_row
        # from here it receives full request without duplicates
        recv2_start = _get_next_idx(IDX(60, 80), recv2_overflow,
                                    FILE_LEN, FILE_NUM)
        recv2_expected = _ground_truth_payload(recv2_start, SEND_ROW_NUM,
                                               FILE_LEN, FILE_NUM)
        recv2_expected = '{}_{}-{}_{}'.format(60, 80,
                                              recv2_start.file_idx,
                                              recv2_start.row_idx) \
                         + recv2_expected

        with open(os.path.join(self._mgr1_path, 'send.txt'), 'r') as f:
            self.assertEqual(f.read(), send1_expected)
        with open(os.path.join(self._mgr1_path, 'recv.txt'), 'r') as f:
            self.assertEqual(f.read(), recv1_expected)
        with open(os.path.join(self._mgr2_path, 'send.txt'), 'r') as f:
            self.assertEqual(f.read(), send2_expected)
        with open(os.path.join(self._mgr2_path, 'recv.txt'), 'r') as f:
            self.assertEqual(f.read(), recv2_expected)

    def tearDown(self) -> None:
        gfile.DeleteRecursively(self._test_root)


if __name__ == '__main__':
    unittest.main()
