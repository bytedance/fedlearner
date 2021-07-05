import typing
from functools import partial

import numpy as np
import pyarrow as pa
from google.protobuf.empty_pb2 import Empty

import fedlearner.common.private_set_union_pb2 as psu_pb
import fedlearner.common.private_set_union_pb2_grpc as psu_grpc
import fedlearner.common.transmitter_service_pb2 as tsmt_pb
import fedlearner.common.transmitter_service_pb2_grpc as tsmt_grpc
import fedlearner.data_join.private_set_union.parquet_utils as pqu
from fedlearner.data_join.private_set_union.keys import get_keys
from fedlearner.data_join.private_set_union.transmit.base_components import \
    PSUSender, PSUReceiver
from fedlearner.data_join.private_set_union.utils import E2, E3, E4, Paths
from fedlearner.data_join.visitors.parquet_visitor import ParquetVisitor


class SetDiffMode:
    L = 'l_diff'
    R = 'r_diff'


class ParquetSetDiffSender(PSUSender):
    def __init__(self,
                 rank_id: int,
                 mode: str,  # l_diff (right - left) or r_diff (l - r)
                 peer_client: tsmt_grpc.TransmitterWorkerServiceStub,
                 master_client: psu_grpc.PSUTransmitterMasterServiceStub,
                 batch_size: int,
                 send_queue_len: int = 10,
                 resp_queue_len: int = 10):
        assert mode in (SetDiffMode.L, SetDiffMode.R)
        self._mode = mode
        if self._mode == SetDiffMode.L:
            self._send_col = E2
            self._resp_col = E3
            self._schema = pa.schema([pa.field(E4, pa.string())])
            phase = psu_pb.PSU_L_Diff
        else:
            self._send_col = E3
            self._resp_col = None
            self._schema = None
            phase = psu_pb.PSU_R_Diff

        super().__init__(rank_id=rank_id,
                         phase=phase,
                         visitor=ParquetVisitor(batch_size=batch_size,
                                                columns=[self._send_col],
                                                consume_remain=True),
                         master_client=master_client,
                         peer_client=peer_client,
                         send_queue_len=send_queue_len,
                         resp_queue_len=resp_queue_len)

        key_info = self._master.GetKeys(Empty()).key_info
        self._keys = get_keys(key_info)
        self._hash_func = np.frompyfunc(self._keys.hash, 1, 1)
        self._encode_func = np.frompyfunc(self._keys.encode, 1, 1)
        self._decode_func = np.frompyfunc(self._keys.decode, 1, 1)
        self._encrypt_func1 = np.frompyfunc(self._keys.encrypt_1, 1, 1)
        self._encrypt_func2 = np.frompyfunc(self._keys.encrypt_2, 1, 1)

        self._dumper = None

    def _data_iterator(self) \
            -> typing.Iterable[typing.Tuple[bytes, tsmt_pb.BatchInfo]]:
        for batch, file_idx, file_finished in self._visitor:
            payload = psu_pb.DataSyncRequest(
                payload={
                    self._send_col: psu_pb.StringList(
                        value=batch[self._send_col])
                })
            yield payload.SerializeToString(), \
                  tsmt_pb.BatchInfo(finished=file_finished,
                                    file_idx=file_idx,
                                    batch_idx=self._batch_idx)
            self._batch_idx += 1

    def _resp_process(self,
                      resp: tsmt_pb.TransmitDataResponse) -> None:
        if self._mode == SetDiffMode.R:
            # no response needed to process in right diff mode
            if resp.batch_info.finished:
                self._master.FinishFiles(psu_pb.PSUFinishFilesRequest(
                    file_idx=[resp.batch_info.file_idx],
                    phase=self.phase
                ))
            return

        sync_res = psu_pb.DataSyncResponse()
        sync_res.ParseFromString(resp.payload)
        # construct a table and dump
        table = {
            E4: self._encode_func(self._encrypt_func2(
                self._decode_func(np.asarray(sync_res.payload[E3].value))
            ))
        }
        table = pa.Table.from_pydict(mapping=table, schema=self._schema)
        # OUTPUT_PATH/quadruply_encrypted/<file_idx>.parquet
        file_path = Paths.encode_e4_file_path(resp.batch_info.file_idx)
        # dumper will be renewed if file changed.
        self._dumper = pqu.make_or_update_dumper(
            self._dumper, file_path, self._schema, flavor='spark')
        self._dumper.write_table(table)
        if resp.batch_info.finished:
            self._dumper.close()
            self._dumper = None
            self._master.FinishFiles(psu_pb.PSUFinishFilesRequest(
                file_idx=[resp.batch_info.file_idx],
                phase=self.phase
            ))


class ParquetSetDiffReceiver(PSUReceiver):
    def __init__(self,
                 mode: str,
                 peer_client: tsmt_grpc.TransmitterWorkerServiceStub,
                 master_client,
                 recv_queue_len: int = 10):
        assert mode in (SetDiffMode.L, SetDiffMode.R)
        self._mode = mode
        key_info = master_client.GetKeys(Empty()).key_info
        self._keys = get_keys(key_info)
        self._hash_func = np.frompyfunc(self._keys.hash, 1, 1)
        self._encode_func = np.frompyfunc(self._keys.encode, 1, 1)
        self._decode_func = np.frompyfunc(self._keys.decode, 1, 1)
        self._encrypt_func1 = np.frompyfunc(self._keys.encrypt_1, 1, 1)
        self._encrypt_func2 = np.frompyfunc(self._keys.encrypt_2, 1, 1)
        super().__init__(schema=pa.schema([pa.field(E4, pa.string())]),
                         peer_client=peer_client,
                         recv_queue_len=recv_queue_len)

    def _recv_process(self,
                      req: tsmt_pb.TransmitDataRequest,
                      consecutive: bool) -> (bytes, [typing.Callable, None]):
        sync_req = psu_pb.DataSyncRequest()
        sync_req.ParseFromString(req.payload)
        if self._mode == SetDiffMode.L:
            payload = self._encode_func(self._encrypt_func2(self._decode_func(
                np.asarray(sync_req.payload[E2].value, np.bytes_)
            )))
            payload = psu_pb.DataSyncResponse(
                payload={E3: psu_pb.StringList(value=payload)}
            ).SerializeToString()
            task = None  # Nothing to dump
        else:
            payload = None  # Noting to return
            if consecutive:
                e4 = self._encrypt_func2(self._decode_func(
                        np.asarray(sync_req.payload[E3].value, np.bytes_)
                ))
                # OUTPUT_PATH/doubly_encrypted/<file_idx>.parquet
                fp = Paths.encode_e4_file_path(req.batch_info.file_idx)
                task = partial(self._job_fn, E4, e4, fp,
                               req.batch_info.finished, self._encode_func)
            else:
                task = None

        return payload, task
