import typing

import numpy as np
import pyarrow as pa

import fedlearner.common.common_pb2 as common_pb
import fedlearner.common.private_set_union_pb2 as psu_pb
import fedlearner.common.private_set_union_pb2_grpc as psu_grpc
import fedlearner.common.transmitter_service_pb2 as tsmt_pb
import fedlearner.common.transmitter_service_pb2_grpc as tsmt_grpc
import fedlearner.data_join.private_set_union.parquet_utils as pqu
from fedlearner.data_join.transmitter.components import Sender, Receiver
from fedlearner.data_join.visitors.visitor import Visitor


class PSUSender(Sender):
    def __init__(self,
                 rank_id: int,
                 phase,
                 visitor: Visitor,
                 master_client: psu_grpc.PSUTransmitterMasterServiceStub,
                 peer_client: tsmt_grpc.TransmitterWorkerServiceStub,
                 send_queue_len: int = 10,
                 resp_queue_len: int = 10):
        self._rank_id = rank_id
        self.phase = phase
        self._visitor = visitor
        self._batch_idx = 0
        self._master = master_client
        super().__init__(peer_client, send_queue_len, resp_queue_len)

    def _data_iterator(self) \
            -> typing.Iterable[typing.Tuple[bytes, tsmt_pb.BatchInfo]]:
        raise NotImplementedError

    def _resp_process(self,
                      resp: tsmt_pb.TransmitDataResponse) -> None:
        raise NotImplementedError

    def _request_task_from_master(self) -> common_pb.Status:
        resp = self._master.AllocateTask(
            psu_pb.PSUAllocateTaskRequest(rank_id=self._rank_id,
                                          phase=self.phase))
        if resp.status.code != common_pb.STATUS_NO_MORE_DATA:
            self._visitor.init(resp.file_infos)
        return resp.status

    def report_peer_file_finish_to_master(self, file_idx: int):
        return self._master.RecvFinishFiles(
            psu_pb.PSUFinishFilesRequest(file_idx=[file_idx],
                                         phase=self.phase))


class PSUReceiver(Receiver):
    def __init__(self,
                 schema: pa.Schema,
                 peer_client: tsmt_grpc.TransmitterWorkerServiceStub,
                 recv_queue_len: int = 10):
        self._schema = schema
        self._dumper = None
        super().__init__(peer_client, recv_queue_len)

    def _recv_process(self,
                      req: tsmt_pb.TransmitDataRequest,
                      consecutive: bool) -> (bytes, [typing.Callable, None]):
        raise NotImplementedError

    def _job_fn(self,
                col_name: str,
                col_data: np.ndarray,
                file_path: str,
                file_finished: bool,
                encode_func: typing.Callable = None):
        self._dumper = pqu.make_or_update_dumper(
            self._dumper, file_path, self._schema, flavor='spark')
        if encode_func:
            table = pa.Table.from_pydict(
                mapping={col_name: encode_func(col_data)}, schema=self._schema)
        else:
            table = pa.Table.from_pydict(
                mapping={col_name: col_data}, schema=self._schema)
        self._dumper.write_table(table)
        if file_finished:
            self._dumper.close()
            self._dumper = None

