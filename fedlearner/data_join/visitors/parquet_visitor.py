import typing

import pyarrow.parquet as pq

from fedlearner.data_join.visitors.visitor import Visitor


class ParquetVisitor(Visitor):
    def __init__(self,
                 file_info: typing.List[str],
                 batch_size: int,
                 columns: typing.List[str] = None):
        super(ParquetVisitor, self).__init__(file_info, batch_size)
        self._columns = columns

    def create_iter(self, file_path):
        pq_file = pq.ParquetFile(file_path)
        return pq_file.iter_batches(self._batch_size,
                                    columns=self._columns)

