import itertools
import json
import threading
import typing
from collections import defaultdict

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
        self._meta_path = meta_path
        self._db_client = DBClient('dfs')
        self._condition = threading.Condition()
        self._meta = self._get_meta()
        self._stopped = False
        self._task_size = len(self._meta['waiting']) // worker_num
        # use remains to equally distribute file to every task
        self._remains = len(self._meta['waiting']) % worker_num
        super().__init__()

    def AllocateTask(self, request, context):
        rid = request.rank_id
        if self._file_depleted(rank_id=rid):
            with self._condition:
                self._condition.notify_all()
            return tsmt_pb.AllocateTaskResponse(
                status=common_pb.STATUS_NO_MORE_DATA)

        with self._condition:
            alloc_num = self._task_size
            alloc_idx = self._meta['processing'][rid][:alloc_num + 1]
            alloc_num -= len(alloc_idx)
            # if too many processing files, will not allocate waiting files
            if alloc_num >= 0:
                if self._remains > 0:
                    alloc_num += 1
                    self._remains -= 1
                new_alloc = self._meta['waiting'][:alloc_num]
                self._meta['waiting'] = self._meta['waiting'][alloc_num:]
                self._meta['processing'][rid] += new_alloc
                alloc_idx += new_alloc
        alloc_files = [self._meta['files'][i] for i in alloc_idx]
        return tsmt_pb.AllocateTaskResponse(
            status=common_pb.STATUS_SUCCESS,
            files=alloc_files,
            file_idx=alloc_idx)

    def FinishFiles(self, request, context):
        rid = request.rank_id
        not_processing = []
        with self._condition:
            for i in request.file_idx:
                try:
                    self._meta['processing'][rid].remove(i)
                except ValueError:
                    not_processing.append(i)
                else:
                    self._meta['finished'].append(i)

            self._dump_meta(self._meta)

        if not_processing:
            np = [self._meta['files'][i] for i in not_processing]
            return tsmt_pb.FinishFilesResponse(
                status=common_pb.STATUS_NOT_PROCESSING,
                err_msg='Files [{}] were not in processing state.'.format(np))

        return tsmt_pb.FinishFilesResponse(
            status=common_pb.STATUS_SUCCESS)

    def _get_meta(self) -> dict:
        meta = self._read_meta()
        if meta:
            processing = list(itertools.chain(*meta['processing'].values()))
            meta['waiting'] = processing + meta['waiting']
            meta['processing'] = {}
            new_files = set(self._file_paths) - set(meta['files'])
            if new_files:
                meta['waiting'].extend(
                    range(len(meta['files']),
                          len(meta['files']) + len(new_files)))
                meta['files'].extend(new_files)
        else:
            meta = {
                'files': self._file_paths,
                'waiting': list(range(len(self._file_paths))),
                'processing': defaultdict(list),
                'finished': []
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
        meta['processing'] = defaultdict(list, meta['processing'])
        return meta

    @staticmethod
    def encode_meta(meta: dict) -> str:
        return json.dumps(meta)

    def _file_depleted(self, rank_id: int = None):
        depleted = len(self._meta['waiting']) == 0
        if rank_id:
            depleted = depleted and len(self._meta['processing'][rank_id]) == 0
        else:
            for processing in self._meta['processing'].values():
                if not depleted:
                    return False
                depleted = depleted and len(processing) == 0
        return depleted

    def wait_for_finished(self):
        if not self._file_depleted() and not self._stopped:
            with self._condition:
                while not self._file_depleted() and not self._stopped:
                    self._condition.wait()
