import os
import typing
import json
import unittest
import threading

from tensorflow import gfile

import fedlearner.common.stream_transmit_pb2 as st_pb
from fedlearner.data_join.stream_transmit.stream_transmit import Sender, \
    Receiver, StreamTransmit
import fedlearner.common.common_pb2 as common_pb


class TestSender(Sender):
    def __init__(self,
                 output_path: str,
                 meta_dir: str,
                 send_row_num: int,
                 file_paths: typing.List[str],
                 root_path: str = None,
                 pending_len: int = 10):
        self._output_path = output_path
        super().__init__(meta_dir, send_row_num, file_paths,
                         root_path, pending_len)

    def _send_process(self,
                      file_path: str,
                      row_index: int,
                      row_num: int) -> (bytes, int, bool):
        actual_num = min(row_num, 100 - row_index)
        payload = '{}'.format(file_path)
        send_ = os.path.join(self._output_path, 'send.txt')
        finished = row_index + actual_num == 100
        if finished:
            with gfile.GFile(send_, 'a') as f:
                f.write(payload)
        return bytes(payload, encoding='utf-8'), \
               actual_num, finished

    def _resp_process(self,
                      resp: st_pb.Response) -> bool:
        resp_ = os.path.join(self._output_path, 'resp.txt')
        if resp.status.code == common_pb.STATUS_FILE_FINISHED or \
                resp.status.code == common_pb.STATUS_DATA_FINISHED:
            with gfile.GFile(resp_, 'a') as f:
                f.write(resp.payload.decode())
        return True


class TestReceiver(Receiver):
    def _process(self,
                 req: st_pb.Request,
                 preceded: bool,
                 duplicated: bool) -> (bytes, bool):
        if not preceded and not duplicated:
            recv_ = os.path.join(self._output_path, 'recv.txt')
            if req.status.code == common_pb.STATUS_FILE_FINISHED or \
                    req.status.code == common_pb.STATUS_DATA_FINISHED:
                with gfile.GFile(recv_, 'a') as f:
                    f.write(req.payload.decode())
        return req.payload, True


class TestStreamTransmit(unittest.TestCase):
    def setUp(self) -> None:
        self.file_paths = [str(i) for i in range(500)]
        self._test_root = './test_stream_transmit'
        self._mgr1_path = os.path.join(self._test_root, '1')
        self._mgr2_path = os.path.join(self._test_root, '2')
        if gfile.Exists(self._test_root):
            gfile.DeleteRecursively(self._test_root)
        gfile.MakeDirs(self._mgr1_path)
        gfile.MakeDirs(self._mgr2_path)
        self._manager1 = StreamTransmit(
            listen_port=10086,
            remote_address='localhost:10010',
            receiver=TestReceiver(meta_dir=self._mgr1_path,
                                  output_path=self._mgr1_path),
            sender=TestSender(output_path=self._mgr1_path,
                              meta_dir=self._mgr1_path,
                              send_row_num=60,
                              file_paths=self.file_paths,
                              root_path=self._test_root)
        )
        self._manager2 = StreamTransmit(
            listen_port=10010,
            remote_address='localhost:10086',
            receiver=TestReceiver(meta_dir=self._mgr2_path,
                                  output_path=self._mgr2_path),
            sender=TestSender(output_path=self._mgr2_path,
                              meta_dir=self._mgr2_path,
                              send_row_num=60,
                              file_paths=self.file_paths,
                              root_path=self._test_root)
        )

    def test_transmit(self):
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
        with gfile.GFile(self._manager1._receiver._meta_path) as f:
            recv1_meta = json.load(f)
        with gfile.GFile(self._manager2._receiver._meta_path) as f:
            recv2_meta = json.load(f)
        with gfile.GFile(self._manager1._sender._meta_path) as f:
            send1_meta = json.load(f)
        with gfile.GFile(self._manager2._sender._meta_path) as f:
            send2_meta = json.load(f)
        del recv1_meta['output_path']
        del recv2_meta['output_path']
        del send1_meta['root']
        del send2_meta['root']
        self.assertEqual(send1_meta, {'file_index': len(self.file_paths),
                                      'row_index': 0,
                                      'files': self.file_paths,
                                      'finished': True})
        self.assertEqual(recv1_meta, recv2_meta)
        self.assertEqual(send1_meta, send2_meta)
        self.assertEqual(send1_meta['file_index'], recv1_meta['file_index'])
        self.assertEqual(send1_meta['row_index'], recv1_meta['row_index'])
        expected_content = ''.join([os.path.join(self._test_root, f)
                                    for f in self.file_paths])
        print(len(expected_content))
        for file in gfile.ListDirectory(self._mgr1_path):
            if file.endswith('txt'):
                with gfile.GFile(os.path.join(self._mgr1_path, file), 'r') as f:
                    self.assertEqual(f.read(), expected_content)
        for file in gfile.ListDirectory(self._mgr2_path):
            if file.endswith('txt'):
                with gfile.GFile(os.path.join(self._mgr2_path, file), 'r') as f:
                    self.assertEqual(f.read(), expected_content)


if __name__ == '__main__':
    unittest.main()
