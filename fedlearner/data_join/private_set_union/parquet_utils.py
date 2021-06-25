import os

import pyarrow as pa
import pyarrow.parquet as pq
from tensorflow import gfile


def list_parquet_files(dir_path: str):
    return [f for f in gfile.ListDirectory(dir_path) if f.endswith('.parquet')]


def make_dirs_if_not_exists(file_path: str):
    if not gfile.Exists(os.path.dirname(file_path)):
        gfile.MakeDirs(os.path.dirname(file_path))


def clear_file_if_exists(file_path: str):
    if gfile.Exists(os.path.dirname(file_path)):
        gfile.DeleteRecursively(file_path)


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
