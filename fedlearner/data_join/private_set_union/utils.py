import pyarrow as pa
import pyarrow.parquet as pq
from tensorflow import gfile

from fedlearner.data_join.transmitter.utils import IDX


def _make_parquet_dumper(file_path: str,
                         schema: pa.Schema,
                         current_dumper: pq.ParquetWriter,
                         dump_idx: IDX,
                         end_idx: IDX) -> pq.ParquetWriter:
    if dump_idx.file_idx < end_idx.file_idx and current_dumper is not None:
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
