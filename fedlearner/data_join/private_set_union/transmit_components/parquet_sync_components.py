import typing

import numpy as np
import pyarrow as pa

import fedlearner.common.private_set_union_pb2 as psu_pb
import fedlearner.common.transmitter_service_pb2 as tsmt_pb
import fedlearner.common.transmitter_service_pb2_grpc as tsmt_grpc
import fedlearner.data_join.private_set_union.parquet_utils as pqu
from fedlearner.data_join.transmitter.components import Sender, Receiver
from fedlearner.data_join.transmitter.utils import PostProcessJob
from fedlearner.data_join.visitors.parquet_visitor import ParquetVisitor


class ParquetSyncSender(Sender):
    def __init__(self,
                 sync_columns: typing.List,
                 need_shuffle: bool,
                 peer_client: tsmt_grpc.TransmitterWorkerServiceStub,
                 master_client,
                 send_row_num: int,
                 consume_remain: bool = True,
                 send_queue_len: int = 10,
                 resp_queue_len: int = 10):
        self._columns = sync_columns
        self._need_shuffle = need_shuffle
        self._consume_remain = consume_remain
        # TODO(zhangzihui): accustom for new file info
        visitor = ParquetVisitor(batch_size=send_row_num,
                                 columns=sync_columns,
                                 consume_remain=True)
        super().__init__(visitor, peer_client, master_client,
                         send_row_num, send_queue_len, resp_queue_len)

    def _request_task_from_master(self):
        return self._master.AllocateTask(
            tsmt_pb.AllocateTaskRequest(rank_id=self._rank_id))

    def report_peer_file_finish_to_master(self, file_idx: int):
        return self._master.RecvFinishFiles(
            tsmt_pb.FinishFilesRequest(file_idx=[file_idx]))

    def _send_process(self) -> typing.Iterable[bytes, tsmt_pb.BatchInfo]:
        for batches, batch_info in self._visitor:
            if len(batches) == 0:
                yield None, batch_info
            batches = [batch.to_pydict() for batch in batches]
            batches = {
                col: np.concatenate([b[col] for b in batches]).astype(np.bytes_)
                for col in self._columns
            }
            if self._need_shuffle:
                p = np.random.permutation(len(batches[self._columns[0]]))
                for col in self._columns:
                    batches[col] = batches[col][p]
            batches = {col: psu_pb.BytesList(value=batches[col])
                       for col in self._columns}
            payload = psu_pb.DataSyncRequest(payload=batches)
            return payload.SerializeToString(), batch_info

    def _resp_process(self,
                      resp: tsmt_pb.Response) -> None:
        if resp.batch_info.finished:
            self._master.FinishFiles(tsmt_pb.FinishFilesRequest(
                file_idx=resp.batch_info.file_idx))


class ParquetSyncReceiver(Receiver):
    def __init__(self,
                 peer_client: tsmt_grpc.TransmitterWorkerServiceStub,
                 master_client,
                 output_path: str,
                 recv_queue_len: int):
        self._dumper = None
        self._schema = pa.schema([pa.field('doubly_encrypted', pa.string())])
        super().__init__(peer_client, master_client,
                         output_path, recv_queue_len)

    def _recv_process(self,
                      req: tsmt_pb.Request,
                      consecutive: bool) -> (bytes, [PostProcessJob, None]):
        # duplicated and preceded req does not need dump
        if consecutive:
            encrypt_req = psu_pb.DataSyncRequest()
            encrypt_req.ParseFromString(req.payload)
            # OUTPUT_PATH/doubly_encrypted/<file_idx>.parquet
            file_path = pqu.encode_doubly_encrypted_file_path(self._output_path,
                                                              req.file_idx)
            return PostProcessJob(
                self._job_fn, encrypt_req.doubly_encrypted, file_path)
        return None

    def _job_fn(self,
                doubly_encrypted: typing.List,
                file_path: str):
        self._dumper = pqu.make_or_update_dumper(
            self._dumper, file_path, self._schema, flavor='spark')
        table = pa.Table.from_pydict(
            mapping={'doubly_encrypted': doubly_encrypted},
            schema=self._schema)
        self._dumper.write_table(table)

    def _stop(self, *args, **kwargs):
        if self._dumper:
            self._dumper.close()
