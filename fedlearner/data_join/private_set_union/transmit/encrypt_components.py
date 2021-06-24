import functools
import typing
import uuid

import numpy as np
import pyarrow as pa
from google.protobuf.empty_pb2 import Empty

import fedlearner.common.private_set_union_pb2 as psu_pb
import fedlearner.common.private_set_union_pb2_grpc as psu_grpc
import fedlearner.common.transmitter_service_pb2 as tsmt_pb
import fedlearner.common.transmitter_service_pb2_grpc as tsmt_grpc
import fedlearner.data_join.private_set_union.parquet_utils as pqu
from fedlearner.data_join.private_set_union import transmit
from fedlearner.data_join.private_set_union.keys import get_keys
from fedlearner.data_join.private_set_union.utils import E1, E2, E3, E4
from fedlearner.data_join.transmitter.components import Receiver
from fedlearner.data_join.visitors.parquet_visitor import ParquetVisitor


class _Col:
    idx = '_index'
    job_id = '_job_id'


class ParquetEncryptSender(transmit.PSUSender):
    def __init__(self,
                 rank_id: int,
                 output_path: str,
                 batch_size: int,
                 join_key: str,
                 master_client: psu_grpc.PSUTransmitterMasterServiceStub,
                 peer_client: tsmt_grpc.TransmitterWorkerServiceStub,
                 send_queue_len: int = 10,
                 resp_queue_len: int = 10):
        super().__init__(rank_id=rank_id,
                         phase=psu_pb.Encrypt,
                         visitor=ParquetVisitor(
                             batch_size=batch_size,
                             columns=[join_key, _Col.idx, _Col.job_id],
                             consume_remain=True),
                         master_client=master_client,
                         peer_client=peer_client,
                         send_queue_len=send_queue_len,
                         resp_queue_len=resp_queue_len)

        self._output_path = output_path
        self._join_key = join_key

        key_info = self._master.GetKeys(Empty()).key_info
        self._keys = get_keys(key_info)
        self._hash_func = np.frompyfunc(self._keys.hash, 1, 1)
        self._encode_func = np.frompyfunc(self._keys.encode, 1, 1)
        self._decode_func = np.frompyfunc(self._keys.decode, 1, 1)
        self._encrypt_func1 = np.frompyfunc(self._keys.encrypt_1, 1, 1)
        self._encrypt_func2 = np.frompyfunc(self._keys.encrypt_2, 1, 1)

        self._indices = {}
        self._dumper = None
        self._schema = pa.schema([pa.field('_job_id', pa.int64()),
                                  pa.field('_index', pa.int64()),
                                  pa.field(E4, pa.string())])

    def _data_iterator(self) \
            -> typing.Iterable[typing.Tuple[bytes, tsmt_pb.BatchInfo]]:
        for batch, file_idx, file_finished in self._visitor:
            assert len(batch[_Col.idx]) == len(batch[self._join_key])
            # the job id of this file. _index is unique if job id is same.
            job_id = batch[_Col.job_id][0]
            # _index is the order of each row in raw data's Spark process,
            #   independent of <join_key>.
            _index = np.asarray(batch[_Col.idx])
            # hash and encrypt join keys using private key 1
            singly_encrypted = self._encode_func(self._encrypt_func1(
                self._hash_func(np.asarray(batch[self._join_key]))
            ))
            # in-place shuffle
            unison = np.c_[_index, singly_encrypted]
            np.random.shuffle(unison)
            # record the original indices for data merging in the future
            req_id = uuid.uuid4().hex.encode()
            self._indices[req_id] = unison[:, 0].astype(np.long).tobytes()
            payload = psu_pb.DataSyncRequest(
                payload={
                    E1: psu_pb.BytesList(value=unison[:, 1]),
                    _Col.job_id: psu_pb.BytesList(value=[str(job_id).encode()]),
                    'req_id': psu_pb.BytesList(value=[req_id])
                }
            )
            yield payload.SerializeToString(), \
                  tsmt_pb.BatchInfo(finished=file_finished,
                                    file_idx=file_idx,
                                    batch_idx=self._batch_idx)
            self._batch_idx += 1

    def _resp_process(self,
                      resp: tsmt_pb.TransmitDataResponse) -> None:
        sync_res = psu_pb.DataSyncResponse()
        sync_res.ParseFromString(resp.payload)
        # retrieve original indices, Channel assures each response will only
        #   arrive once
        _index = np.frombuffer(
            self._indices.pop(sync_res.payload['req_id'].value[0]),
            dtype=np.long
        )
        quadruply_encrypted = self._encrypt_func2(self._decode_func(
            np.asarray(sync_res.payload[E3].value)
        ))

        # construct a table and dump
        table = {_Col.idx: _index,
                 _Col.job_id: [int(sync_res.payload[_Col.job_id].value[0])
                               for _ in range(len(_index))],
                 E4: quadruply_encrypted}
        table = pa.Table.from_pydict(mapping=table, schema=self._schema)

        # OUTPUT_PATH/quadruply_encrypted/<file_idx>.parquet
        fp = pqu.encode_e4_file_path(self._output_path,
                                     resp.batch_info.file_idx)
        # dumper will be renewed if file changed.
        self._dumper = pqu.make_or_update_dumper(self._dumper, fp,
                                                 self._schema, flavor='spark')
        self._dumper.write_table(table)
        if resp.batch_info.finished:
            self._dumper.close()
            self._dumper = None
            self._master.FinishFiles(psu_pb.PSUFinishFilesRequest(
                file_idx=[resp.batch_info.file_idx],
                rank_id=self._rank_id
            ))


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

        self._output_path = output_path
        self._dumper = None
        self._schema = pa.schema([pa.field(E2, pa.string())])
        super().__init__(peer_client, recv_queue_len)

    def _recv_process(self,
                      req: tsmt_pb.TransmitDataRequest,
                      consecutive: bool) -> (bytes, [typing.Callable, None]):
        sync_req = psu_pb.DataSyncRequest()
        sync_req.ParseFromString(req.payload)

        doubly_encrypted = self._encrypt_func1(self._decode_func(
            np.asarray(sync_req.payload[E1].value, np.bytes_))
        )
        triply_encrypted = self._encode_func(
            self._encrypt_func2(doubly_encrypted))

        if consecutive:
            # OUTPUT_PATH/doubly_encrypted/<file_idx>.parquet
            file_path = pqu.encode_e2_file_path(
                self._output_path, req.batch_info.file_idx)
            job = functools.partial(self._job_fn, doubly_encrypted,
                                    file_path, req.batch_info.finished)
        else:
            job = None

        res = psu_pb.DataSyncResponse(
            payload={
                E3: psu_pb.BytesList(value=triply_encrypted),
                'req_id': sync_req.payload['req_id'],
                _Col.job_id: sync_req.payload[_Col.job_id]
            }
        )
        return res.SerializeToString(), job

    def _job_fn(self,
                doubly_encrypted: np.ndarray,
                file_path: str,
                finished: bool):
        self._dumper = pqu.make_or_update_dumper(
            self._dumper, file_path, self._schema, flavor='spark')
        table = pa.Table.from_pydict(
            mapping={E2: self._encode_func(doubly_encrypted)},
            schema=self._schema)
        self._dumper.write_table(table)
        if finished:
            self._dumper.close()
            self._dumper = None
