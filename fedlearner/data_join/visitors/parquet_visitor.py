import typing

import pyarrow.parquet as pq

from fedlearner.data_join.visitors.visitor import Visitor
import fedlearner.common.transmitter_service_pb2 as tsmt_pb


class ParquetVisitor(Visitor):
    def __init__(self,
                 file_info: typing.List[str],
                 batch_size: int,
                 consume_remain: bool = False,
                 columns: typing.List[str] = None):
        self._consume_remain = consume_remain
        self._columns = columns
        self._batch_idx = 0
        self._current_batch = 0
        self._pq_file = None
        self._pq_iter = None
        self._num_full_batch = 0
        self._has_remain = 0
        super(ParquetVisitor, self).__init__(file_info, batch_size)

    @property
    def metadata(self):
        if not self._pq_file:
            return None
        return self._pq_file.metadata

    def create_iter(self, file_path):
        self._pq_file = pq.ParquetFile(file_path)
        self._pq_iter = self._pq_file.iter_batches(self._batch_size,
                                                   columns=self._columns)
        self._num_full_batch = self.metadata.num_rows // self._batch_size
        self._has_remain = (self.metadata.num_rows % self._batch_size) > 0
        self._current_batch = 0
        return self._batch_iter()

    def _batch_iter(self):
        for batch in self._pq_iter:
            b = [batch]
            self._batch_idx += 1
            self._current_batch += 1
            if self._consume_remain and self._has_remain \
                    and self._num_full_batch == self._current_batch:
                batch2 = next(self._pq_iter)
                b.append(batch2)
            yield b, tsmt_pb.BatchInfo(file_idx=self._file_idx,
                                       batch_idx=self._batch_idx)
