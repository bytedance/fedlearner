import os
import typing

import pyarrow as pa
import pyarrow.parquet as pq
from tensorflow import gfile


class ParquetBatchReader:
    def __init__(self,
                 file_path: str,
                 batch_size: int,
                 columns: typing.List[str] = None):
        self._pq_file = pq.ParquetFile(file_path)
        self._reader = self._pq_file.iter_batches(batch_size, columns=columns)
        self.file_path = file_path
        self._row = 0

    @property
    def metadata(self):
        return self._pq_file.metadata

    @property
    def row(self):
        return self._row

    @property
    def finished(self):
        return self._pq_file.metadata.num_rows == self._row

    def __next__(self):
        batch = next(self._reader)
        self._row += batch.num_rows
        return batch

    def __iter__(self):
        return self


def encode_doubly_encrypted_file_path(output_path: str, file_id: [int, str]):
    return os.path.join(str(output_path),
                        'doubly_encrypted',
                        str(file_id) + '.parquet')


def encode_quadruply_encrypted_file_path(output_path: str, file_id: [int, str]):
    return os.path.join(str(output_path),
                        'quadruply_encrypted',
                        str(file_id) + '.parquet')


def make_dirs_if_not_exists(file_path: str):
    if not gfile.Exists(os.path.dirname(file_path)):
        gfile.MakeDirs(os.path.dirname(file_path))


def clear_file_if_exists(file_path: str):
    if gfile.Exists(os.path.dirname(file_path)):
        gfile.DeleteRecursively(file_path)


def get_batch(reader: ParquetBatchReader,
              file_path: str,
              row_num: int,
              columns: typing.List[str],
              consume_remain: bool = False) -> (pa.RecordBatch,
                                                ParquetBatchReader):
    if reader is None or reader.file_path != file_path:
        reader = ParquetBatchReader(file_path, row_num, columns)
    try:
        batch = next(reader)
    except StopIteration:
        return [], reader

    batches = [batch]
    if consume_remain and reader.metadata.num_rows - reader.row < row_num:
        batches.append(next(reader))
    return batches, reader


def make_or_update_dumper(dumper: [pq.ParquetWriter, None],
                          file_path: str,
                          schema: pa.Schema,
                          flavor: str = None) -> pq.ParquetWriter:
    if not dumper or dumper.where != file_path:
        if dumper:
            dumper.close()
            clear_file_if_exists(file_path)
        make_dirs_if_not_exists(file_path)
        dumper = pq.ParquetWriter(file_path, schema, flavor=flavor)
    return dumper
