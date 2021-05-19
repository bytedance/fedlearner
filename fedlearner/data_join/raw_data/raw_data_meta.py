import logging
import json
import os


from tensorflow.compat.v1 import gfile
from tensorflow.python.lib.io import file_io


class MetaKeys:
    job_id = "job_id"
    fpath = "fpath"


def raw_data_meta_path(base_path):
    meta_file_name = "job.meta.csv"
    return os.path.join(base_path, meta_file_name)


class RawDataMeta:
    def __init__(self, meta_file):
        self._meta_file = meta_file

        if gfile.Exists(meta_file):
            with gfile.Open(meta_file, 'r') as f:
                self._metas = json.load(f)
        else:
            self._metas = []

        self._job_id = -1
        self._processed_fpath = set()

        for meta in self._metas:
            self._job_id = max(self._job_id,
                               int(meta[MetaKeys.job_id]))
            for fpath in meta[MetaKeys.fpath]:
                self._processed_fpath.add(fpath)
        logging.info("Found RawData meta with max job_id %d, number of "
                     "processed file is %d",
                     self._job_id, len(self._processed_fpath))

    @property
    def job_id(self):
        return self._job_id

    @property
    def processed_fpath(self):
        return self._processed_fpath

    def add_meta(self, job_id, paths):
        record = {
            MetaKeys.job_id: job_id,
            MetaKeys.fpath: paths,
        }
        self._processed_fpath.update(paths)
        self._job_id = max(self._job_id, job_id)
        self._metas.append(record)

    def persist(self):
        data = json.dumps(self._metas)
        file_io.atomic_write_string_to_file(self._meta_file, data)
