import copy
import json
import threading
import typing
from collections import defaultdict

from tensorflow.python.lib.io import file_io

import fedlearner.common.common_pb2 as common_pb
import fedlearner.common.private_set_union_pb2 as psu_pb
import fedlearner.common.private_set_union_pb2_grpc as psu_grpc
import fedlearner.common.transmitter_service_pb2 as tsmt_pb
from fedlearner.data_join.private_set_union import utils
from fedlearner.data_join.private_set_union.keys import get_keys


class TransmitterMaster(psu_grpc.PSUTransmitterMasterServiceServicer):
    def __init__(self,
                 key_type,
                 file_paths: typing.List[str],
                 worker_num: int):
        self._key_info = get_keys(psu_pb.KeyInfo(type=key_type))
        self._file_paths = file_paths
        self._worker_num = worker_num
        self._meta_path = utils.Paths.encode_master_meta_path()
        self._condition = threading.Condition()
        self._meta = self._get_meta()
        self._signal_buffer = defaultdict(set)
        self._started = False
        self._stopped = False
        super().__init__()

    def GetKeys(self, request, context):
        return psu_pb.GetKeysResponse(status=common_pb.STATUS_SUCCESS,
                                      key_info=self._key_info)

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
        self._check_file_finished(request.file_idx, 'send')
        return tsmt_pb.FinishFilesResponse(status=common_pb.STATUS_SUCCESS)

    def RecvFinishFiles(self, request, context):
        self._check_file_finished(request.file_idx, 'recv')
        return tsmt_pb.FinishFilesResponse(status=common_pb.STATUS_SUCCESS)

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
        if file_io.file_exists(self._meta_path):
            meta_str = file_io.read_file_to_string(self._meta_path)
            meta = self.decode_meta(meta_str)
        else:
            meta = None
        return meta

    def _dump_meta(self, meta: dict) -> None:
        assert meta
        with self._condition:
            file_io.atomic_write_string_to_file(self._meta_path,
                                                self.encode_meta(meta))

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

    def _check_file_finished(self, indices: typing.List[int], kind: str):
        assert kind in ('send', 'recv')
        opposite = 'send' if kind == 'recv' else 'recv'
        with self._condition:
            for idx in indices:
                if idx in self._meta['finished']:
                    continue
                if idx in self._signal_buffer[opposite]:
                    self._meta['finished'].add(idx)
                    self._signal_buffer[opposite].discard(idx)
                else:
                    self._signal_buffer[kind].add(idx)
            self._dump_meta(self._meta)
