import typing

import numpy as np
import pyarrow as pa

import fedlearner.common.private_set_union_pb2 as psu_pb
import fedlearner.common.transmitter_service_pb2 as transmitter_pb
import fedlearner.data_join.private_set_union.parquet_utils as pqu
from fedlearner.data_join.transmitter.components import Sender, Receiver
from fedlearner.data_join.transmitter.utils import IDX


class ParquetSyncSender(Sender):
    def __init__(self,
                 meta_path: str,
                 send_row_num: int,
                 file_paths: typing.List[str],
                 root_path: str = None,
                 pending_len: int = 10):
        self._reader = None
        # start_from_peer = True, s.t. always use peer's state after restart
        super().__init__(meta_path, send_row_num, file_paths,
                         root_path, True, pending_len)

    def _send_process(self,
                      root_path: str,
                      files: typing.List[str],
                      start_idx: IDX,
                      row_num: int) -> (bytes, IDX, bool):
        batches, self._reader = pqu.get_batch(
            self._reader, root_path, files, start_idx, row_num,
            columns=['doubly_encrypted'],
            consume_remain=True)
        if len(batches) == 0:
            # No batch means all files finished
            #   -> no payload, next of end row, data finished
            return None, IDX(self._reader.file_idx, 0), True
        batches = [batch.to_pydict()['doubly_encrypted'] for batch in batches]
        batches = np.concatenate(batches).astype(np.bytes_)
        np.random.shuffle(batches)
        payload = psu_pb.DataSyncRequest(doubly_encrypted=batches)
        return payload.SerializeToString(), self._reader.idx, False

    def _resp_process(self,
                      resp: transmitter_pb.Response,
                      current_idx: IDX) -> IDX:
        return None if current_idx.file_idx == resp.end_file_idx \
            else IDX(resp.end_file_idx, 0)


class ParquetSyncReceiver(Receiver):
    def __init__(self,
                 meta_path: str,
                 output_path: str):
        self._dumper = None
        self._schema = pa.schema([pa.field('doubly_encrypted', pa.string())])
        super().__init__(meta_path, output_path)

    def _recv_process(self,
                      req: transmitter_pb.Request,
                      current_idx: IDX) -> (bytes, IDX):
        start_idx = IDX(req.start_file_idx, req.start_row_idx)
        end_idx = IDX(req.end_file_idx, req.end_row_idx)
        if end_idx.row_idx == 0:
            # it is the end of all data
            return None, end_idx
        # duplicated and preceded req does not need dump
        need_dump = start_idx == current_idx < end_idx
        encrypt_req = psu_pb.DataSyncRequest()
        encrypt_req.ParseFromString(req.payload)

        if need_dump:
            # OUTPUT_PATH/doubly_encrypted/<file_idx>.parquet
            file_path = pqu.encode_doubly_encrypted_file_path(self._output_path,
                                                              end_idx.file_idx)
            # dumper will be closed and renewed if it's a new file
            self._dumper = pqu.make_or_update_dumper(
                self._dumper, start_idx, end_idx, file_path, self._schema,
                flavor='spark')
            table = pa.Table.from_pydict(
                mapping={'doubly_encrypted': encrypt_req.doubly_encrypted},
                schema=self._schema)
            self._dumper.write_table(table)

        # if it's still the same file, we don't update meta to disk;
        # if it's a new file, update meta to the first line of the new file,
        #   s.t. we will start receiving from the new file if restarts.
        forward_idx = None if current_idx.file_idx == end_idx.file_idx \
            else IDX(end_idx.file_idx, 0)
        return psu_pb.DataSyncResponse().SerializeToString(), forward_idx

    def _stop(self, *args, **kwargs):
        if self._dumper:
            self._dumper.close()
