import typing
import uuid

import numpy as np
import pyarrow as pa
from google.protobuf.empty_pb2 import Empty

import fedlearner.common.private_set_union_pb2 as psu_pb
import fedlearner.common.transmitter_service_pb2 as tsmt_pb
import fedlearner.common.transmitter_service_pb2_grpc as tsmt_grpc
import fedlearner.data_join.private_set_union.parquet_utils as pqu
from fedlearner.data_join.private_set_union.keys import get_keys
from fedlearner.data_join.private_set_union.utils import E2, E4
from fedlearner.data_join.transmitter.components import Sender, Receiver
from fedlearner.data_join.transmitter.utils import PostProcessJob
from fedlearner.data_join.visitors.parquet_visitor import ParquetVisitor


class ParquetEncryptSender(Sender):
    def __init__(self,
                 output_path: str,
                 peer_client: tsmt_grpc.TransmitterWorkerServiceStub,
                 master_client,
                 send_row_num: int,
                 send_queue_len: int = 10,
                 resp_queue_len: int = 10,
                 join_key: str = 'example_id'):
        key_info = master_client.GetKeys(Empty()).key_info
        self._keys = get_keys(key_info)
        self._hash_func = np.frompyfunc(self._keys.hash, 1, 1)
        self._encode_func = np.frompyfunc(self._keys.encode, 1, 1)
        self._decode_func = np.frompyfunc(self._keys.decode, 1, 1)
        self._encrypt_func1 = np.frompyfunc(self._keys.encrypt_1, 1, 1)
        self._encrypt_func2 = np.frompyfunc(self._keys.encrypt_2, 1, 1)
        self._output_path = output_path
        self._join_key = join_key
        self._indices = {}
        self._dumper = None
        self._schema = pa.schema([pa.field('_job_id', pa.int64()),
                                  pa.field('_index', pa.int64()),
                                  pa.field(E4, pa.string())])
        # TODO(zhangzihui): accustom for new info
        visitor = ParquetVisitor()
        super().__init__(visitor, peer_client, master_client,
                         send_row_num, send_queue_len, resp_queue_len)

    def _send_process(self) -> typing.Iterable[bytes, tsmt_pb.BatchInfo]:
        for batches, batch_info in self._visitor:
            if len(batches) == 0:
                yield None, batch_info

            batch_dict = batches[0].to_pydict()
            if len(batches) > 1:
                batch2 = batches[1].to_pydict()
                for k in batch_dict.keys():
                    batch_dict[k].extend(batch2[k])
            assert len(batch_dict['_index']) == len(batch_dict[self._join_key])
            # the job id of this file. _index is unique if job id is same.
            job_id = batch_dict['_job_id'][0]
            # _index is the order of each row in raw data's Spark process,
            #   independent of <join_key>.
            _index = np.asarray(batch_dict['_index'])
            # hash and encrypt join keys using private key 1
            singly_encrypted = self._encode_func(self._encrypt_func1(
                self._hash_func(np.asarray(batch_dict[self._join_key]))
            ))
            # in-place shuffle
            unison = np.c_[_index, singly_encrypted]
            np.random.shuffle(unison)
            # record the original indices for data merging in the future
            req_id = uuid.uuid4().hex
            self._indices[req_id] = unison[:, 0].astype(np.long).tobytes()
            payload = psu_pb.EncryptTransmitRequest(
                singly_encrypted=unison[:, 1],
                job_id=job_id,
                req_id=req_id)
            yield payload.SerializeToString(), batch_info

    def _resp_process(self,
                      resp: tsmt_pb.Response) -> None:
        encrypt_res = psu_pb.EncryptTransmitResponse()
        encrypt_res.ParseFromString(resp.payload)
        # retrieve original indices, Channel assures each response will only
        #   arrive once
        _index = np.frombuffer(self._indices.pop(encrypt_res.req_id),
                               dtype=np.long)
        quadruply_encrypted = self._encrypt_func2(self._decode_func(
            np.asarray(encrypt_res.triply_encrypted)
        ))
        # construct a table and dump
        table = {'_index': _index,
                 '_job_id': [encrypt_res.job_id for _ in range(len(_index))],
                 E4: quadruply_encrypted}
        table = pa.Table.from_pydict(mapping=table, schema=self._schema)
        # OUTPUT_PATH/quadruply_encrypted/<file_idx>.parquet
        file_path = pqu.encode_quadruply_encrypted_file_path(
            self._output_path, resp.file_idx)
        # dumper will be renewed if file changed.
        self._dumper = pqu.make_or_update_dumper(
            self._dumper, file_path, self._schema, flavor='spark')
        self._dumper.write_table(table)
        if resp.batch_info.finished:
            self._dumper.close()
            self._dumper = None
            self._master.FinishFiles(tsmt_pb.FinishFilesRequest(
                file_idx=[resp.batch_info.file_idx]))

    def _request_task_from_master(self):
        return self._master.AllocateTask(
            tsmt_pb.AllocateTaskRequest(rank_id=self._rank_id))

    def report_peer_file_finish_to_master(self, file_idx: int):
        return self._master.RecvFinishFiles(
            tsmt_pb.FinishFilesRequest(file_idx=[file_idx]))

    def _stop(self, *args, **kwargs):
        if self._dumper:
            self._dumper.close()


class ParquetEncryptReceiver(Receiver):
    def __init__(self,
                 peer_client: tsmt_grpc.TransmitterWorkerServiceStub,
                 master_client,
                 output_path: str,
                 recv_queue_len: int):
        key_info = master_client.GetKeys(Empty()).key_info
        self._keys = get_keys(key_info)
        self._hash_func = np.frompyfunc(self._keys.hash, 1, 1)
        self._encode_func = np.frompyfunc(self._keys.encode, 1, 1)
        self._decode_func = np.frompyfunc(self._keys.decode, 1, 1)
        self._encrypt_func1 = np.frompyfunc(self._keys.encrypt_1, 1, 1)
        self._encrypt_func2 = np.frompyfunc(self._keys.encrypt_2, 1, 1)
        self._dumper = None
        self._schema = pa.schema([pa.field(E2, pa.string())])
        super().__init__(peer_client, master_client,
                         output_path, recv_queue_len)

    def _recv_process(self,
                      req: tsmt_pb.Request,
                      consecutive: bool) -> (bytes, [PostProcessJob, None]):
        encrypt_req = psu_pb.EncryptTransmitRequest()
        encrypt_req.ParseFromString(req.payload)

        doubly_encrypted = self._encrypt_func1(self._decode_func(
            np.asarray(encrypt_req.singly_encrypted, np.bytes_))
        )
        triply_encrypted = self._encode_func(
            self._encrypt_func2(doubly_encrypted))

        if consecutive:
            # OUTPUT_PATH/doubly_encrypted/<file_idx>.parquet
            file_path = pqu.encode_doubly_encrypted_file_path(
                self._output_path, req.file_idx)
            task = PostProcessJob(self._job_fn, doubly_encrypted, file_path)
        else:
            task = None

        res = psu_pb.EncryptTransmitResponse(
            triply_encrypted=triply_encrypted,
            req_id=encrypt_req.req_id,
            job_id=encrypt_req.job_id)
        return res.SerializeToString(), task

    def _job_fn(self,
                doubly_encrypted: np.ndarray,
                file_path: str):
        self._dumper = pqu.make_or_update_dumper(
            self._dumper, file_path, self._schema, flavor='spark')
        table = pa.Table.from_pydict(
            mapping={E2: self._encode_func(doubly_encrypted)},
            schema=self._schema)
        self._dumper.write_table(table)

    def _stop(self, *args, **kwargs):
        if self._dumper:
            self._dumper.close()
