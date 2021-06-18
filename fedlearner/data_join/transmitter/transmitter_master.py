import copy
import json
import threading
import typing

import fedlearner.common.common_pb2 as common_pb
import fedlearner.common.transmitter_service_pb2 as tsmt_pb
import fedlearner.common.transmitter_service_pb2_grpc as tsmt_grpc
from fedlearner.common.db_client import DBClient


class TransmitterMaster(tsmt_grpc.TransmitterMasterServiceServicer):
    def __init__(self,
                 file_paths: typing.List[str],
                 worker_num: int,
                 meta_path: str):
        self._file_paths = file_paths
        self._worker_num = worker_num
        self._meta_path = meta_path
        self._db_client = DBClient('dfs')
        self._condition = threading.Condition()
        self._meta = self._get_meta()
        self._stopped = False
        super().__init__()

    def AllocateTask(self, request, context):
        rid = request.rank_id
        alloc_files = []
        alloc_idx = []
        with self._condition:
            for i in range(rid, len(self._file_paths), self._worker_num):
                if i in self._meta['finished']:
                    continue
                alloc_files.append(self._file_paths[i])
                alloc_idx.append(i)
        return tsmt_pb.AllocateTaskResponse(
            status=common_pb.STATUS_SUCCESS,
            files=alloc_files,
            file_idx=alloc_idx)

    def FinishFiles(self, request, context):
        with self._condition:
            self._meta['finished'].update(request.files)
            self._dump_meta(self._meta)
        return tsmt_pb.FinishFilesResponse(
            status=common_pb.STATUS_SUCCESS)

    def _get_meta(self) -> dict:
        meta = self._read_meta()
        if meta:
            diff = set(self._file_paths) - set(meta['files'])
            if diff:
                for f in self._file_paths:
                    if f in diff:
                        meta['files'].append(f)
        else:
            meta = {
                'files': self._file_paths,
                'finished': set()
            }
        self._dump_meta(meta)
        return meta

    def _read_meta(self) -> [None, dict]:
        meta_str = self._db_client.get_data(self._meta_path)
        if meta_str:
            meta = self.decode_meta(meta_str)
        else:
            meta = None
        return meta

    def _dump_meta(self, meta: dict) -> None:
        assert meta
        with self._condition:
            self._db_client.set_data(self._meta_path, self.encode_meta(meta))

    @staticmethod
    def decode_meta(json_str: [str, bytes]) -> dict:
        meta = json.loads(json_str)
        meta['finished'] = set(meta['finish'])
        return meta

    @staticmethod
    def encode_meta(meta: dict) -> str:
        m = copy.deepcopy(meta)
        m['finished'] = list(m['finished'])
        return json.dumps(m)

    @property
    def data_finished(self):
        with self._condition:
            return len(self._meta['finished']) == len(self._file_paths)

    def wait_for_finished(self):
        if not self.data_finished and not self._stopped:
            with self._condition:
                while not self.data_finished and not self._stopped:
                    self._condition.wait()
