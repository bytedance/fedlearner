import functools
import typing

import numpy as np
import pyarrow as pa

import fedlearner.common.private_set_union_pb2 as psu_pb
import fedlearner.common.private_set_union_pb2_grpc as psu_grpc
import fedlearner.common.transmitter_service_pb2 as tsmt_pb
import fedlearner.common.transmitter_service_pb2_grpc as tsmt_grpc
from fedlearner.data_join.private_set_union.transmit.base_components import \
    PSUSender, PSUReceiver
from fedlearner.data_join.private_set_union.utils import E2, Paths
from fedlearner.data_join.visitors.parquet_visitor import ParquetVisitor


class ParquetSyncSender(PSUSender):
    def __init__(self,
                 rank_id: int,
                 sync_columns: typing.List[str],
                 need_shuffle: bool,
                 master_client: psu_grpc.PSUTransmitterMasterServiceStub,
                 peer_client: tsmt_grpc.TransmitterWorkerServiceStub,
                 batch_size: int,
                 send_queue_len: int = 10,
                 resp_queue_len: int = 10):
        super().__init__(rank_id=rank_id,
                         phase=psu_pb.PSU_Sync,
                         visitor=ParquetVisitor(batch_size=batch_size,
                                                columns=sync_columns,
                                                consume_remain=True),
                         master_client=master_client,
                         peer_client=peer_client,
                         send_queue_len=send_queue_len,
                         resp_queue_len=resp_queue_len)
        self._rank_id = rank_id
        self.phase = psu_pb.PSU_Sync
        self._columns = sync_columns
        self._need_shuffle = need_shuffle

    def _data_iterator(self) \
            -> typing.Iterable[typing.Tuple[bytes, tsmt_pb.BatchInfo]]:
        for batch, file_idx, file_finished in self._visitor:
            batch = {col: np.asarray(batch[col]) for col in self._columns}
            if self._need_shuffle:
                p = np.random.permutation(len(batch[self._columns[0]]))
                for col in self._columns:
                    batch[col] = batch[col][p]
            payload = psu_pb.DataSyncRequest(
                payload={col: psu_pb.StringList(value=batch[col])
                         for col in self._columns}
            )
            yield payload.SerializeToString(), \
                  tsmt_pb.BatchInfo(finished=file_finished,
                                    file_idx=file_idx,
                                    batch_idx=self._batch_idx)
            self._batch_idx += 1

    def _resp_process(self,
                      resp: tsmt_pb.TransmitDataResponse) -> None:
        if resp.batch_info.finished:
            self._master.FinishFiles(psu_pb.PSUFinishFilesRequest(
                file_idx=[resp.batch_info.file_idx],
                phase=self.phase
            ))


class ParquetSyncReceiver(PSUReceiver):
    def __init__(self,
                 peer_client: tsmt_grpc.TransmitterWorkerServiceStub,
                 recv_queue_len: int = 10):
        super().__init__(schema=pa.schema([pa.field(E2, pa.string())]),
                         peer_client=peer_client,
                         recv_queue_len=recv_queue_len)

    def _recv_process(self,
                      req: tsmt_pb.TransmitDataRequest,
                      consecutive: bool) -> (bytes, [typing.Callable, None]):
        # duplicated and preceded req does not need dump
        if consecutive:
            sync_req = psu_pb.DataSyncRequest()
            sync_req.ParseFromString(req.payload)
            # OUTPUT_PATH/doubly_encrypted_sync/<file_idx>.parquet
            fp = Paths.encode_sync_file_path(req.batch_info.file_idx)
            return None, functools.partial(
                self._job_fn, E2, sync_req.payload[E2].value,
                fp, req.batch_info.finished, None)
        return None, None
