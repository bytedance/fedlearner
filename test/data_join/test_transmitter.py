import functools
import os
import typing
import unittest

from tensorflow import gfile

import fedlearner.common.common_pb2 as common_pb
import fedlearner.common.transmitter_service_pb2 as tsmt_pb
import fedlearner.common.transmitter_service_pb2_grpc as tsmt_grpc
from fedlearner.channel import Channel
from fedlearner.data_join.transmitter.components import Sender, Receiver
from fedlearner.data_join.transmitter.transmitter_worker import \
    TransmitterWorker
from fedlearner.data_join.visitors.visitor import Visitor

TASK_NUM = 3
FILE_NUM = 100
ROW_NUM = 200
SEND_ROW_NUM = 70


def _ground_truth_payload():
    res = ''
    file_idx = 0
    for _ in range(TASK_NUM):
        for _ in range(FILE_NUM):
            for r in range(0, ROW_NUM + SEND_ROW_NUM, SEND_ROW_NUM):
                res += f'->{file_idx}_{min(r, ROW_NUM)}'
            file_idx += 1
    return res


class TestVisitor(Visitor):
    def create_iter(self, file_path):
        file_infos = self._file_infos
        file_idx = file_infos[self._file_idx].idx

        def _iter():
            for i in range(0, ROW_NUM + SEND_ROW_NUM, SEND_ROW_NUM):
                yield min(i, ROW_NUM), file_idx, i >= ROW_NUM

        return _iter()


class TestSender(Sender):
    def __init__(self,
                 output_path: str,
                 peer_client: tsmt_grpc.TransmitterWorkerServiceStub,
                 send_queue_len: int = 10,
                 resp_queue_len: int = 10):
        self._output_path = output_path
        self._task_id = 0
        self._visitor = TestVisitor()
        self._batch_idx = 0
        super().__init__(peer_client, send_queue_len, resp_queue_len)

    def _data_iterator(self) \
        -> typing.Iterable[typing.Tuple[bytes, tsmt_pb.BatchInfo]]:
        for batch, f_idx, finished in self._visitor:
            send_payload_path = os.path.join(self._output_path, 'send.txt')
            with gfile.GFile(send_payload_path, 'a') as fp:
                fp.write(f'->{f_idx}_{batch}')
            yield f'->{f_idx}_{batch}'.encode(), \
                  tsmt_pb.BatchInfo(finished=finished,
                                    file_idx=f_idx,
                                    batch_idx=self._batch_idx)
            self._batch_idx += 1

    def _resp_process(self,
                      resp: tsmt_pb.TransmitDataResponse) -> None:
        resp_payload_path = os.path.join(self._output_path, 'resp.txt')
        with gfile.GFile(resp_payload_path, 'a') as f:
            f.write(resp.payload.decode())

    def _request_task_from_master(self):
        if self._task_id < TASK_NUM:
            file_infos = [
                tsmt_pb.FileInfo(file_path=f'{i}', idx=i)
                for i in range(self._task_id * FILE_NUM,
                               (self._task_id + 1) * FILE_NUM)
            ]
            self._visitor.init(file_infos)
            self._task_id += 1
            return common_pb.Status(code=common_pb.STATUS_SUCCESS)
        return common_pb.Status(code=common_pb.STATUS_NO_MORE_DATA)

    def report_peer_file_finish_to_master(self, file_idx: int) \
        -> common_pb.Status:
        peer_fin_file_path = os.path.join(self._output_path, 'peer_fin.fxf')
        with gfile.GFile(peer_fin_file_path, 'a') as f:
            f.write(f'->{file_idx}')
        return common_pb.Status(code=common_pb.STATUS_SUCCESS)


class TestReceiver(Receiver):
    def __init__(self, output_path: str,
                 peer_client: tsmt_grpc.TransmitterWorkerServiceStub,
                 recv_queue_len: int = 10):
        self._output_path = output_path
        super().__init__(peer_client, recv_queue_len)

    def _recv_process(self,
                      req: tsmt_pb.TransmitDataRequest,
                      consecutive: bool) -> (bytes, [typing.Callable, None]):
        def _post_job(payload: bytes, job_output_path: str):
            with gfile.GFile(job_output_path, 'a') as f_:
                f_.write(payload.decode())

        recv_payload_path = os.path.join(self._output_path, 'recv.txt')
        post_output_path = os.path.join(self._output_path, 'post.txt')
        job = None
        if consecutive:
            with gfile.GFile(recv_payload_path, 'a') as f:
                f.write(req.payload.decode())
            job = functools.partial(_post_job, req.payload, post_output_path)
        return req.payload, job


class TestTransmitterWorker(TransmitterWorker):
    def start(self):
        self._sender.start()
        self._receiver.start()

    def wait_for_finish(self):
        self._sender.wait_for_finish()
        self._receiver.wait_for_finish()


class TestStreamTransmit(unittest.TestCase):
    def setUp(self) -> None:
        self._test_root = './test_transmitter'
        os.environ['STORAGE_ROOT_PATH'] = self._test_root
        self._mgr1_path = os.path.join(self._test_root, '1')
        self._mgr2_path = os.path.join(self._test_root, '2')
        if gfile.Exists(self._test_root):
            gfile.DeleteRecursively(self._test_root)
        gfile.MakeDirs(self._mgr1_path)
        gfile.MakeDirs(self._mgr2_path)
        port_1 = 10086
        port_2 = 10010
        self._channel_1 = Channel(f'[::]:{port_1}', f'[::]:{port_2}')
        self._channel_2 = Channel(f'[::]:{port_2}', f'[::]:{port_1}')
        self._channel_1.connect(False)
        self._channel_2.connect(False)
        self._client_1 = tsmt_grpc.TransmitterWorkerServiceStub(self._channel_1)
        self._client_2 = tsmt_grpc.TransmitterWorkerServiceStub(self._channel_2)

    def _transmit(self):
        self._manager1 = TestTransmitterWorker(
            receiver=TestReceiver(output_path=self._mgr1_path,
                                  peer_client=self._client_1),
            sender=TestSender(output_path=self._mgr1_path,
                              peer_client=self._client_1)
        )
        self._manager2 = TestTransmitterWorker(
            receiver=TestReceiver(output_path=self._mgr2_path,
                                  peer_client=self._client_2),
            sender=TestSender(output_path=self._mgr2_path,
                              peer_client=self._client_2)
        )
        tsmt_grpc.add_TransmitterWorkerServiceServicer_to_server(
            self._manager1, self._channel_1
        )
        tsmt_grpc.add_TransmitterWorkerServiceServicer_to_server(
            self._manager2, self._channel_2
        )
        self._manager1.start()
        self._manager2.start()
        self._manager1.wait_for_finish()
        self._manager2.wait_for_finish()

    def test_transmit(self):
        self._transmit()
        expected_payload = _ground_truth_payload()
        expected_files = '->' + '->'.join(map(str, range(TASK_NUM * FILE_NUM)))
        for dir_ in (self._mgr1_path, self._mgr2_path):
            for file in gfile.ListDirectory(dir_):
                path = os.path.join(dir_, file)
                if file.endswith('txt'):
                    with gfile.GFile(path, 'r') as f:
                        self.assertEqual(f.read(), expected_payload)
                if file.endswith('fxf'):
                    with gfile.GFile(path, 'r') as f:
                        self.assertEqual(f.read(), expected_files)

    def tearDown(self) -> None:
        gfile.DeleteRecursively(self._test_root)


if __name__ == '__main__':
    unittest.main()
