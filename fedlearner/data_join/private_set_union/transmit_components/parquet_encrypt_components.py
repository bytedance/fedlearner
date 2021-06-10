import os
import typing
import uuid

import numpy as np
import pyarrow as pa

import fedlearner.common.private_set_union_pb2 as psu_pb
import fedlearner.common.transmitter_service_pb2 as transmitter_pb
import fedlearner.data_join.private_set_union.parquet_utils as pqu
from fedlearner.data_join.private_set_union.keys import BaseKeys
from fedlearner.data_join.transmitter.components import Sender, Receiver
from fedlearner.data_join.transmitter.utils import IDX


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
        self._hash_func = np.frompyfunc(self._keys.hash, 1, 1)
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
        super().__init__(meta_path, send_row_num, file_paths,
                         root_path, False, pending_len)

    def _send_process(self,
                      root_path: str,
                      files: typing.List[str],
                      start_idx: IDX,
                      row_num: int) -> (bytes, IDX, bool):
        """
        Prepare requests to send. Note that we will start sending from the
            beginning of a file.
        Args:
            root_path: root path of all files.
            files: file paths relative to root_path.
            start_idx: IDX from where we start reading.
            row_num: number of rows to read.

        Returns:
            a serialized encrypt request payload,
            an IDX indicating the start IDX of next restart,
            a bool indicating whether all data is finished.
        """
        batches, self._reader = pqu.get_batch(
            self._reader, root_path, files, start_idx, row_num,
            columns=['_index', '_job_id', self._join_key],
            consume_remain=True)

        if len(batches) == 0:
            # No batch means all files finished
            #   (return)-> no payload, start of next file, data finished
            # NOTE: this next-file IDX is needed for peer and self(in recv) to
            #   update the meta respectively
            return None, IDX(self._reader.file_idx + 1, 0), True

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
        singly_encrypted = unison[:, 1]
        payload = psu_pb.EncryptTransmitRequest(
            singly_encrypted=singly_encrypted,
            job_id=job_id,
            req_id=req_id)
        return payload.SerializeToString(), self._reader.idx, False

    def _resp_process(self,
                      resp: transmitter_pb.Response,
                      current_idx: IDX) -> IDX:
        """
        Process response from peer. Note that we will start sending & dumping
            from the beginning of a file, so responses will not contain
            partially duplicated rows.
        Args:
            resp: transmitter response.
            current_idx: the next row we expect to process, will start from the
                beginning of a file if restarts.

        Returns:
            an IDX indicating where the next restart should start from. Note
                that this will be None or its row_idx part will be 0.
        """
        start_idx = IDX(resp.start_file_idx, resp.start_row_idx)
        end_idx = IDX(resp.end_file_idx, resp.end_row_idx)
        if end_idx.row_idx == 0:
            # it is the last response indicating the end of all data
            return end_idx
        if not start_idx == current_idx < end_idx:
            # it is a duplicated one or a preceded one, nothing to dump
            return None

        encrypt_res = psu_pb.EncryptTransmitResponse()
        encrypt_res.ParseFromString(resp.payload)
        # retrieve original indices, Channel assures each response will only
        #   arrive once
        _index = np.frombuffer(self._indices.pop(encrypt_res.req_id),
                               dtype=np.long)
        triply_encrypted = np.asarray(encrypt_res.triply_encrypted)
        assert len(triply_encrypted) == len(_index)
        quadruply_encrypted = self._encrypt_func2(triply_encrypted)
        # construct a table and dump
        table = {'_index': _index.tolist(),
                 '_job_id': [encrypt_res.job_id for _ in range(len(_index))],
                 'quadruply_encrypted': quadruply_encrypted.tolist()}
        table = pa.Table.from_pydict(mapping=table, schema=self._schema)
        # OUTPUT_PATH/quadruply_encrypted/<file_idx>.parquet
        file_path = pqu.encode_quadruply_encrypted_file_path(
            self._output_path, end_idx.file_idx)
        # dumper will be renewed if the last file finished.
        self._dumper = pqu.make_or_update_dumper(
            self._dumper, start_idx, end_idx, file_path, self._schema,
            flavor='spark')
        self._dumper.write_table(table)
        # if it's still the same file, we don't update meta to disk;
        # if it's a new file, update meta to the first line of the new file,
        #   s.t. we will start reading from the new file if restarts.
        return None if current_idx.file_idx == end_idx.file_idx \
            else IDX(end_idx.file_idx, 0)

    def _stop(self, *args, **kwargs):
        if self._dumper:
            self._dumper.close()


class ParquetEncryptReceiver(Receiver):
    def __init__(self,
                 keys: BaseKeys,
                 meta_path: str,
                 output_path: str):
        self._keys = keys
        self._hash_func = np.frompyfunc(self._keys.hash, 1, 1)
        self._encrypt_func1 = np.frompyfunc(self._keys.encrypt_1, 1, 1)
        self._encrypt_func2 = np.frompyfunc(self._keys.encrypt_2, 1, 1)
        self._dumper = None
        self._schema = pa.schema([pa.field('doubly_encrypted', pa.string())])
        super().__init__(meta_path, output_path)

    def _recv_process(self,
                      req: transmitter_pb.Request,
                      current_idx: IDX) -> (bytes, IDX):
        """
        Process requests from peer. Note that we will start from the beginning
            of a file after restarts. No requests will contain partially
            duplicated rows. If there is a duplicated / preceded request, we'll
            encrypt it as usual but without dumping.
        Args:
            req: a transmitter request.
            current_idx: the next IDX we expect to process

        Returns:
            a serialized encrypt response payload,
            an IDX indicating where to start from if restarts
        """
        start_idx = IDX(req.start_file_idx, req.start_row_idx)
        end_idx = IDX(req.end_file_idx, req.end_row_idx)
        if end_idx.row_idx == 0:
            # it is the end of all data
            return None, end_idx
        # duplicated and preceded req does not need dump
        need_dump = start_idx == current_idx < end_idx
        encrypt_req = psu_pb.EncryptTransmitRequest()
        encrypt_req.ParseFromString(req.payload)

        doubly_encrypted = self._encrypt_func1(
            np.asarray(encrypt_req.singly_encrypted, np.bytes_)
        )
        triply_encrypted = self._encrypt_func2(doubly_encrypted)

        if need_dump:
            # OUTPUT_PATH/doubly_encrypted/<file_idx>.parquet
            file_path = pqu.encode_doubly_encrypted_file_path(
                self._output_path, end_idx.file_idx)
            self._dumper = pqu.make_or_update_dumper(
                self._dumper, start_idx, end_idx, file_path, self._schema,
                flavor='spark')
            table = pa.Table.from_pydict(
                mapping={'doubly_encrypted': doubly_encrypted},
                schema=self._schema)
            self._dumper.write_table(table)

        # if it's still the same file, we don't update meta to disk;
        # if it's a new file, update meta to the first line of the new file,
        #   s.t. we will start receiving from the new file if restarts.
        forward_idx = None if current_idx.file_idx == end_idx.file_idx \
            else IDX(end_idx.file_idx, 0)
        res = psu_pb.EncryptTransmitResponse(
            triply_encrypted=triply_encrypted,
            req_id=encrypt_req.req_id,
            job_id=encrypt_req.job_id)
        return res.SerializeToString(), forward_idx

    def _stop(self, *args, **kwargs):
        if self._dumper:
            self._dumper.close()
