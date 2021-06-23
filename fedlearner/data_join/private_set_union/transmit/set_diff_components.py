import logging
import typing

import numpy as np
import pyarrow as pa
from google.protobuf.empty_pb2 import Empty

import fedlearner.common.common_pb2 as common_pb
import fedlearner.common.private_set_union_pb2 as psu_pb
import fedlearner.common.transmitter_service_pb2 as tsmt_pb
import fedlearner.common.transmitter_service_pb2_grpc as tsmt_grpc
import fedlearner.data_join.private_set_union.parquet_utils as pqu
from fedlearner.data_join.private_set_union.keys import get_keys
from fedlearner.data_join.private_set_union.utils import E2, E3, E4
from fedlearner.data_join.transmitter.components import Sender, Receiver
from fedlearner.data_join.transmitter.utils import PostProcessJob
from fedlearner.data_join.visitors.parquet_visitor import ParquetVisitor


class SetDiffMode:
    L = 'l_diff'
    R = 'r_diff'


class ParquetSetDiffSender(Sender):
    def __init__(self,
                 mode: str,  # l_diff (right - left) or r_diff (l - r)
                 output_path: str,
                 peer_client: tsmt_grpc.TransmitterWorkerServiceStub,
                 master_client,
                 send_row_num: int,
                 send_queue_len: int = 10,
                 resp_queue_len: int = 10):
        assert mode in (SetDiffMode.L, SetDiffMode.R)
        self._mode = mode
        self._master = master_client
        key_info = self._master.GetKeys(Empty()).key_info
        self._keys = get_keys(key_info)
        self._hash_func = np.frompyfunc(self._keys.hash, 1, 1)
        self._encode_func = np.frompyfunc(self._keys.encode, 1, 1)
        self._decode_func = np.frompyfunc(self._keys.decode, 1, 1)
        self._encrypt_func1 = np.frompyfunc(self._keys.encrypt_1, 1, 1)
        self._encrypt_func2 = np.frompyfunc(self._keys.encrypt_2, 1, 1)
        self._output_path = output_path
        self._indices = {}
        self._dumper = None
        # TODO(zhangzihui): accustom for new info
        if self._mode == SetDiffMode.L:
            self._send_col = E2
            self._resp_col = E3
            self._schema = pa.schema([pa.field(E4, pa.string())])
        else:
            self._send_col = E3
            self._resp_col = None
            self._schema = None
        self._visitor = ParquetVisitor(batch_size=send_row_num,
                                       columns=self._send_col,
                                       consume_remain=True)
        super().__init__(peer_client, send_queue_len, resp_queue_len)

    def _send_process(self) -> typing.Iterable[bytes, tsmt_pb.BatchInfo]:
        for batches, batch_info in self._visitor:
            if len(batches) == 0:
                yield None, batch_info

            batch_dict = batches[0].to_pydict()
            if len(batches) > 1:
                batch2 = batches[1].to_pydict()
                for k in batch_dict.keys():
                    batch_dict[k].extend(batch2[k])
            payload = psu_pb.DataSyncRequest(payload=batches)
            yield payload.SerializeToString(), batch_info

    def _resp_process(self,
                      resp: tsmt_pb.Response) -> None:
        if self._mode == SetDiffMode.R:
            # no response needed to process in right diff mode
            if resp.batch_info.finished:
                self._master.FinishFiles(tsmt_pb.FinishFilesRequest(
                    file_idx=[resp.batch_info.file_idx]))
            return

        encrypt_res = psu_pb.EncryptTransmitResponse()
        encrypt_res.ParseFromString(resp.payload)
        quadruply_encrypted = self._encode_func(self._encrypt_func2(
            self._decode_func(np.asarray(encrypt_res.triply_encrypted))
        ))
        # construct a table and dump
        table = {E4: quadruply_encrypted}
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
                file_idx=resp.batch_info.file_idx))

    def _request_task_from_master(self):
        resp = self._master.AllocateTask(
            tsmt_pb.AllocateTaskRequest(rank_id=self._rank_id))
        if resp.status.code == common_pb.STATUS_INVALID_REQUEST:
            # TODO(zhangzihui): error handling
            logging.warning('Invalid Request Task')
        self._visitor.init(resp.file_info)
        return resp

    def report_peer_file_finish_to_master(self, file_idx: int):
        return self._master.RecvFinishFiles(
            tsmt_pb.FinishFilesRequest(file_idx=[file_idx]))

    def _stop(self, *args, **kwargs):
        if self._dumper:
            self._dumper.close()


class ParquetSetDiffReceiver(Receiver):
    def __init__(self,
                 mode: str,
                 peer_client: tsmt_grpc.TransmitterWorkerServiceStub,
                 master_client,
                 output_path: str,
                 recv_queue_len: int):
        assert mode in (SetDiffMode.L, SetDiffMode.R)
        self._mode = mode
        key_info = master_client.GetKeys(Empty()).key_info
        self._keys = get_keys(key_info)
        self._hash_func = np.frompyfunc(self._keys.hash, 1, 1)
        self._encode_func = np.frompyfunc(self._keys.encode, 1, 1)
        self._decode_func = np.frompyfunc(self._keys.decode, 1, 1)
        self._encrypt_func1 = np.frompyfunc(self._keys.encrypt_1, 1, 1)
        self._encrypt_func2 = np.frompyfunc(self._keys.encrypt_2, 1, 1)
        self._dumper = None
        self._schema = pa.schema([pa.field(E4, pa.string())])
        super().__init__(peer_client, output_path, recv_queue_len)

    def _recv_process(self,
                      req: tsmt_pb.Request,
                      consecutive: bool) -> (bytes, [PostProcessJob, None]):
        encrypt_req = psu_pb.EncryptTransmitRequest()
        encrypt_req.ParseFromString(req.payload)
        if self._mode == SetDiffMode.L:
            payload = self._encode_func(self._encrypt_func2(self._decode_func(
                np.asarray(encrypt_req.doubly_encrypted, np.bytes_)
            )))
            payload = psu_pb.DataSyncResponse(
                payload={E3: psu_pb.BytesList(value=payload)}
            ).SerializeToString()
            task = None  # Nothing to dump
        else:
            payload = None  # Noting to return
            if consecutive:
                e4 = self._encode_func(self._encrypt_func2(self._decode_func(
                        np.asarray(encrypt_req.triply_encrypted, np.bytes_)
                )))
                # OUTPUT_PATH/doubly_encrypted/<file_idx>.parquet
                file_path = pqu.encode_quadruply_encrypted_file_path(
                    self._output_path, req.file_idx)
                task = PostProcessJob(self._job_fn, e4, file_path)
            else:
                task = None

        return payload, task

    def _job_fn(self,
                doubly_encrypted: np.ndarray,
                file_path: str):
        self._dumper = pqu.make_or_update_dumper(
            self._dumper, file_path, self._schema, flavor='spark')
        table = pa.Table.from_pydict(
            mapping={'doubly_encrypted': self._encode_func(doubly_encrypted)},
            schema=self._schema)
        self._dumper.write_table(table)

    def _stop(self, *args, **kwargs):
        if self._dumper:
            self._dumper.close()
