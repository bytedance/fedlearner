import os
import typing

import pyarrow as pa
import pyarrow.parquet as pq
from tensorflow import gfile

from fedlearner.data_join.transmitter.utils import IDX
from fedlearner.data_join.private_set_union.idx_utils import is_new_file


class ParquetBatchReader:
    def __init__(self,
                 file_path: str,
                 file_idx: int,
                 batch_size: int,
                 columns: typing.List[str] = None):
        self._pq_file = pq.ParquetFile(file_path)
        self._reader = self._pq_file.iter_batches(batch_size, columns=columns)
        self.idx = IDX(file_idx, 0)

    @property
    def file_idx(self):
        return self.idx.file_idx

    @property
    def row_idx(self):
        return self.idx.row_idx

    @property
    def metadata(self):
        return self._pq_file.metadata

    def __next__(self):
        batch = next(self._reader)
        self.idx.row_idx += batch.num_rows
        return batch

    def __iter__(self):
        return self


class ParquetBatchDumper:
    def __init__(self,
                 file_path: str,
                 schema: pa.Schema,
                 dumper_id: int = 0,
                 flavor: str = None,
                 overwrite: bool = True):
        self._writer = pq.ParquetWriter(file_path, schema, flavor=flavor)
        self._file_size = 0
        self._schema = schema
        # this id is used to determine what is the name of next file
        self.id = dumper_id
        if overwrite and gfile.Exists(file_path):
            gfile.DeleteRecursively(file_path)

    def __len__(self):
        return self._file_size

    def dump_table(self,
                   table: pa.Table):
        self._writer.write_table(table)
        self._file_size += table.num_rows

    def close(self):
        self._writer.close()


def encode_doubly_encrypted_file_path(output_path: str, file_id: [int, str]):
    return os.path.join(str(output_path),
                        'doubly_encrypted',
                        str(file_id) + 'parquet')


def get_batch(reader: ParquetBatchReader,
              root_path: str,
              files: typing.List[str],
              start_idx: IDX,
              row_num: int,
              columns: typing.List[str],
              consume_remain: bool = False) -> (pa.RecordBatch,
                                                        ParquetBatchReader):
    file_path = os.path.join(root_path, files[start_idx.file_idx])
    if reader is None or reader.file_idx != start_idx.file_idx:
        reader = ParquetBatchReader(
            file_path, start_idx.file_idx, row_num, columns)

    batch = None
    while not batch:
        try:
            # if this file contains fewer rows than row_idx, jump to next file.
            # NOTE: reader.idx won't be the last row if it's the last file.
            if reader.idx <= start_idx and \
                    reader.metadata.row_nums <= start_idx.row_idx:
                raise StopIteration
            # some file might not contain any row, so `not batch` is needed
            while reader.idx <= start_idx or not batch:
                batch = next(reader)
        except StopIteration:
            # if it is the last file
            if reader.file_idx == len(files) - 1:
                return [], reader
            # starting from a new file
            file_path = os.path.join(root_path, files[reader.file_idx + 1])
            # open a new file. note that the file idx is incremented
            reader = ParquetBatchReader(
                file_path, reader.file_idx + 1, row_num, columns)
            batch = None
    batches = [batch]
    if consume_remain and reader.metadata.num_rows - reader.row_idx < row_num:
        batches.append(next(reader))
    return batches, reader


def make_or_update_dumper(dumper: [pq.ParquetWriter, None],
                          start_idx: IDX,
                          end_idx: IDX,
                          file_path: str,
                          schema: pa.Schema,
                          flavor: str = None) -> pq.ParquetWriter:
    if is_new_file(start_idx, end_idx) or dumper is None:
        if dumper is not None:
            dumper.close()
        dumper = pq.ParquetWriter(file_path, schema, flavor=flavor)
    return dumper





