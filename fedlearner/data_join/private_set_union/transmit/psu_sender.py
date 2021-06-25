import typing

import fedlearner.common.common_pb2 as common_pb
import fedlearner.common.private_set_union_pb2 as psu_pb
import fedlearner.common.private_set_union_pb2_grpc as psu_grpc
import fedlearner.common.transmitter_service_pb2 as tsmt_pb
import fedlearner.common.transmitter_service_pb2_grpc as tsmt_grpc
from fedlearner.data_join.transmitter.components import Sender
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
