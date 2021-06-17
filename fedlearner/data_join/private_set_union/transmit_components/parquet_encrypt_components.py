import uuid

import numpy as np
import pyarrow as pa

import fedlearner.common.private_set_union_pb2 as psu_pb
import fedlearner.common.transmitter_service_pb2 as tsmt_pb
import fedlearner.data_join.private_set_union.parquet_utils as pqu
from fedlearner.data_join.private_set_union.keys import BaseKeys
from fedlearner.data_join.transmitter.components import Sender, Receiver
from fedlearner.data_join.transmitter.utils import PostTask


class ParquetEncryptSender(Sender):
    def __init__(self,
                 keys: BaseKeys,
                 output_path: str,
                 send_row_num: int,
                 join_key: str = 'example_id',
                 send_queue_len: int = 10,
                 resp_queue_len: int = 10):
        self._keys = keys
        self._hash_func = np.frompyfunc(self._keys.hash, 1, 1)
        self._encode_func = np.frompyfunc(self._keys.encode, 1, 1)
        self._decode_func = np.frompyfunc(self._keys.decode, 1, 1)
        self._encrypt_func1 = np.frompyfunc(self._keys.encrypt_1, 1, 1)
        self._encrypt_func2 = np.frompyfunc(self._keys.encrypt_2, 1, 1)
        self._output_path = output_path
        self._join_key = join_key
        self._indices = {}
        self._reader = None
        self._dumper = None
        self._schema = pa.schema([pa.field('_job_id', pa.int64()),
                                  pa.field('_index', pa.int64()),
                                  pa.field('quadruply_encrypted', pa.string())])
        super().__init__(send_row_num, send_queue_len, resp_queue_len)

    def _send_process(self,
                      file_path: str,
                      row_num: int,
                      send_queue_len: int) -> (bytes, bool):
        batches, self._reader = pqu.get_batch(
            self._reader, file_path, row_num,
            columns=['_index', '_job_id', self._join_key],
            consume_remain=True)

        if len(batches) == 0:
            return None, True

        batch_dict = batches[0].to_pydict()
        if len(batches) > 1:
            batch2 = batches[1].to_pydict()
            for k in batch_dict.keys():
                batch_dict[k].extend(batch2[k])
        assert len(batch_dict['_index']) == len(batch_dict[self._join_key])
        # the job id of this file. _index is unique in the event of same job id.
        job_id = batch_dict['_job_id'][0]
        # _index is the order of each row in raw data's Spark process,
        #   independent of <join_key>.
        _index = np.asarray(batch_dict['_index'])
        # hash and encrypt join keys using private key 1
        singly_encrypted = self._encrypt_func1(
            self._hash_func(np.asarray(batch_dict[self._join_key]))
        )
        # in-place shuffle
        unison = np.c_[_index, singly_encrypted]
        np.random.shuffle(unison)
        # record the original indices for data merging in the future
        req_id = uuid.uuid4().hex
        self._indices[req_id] = unison[:, 0].astype(np.long).tobytes()
        singly_encrypted = self._encode_func(unison[:, 1])
        payload = psu_pb.EncryptTransmitRequest(
            singly_encrypted=singly_encrypted,
            job_id=job_id,
            req_id=req_id)
        return payload.SerializeToString(), self._reader.finished

    def _resp_process(self,
                      resp: tsmt_pb.Response) -> None:
        encrypt_res = psu_pb.EncryptTransmitResponse()
        encrypt_res.ParseFromString(resp.payload)
        # retrieve original indices, Channel assures each response will only
        #   arrive once
        _index = np.frombuffer(self._indices.pop(encrypt_res.req_id),
                               dtype=np.long)
        triply_encrypted = self._decode_func(
            np.asarray(encrypt_res.triply_encrypted))
        assert len(triply_encrypted) == len(_index)
        quadruply_encrypted = self._encrypt_func2(triply_encrypted)
        # construct a table and dump
        table = {'_index': _index,
                 '_job_id': [encrypt_res.job_id for _ in range(len(_index))],
                 'quadruply_encrypted': quadruply_encrypted}
        table = pa.Table.from_pydict(mapping=table, schema=self._schema)
        # OUTPUT_PATH/quadruply_encrypted/<file_idx>.parquet
        file_path = pqu.encode_quadruply_encrypted_file_path(
            self._output_path, resp.file_idx)
        # dumper will be renewed if file changed.
        self._dumper = pqu.make_or_update_dumper(
            self._dumper, file_path, self._schema, flavor='spark')
        self._dumper.write_table(table)

    def _stop(self, *args, **kwargs):
        if self._dumper:
            self._dumper.close()


class ParquetEncryptReceiver(Receiver):
    def __init__(self,
                 keys: BaseKeys,
                 output_path: str,
                 recv_queue_len: int = 10):
        self._keys = keys
        self._hash_func = np.frompyfunc(self._keys.hash, 1, 1)
        self._encode_func = np.frompyfunc(self._keys.encode, 1, 1)
        self._decode_func = np.frompyfunc(self._keys.decode, 1, 1)
        self._encrypt_func1 = np.frompyfunc(self._keys.encrypt_1, 1, 1)
        self._encrypt_func2 = np.frompyfunc(self._keys.encrypt_2, 1, 1)
        self._dumper = None
        self._schema = pa.schema([pa.field('doubly_encrypted', pa.string())])
        super().__init__(output_path, recv_queue_len)

    def _recv_process(self,
                      req: tsmt_pb.Request,
                      consecutive: bool) -> (bytes, [PostTask, None]):
        # duplicated and preceded req does not need dump
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
            task = PostTask(self._task_fn, doubly_encrypted, file_path)
        else:
            task = None

        res = psu_pb.EncryptTransmitResponse(
            triply_encrypted=triply_encrypted,
            req_id=encrypt_req.req_id,
            job_id=encrypt_req.job_id)
        return res.SerializeToString(), task

    def _task_fn(self,
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
