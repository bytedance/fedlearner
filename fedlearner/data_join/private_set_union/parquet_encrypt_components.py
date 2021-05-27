import os
import typing
import uuid

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

import fedlearner.common.private_set_union_pb2 as psu_pb
import fedlearner.common.transmitter_service_pb2 as transmitter_pb
from fedlearner.data_join.private_set_union.keys import BaseKeys
from fedlearner.data_join.private_set_union.utils import _make_parquet_dumper, \
    _get_skip
from fedlearner.data_join.private_set_union.parquet_components import ParquetSender
from fedlearner.data_join.transmitter.utils import IDX


class ParquetEncryptSender(ParquetSender):
    def __init__(self,
                 keys: BaseKeys,
                 output_path: str,
                 meta_path: str,
                 send_row_num: int,
                 file_paths: typing.List[str],
                 root_path: str = None,
                 pending_len: int = 10,
                 join_key: str = 'example_id'):
        self._keys = keys
        self._encrypt_func1 = np.frompyfunc(self._keys.encrypt_func1, 1, 1)
        self._encrypt_func2 = np.frompyfunc(self._keys.encrypt_func2, 1, 1)
        self._output_path = output_path
        self._join_key = join_key
        self._indices = {}
        self._dumper = None
        self._dump_file_path = None
        self._schema = pa.schema([pa.field('_job_id', pa.int64()),
                                  pa.field('_index', pa.int64()),
                                  pa.field('quadruply_signed', pa.string())])
        super().__init__(meta_path, send_row_num, file_paths,
                         root_path, pending_len)

    def _send_process(self,
                      root_path: str,
                      files: typing.List[str],
                      start_idx: IDX,
                      row_num: int) -> (bytes, IDX, bool):
        batch, end_idx = self._get_batch(
            root_path, files, start_idx, row_num,
            columns=['_index', '_job_id', self._join_key])
        if not batch:
            # No batch means all files finished
            #   -> no payload, next of end row, data finished
            return None, \
                   IDX(start_idx.file_idx,
                       self._pq_file.metadata.num_rows), \
                   True

        batch_dict = batch.to_pydict()
        # how many elements from batch should be retained, as batch may start
        #   at a position before start_idx.
        if start_idx.file_idx < end_idx.file_idx:
            retain = end_idx.row_idx
        else:
            retain = end_idx.row_idx - start_idx.row_idx

        # the job id of this file. _index is unique in the event of same job id.
        job_id = batch_dict['job_id'][0]
        # _index is the order of each row in raw data's Spark process,
        #   independent of <join_key>.
        _index = np.asarray(batch_dict['_index'][-retain:])
        # encrypt join keys using private key 1
        join_keys = np.asarray(batch_dict[self._join_key][-retain:])
        singly_encrypted = self._encrypt_func1(join_keys)

        assert batch.num_rows == len(_index) == len(singly_encrypted)
        # in-place shuffle
        unison = np.c_[_index, singly_encrypted]
        np.random.shuffle(unison)
        req_id = uuid.uuid4().hex
        self._indices[req_id] = unison[:, 0].tobytes()
        singly_encrypted = unison[:, 1]
        payload = psu_pb.EncryptTransmitRequest(
            singly_encrypted=singly_encrypted.tolist(),
            job_id=job_id,
            req_id=req_id)
        return payload.SerializeToString(), end_idx, False

    def _resp_process(self,
                      resp: transmitter_pb.Response,
                      current_idx: IDX) -> IDX:
        start_idx = IDX(resp.start_file_idx, resp.start_row_idx)
        end_idx = IDX(resp.end_file_idx, resp.end_row_idx)
        if not start_idx <= current_idx < end_idx:
            # it is a duplicated one or a preceded one, nothing to dump
            return None

        # skip rows that are already dumped
        skip = _get_skip(start_idx, current_idx, end_idx)

        encrypt_res = psu_pb.EncryptTransmitResponse()
        encrypt_res.ParseFromString(resp.payload)
        _index = np.frombuffer(self._indices[encrypt_res.req_id],
                               dtype=np.long)[skip:]
        triply_encrypted = np.asarray(encrypt_res.triply_encrypted)[skip:]
        assert len(triply_encrypted) == len(_index)
        quadruply_encrypted = self._encrypt_func2(triply_encrypted)

        table = {'_index': _index.tolist(),
                 '_job_id': [encrypt_res.job_id for _ in range(len(_index))],
                 'quadruply_encrypted': quadruply_encrypted.tolist()}
        table = pa.Table.from_pydict(mapping=table, schema=self._schema)
        # OUTPUT_PATH/<job_id>/<file_idx>.parquet
        file_name = str(end_idx.file_idx) + '.parquet'
        file_path = os.path.join(self._output_path, str(resp.job_id), file_name)
        self._dumper = _make_parquet_dumper(
            file_path, self._schema, self._dumper, current_idx, end_idx)
        self._dumper.write_table(table)
        return None if current_idx.file_idx == end_idx.file_idx \
            else current_idx


class ParquetEncryptReceiver(Receiver):
    def __init__(self,
                 keys: BaseKeys,
                 meta_path: str,
                 output_path: str,
                 join_key: str = 'example_id'):
        self._keys = keys
        self._hash_func = np.frompyfunc(self._keys.hash_func, 1, 1)
        self._encrypt_func1 = np.frompyfunc(self._keys.encrypt_func1, 1, 1)
        self._encrypt_func2 = np.frompyfunc(self._keys.encrypt_func2, 1, 1)
        self._join_key = join_key
        self._dumper = None
        self._dump_file_path = None
        self._schema = pa.schema([pa.field('_doubly_signed', pa.string())])
        super().__init__(meta_path, output_path)

    def _recv_process(self,
                      req: transmitter_pb.Request,
                      current_idx: IDX) -> (bytes, IDX):
        start_idx = IDX(req.start_file_idx, req.start_row_idx)
        end_idx = IDX(req.end_file_idx, req.end_row_idx)
        need_dump = start_idx <= current_idx < end_idx
        sign_req = psu_pb.EncryptTransmitRequest()
        sign_req.ParseFromString(req.payload)

        singly_encrypted = np.asarray(sign_req.singly_signed, np.bytes_)
        doubly_encrypted = self._encrypt_func1(singly_encrypted)
        triply_encrypted = self._encrypt_func2(doubly_encrypted)

        if need_dump:
            # skip the duplicated rows
            skip = _get_skip(start_idx, current_idx, end_idx)
            # OUTPUT_PATH/<job_id>/<file_idx>.parquet
            file_name = str(end_idx.file_idx) + '.parquet'
            file_path = os.path.join(
                self._output_path, str(req.job_id), file_name)
            self._dumper = _make_parquet_dumper(
                file_path, self._schema, self._dumper, current_idx, end_idx)
            table = pa.Table.from_pydict(
                mapping={'_doubly_encrypted': doubly_encrypted[skip:]},
                schema=self._schema)
            self._dumper.write_table(table)

        # if we didn't switch to a new file, then do not forward
        forward_idx = None if current_idx.file_idx == end_idx.file_idx \
            else current_idx
        res = psu_pb.EncryptTransmitResponse(
            triply_encrypted=triply_encrypted.tolist(),
            req_id=req.req_id,
            job_id=req.job_id)
        return res.SerializeToString(), forward_idx
