import os
import typing
import uuid

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from tensorflow import gfile

import fedlearner.common.private_set_union_pb2 as psu_pb
import fedlearner.common.transmitter_service_pb2 as transmitter_pb
from fedlearner.data_join.private_set_union.base_keys import BaseKeys
from fedlearner.data_join.transmitter.components import Sender, Receiver
from fedlearner.data_join.transmitter.utils import IDX


def _make_dumper(output_path: str,
                 schema: pa.Schema,
                 current_dumper: pq.ParquetWriter,
                 dump_idx: IDX,
                 end_idx: IDX,
                 job_id: int) -> pq.ParquetWriter:
    # OUTPUT_PATH/<job_id>/<file_idx>.parquet
    file_name = str(end_idx.file_idx) + '.parquet'
    file_path = os.path.join(output_path, str(job_id), file_name)
    if dump_idx.file_idx < end_idx.file_idx:
        # close the last file's writer and clear the next file
        current_dumper.close()
        current_dumper = None
        if gfile.Exists(file_path):
            gfile.DeleteRecursively(file_path)
    if current_dumper is None:
        current_dumper = pq.ParquetWriter(file_path, schema, flavor='spark')
    return current_dumper


def _get_skip(start_idx: IDX,
              current_idx: IDX,
              end_idx: IDX) -> int:
    """
    Calculate how many rows should be skipped according to current_idx. Note
        that in Parquet scene, we send files one by one without mixing files,
        so if start_idx.file_idx != end_idx.file_idx, all of the rows belong to
        the end_idx.file_idx's file.
    Args:
        start_idx: start IDX of the req/resp
        current_idx: current state of IDX
        end_idx: end IDX of the req/resp

    Returns:

    """
    length = end_idx.row_idx if start_idx.file_idx != end_idx.file_idx \
        else end_idx.row_idx - start_idx.row_idx
    skip = 0 if current_idx.file_idx != end_idx.file_idx \
        else length - (end_idx.row_idx - current_idx.row_idx)
    return skip


class ParquetEncryptSender(Sender):
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
        self._reader = None
        self._pq_file = None
        self._reader_idx = None
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
        file_path, batch, end_idx = self._get_batch(root_path, files,
                                                    start_idx, row_num)
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
        self._dumper = _make_dumper(
            self._output_path, self._schema, self._dumper,
            current_idx, end_idx, encrypt_res.job_id)
        self._dumper.write_table(table)
        return None if current_idx.file_idx == end_idx.file_idx \
            else current_idx

    def _get_batch(self,
                   root_path: str,
                   files: typing.List[str],
                   start_idx: IDX,
                   row_num: int) -> (pa.RecordBatch, IDX):
        file_path = os.path.join(root_path, files[start_idx.file_idx])
        if self._reader is None:
            self._pq_file = pq.ParquetFile(file_path)
            self._reader = self._pq_file.iter_batches(
                row_num, columns=['_job_id', '_index', self._join_key])
            self._reader_idx = IDX(start_idx.file_idx, 0)

        try:
            # entry to the loop should be guaranteed
            assert self._reader_idx.row_idx <= start_idx.row_idx
            while self._reader_idx.row_idx <= start_idx.row_idx:
                batch = next(self._reader)
                self._reader_idx.row_idx += batch.num_rows
        except StopIteration:
            # if it is the end of all files
            if start_idx.file_idx == len(files) - 1:
                return None, self._reader_idx
            # starting from a new file
            file_path = os.path.join(root_path, files[start_idx.file_idx + 1])
            self._pq_file = pq.ParquetFile(file_path)
            self._reader = self._pq_file.iter_batches(
                row_num, columns=['_job_id', '_index', self._join_key])
            batch = next(self._reader)
            self._reader_idx.file_idx += 1
            self._reader_idx.row_idx = batch.num_rows
        return batch, self._reader_idx


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
            self._dumper = _make_dumper(
                self._output_path, self._schema, self._dumper, current_idx,
                end_idx, req.job_id)
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
