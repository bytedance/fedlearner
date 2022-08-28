import typing

import pyarrow.parquet as pq

from fedlearner.data_join.visitors.visitor import Visitor


class ParquetVisitor(Visitor):
    def __init__(self,
                 batch_size: int = 1,
                 columns: typing.List[str] = None,
                 consume_remain: bool = False):
        self._consume_remain = consume_remain
        self._columns = columns
        self._current_batch = 0
        self._current_row = 0
        self._pq_file = None
        self._pq_iter = None
        self._num_full_batch = 0
        self._has_remain = 0
        super(ParquetVisitor, self).__init__(batch_size)

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
        self._current_row = 0
        return self._batch_iter()

    def _batch_iter(self):
        for batch in self._pq_iter:
            self._current_batch += 1
            self._current_row += batch.num_rows
            batch = batch.to_pydict()
            if self._consume_remain and self._has_remain \
                    and self._num_full_batch == self._current_batch:
                batch2 = next(self._pq_iter)
                self._current_row += batch2.num_rows
                batch2 = batch2.to_pydict()
                for k in batch.keys():
                    batch[k].extend(batch2[k])
            yield batch, \
                  self._file_infos[self._file_idx].idx, \
                  self.metadata.num_rows == self._current_row
