import os
import tensorflow.compat.v1 as tf
import logging
import time
from datetime import datetime
from fedlearner.common.db_client import DBClient
from fedlearner.data_join import common as djc

def do_reset(file_or_dir, backup=False):
    if not tf.gfile.Exists(file_or_dir):
        return
    if tf.gfile.IsDirectory(file_or_dir):
        tf.gfile.DeleteRecursively(file_or_dir)
    else:
        tf.gfile.Remove(file_or_dir)

def do_batch_reset(file_list, backup=False):
    for f in file_list:
        do_reset(f, backup)

def walk(file_or_dir, dt):
    queue = [file_or_dir]
    dels = []
    lastest_dt = 0
    while queue:
        fd = queue.pop()
        if tf.gfile.IsDirectory(fd):
            sub_files = tf.gfile.ListDirectory(fd)
            queue.extend(sub_files)
        else:
            fstat = tf.gfile.Stat(fd)
            if fstat.mtime_nsec/1e9 > dt:
                dels.append(fd)
    return dels

class Checkpoint(object):
    def __init__(self, storage_root, task_name):
        self._storage_root = storage_root
        self._task_name = task_name
        kvstore_type = 'dfs'
        self._kvstore = DBClient(kvstore_type, False)

    def reset(self, dt):
        raise NotImplementedError
    def find_ckpt(self, base_dir):
        raise NotImplementedError

class RawDataCheckpoint(Checkpoint):
    def __init__(self, storage_root, task_name):
        super(RawDataCheckpoint, self).__init__(storage_root, task_name)

    def reset(self, dt):
        map_path = os.path.join(self._storage_root, 'raw_data', self._task_name, 'map')
        map_files = walk(map_path, dt)
        reduce_path = os.path.join(self._storage_root, 'raw_data', self._task_name, 'reduce')
        map_files = walk(reduce_path, dt)
        return None

    def find_ckpt(self, base_dir):
        return None

class DataSourceCheckpoint(Checkpoint):
    def __init__(self, storage_root, task_name):
        super(DataSourceCheckpoint, self).__init__(storage_root, task_name)
        self._data_source = djc.retrieve_data_source(self._kvstore, task_name)

    def reset(self):
        p1 = os.path.join(self._storage_root, 'data_source', self._task_name, 'data_block')
        ckpt_files = walk(p1, dt)
        do_batch_reset(ckpt_files)
        p2 = os.path.join(self._storage_root, 'data_source', self._task_name, 'example_dump')
        jobs_files = walk(p2, dt)
        do_batch_reset(jobs_files)

        p2 = os.path.join(self._storage_root, 'data_source', self._task_name, 'raw_data_dir')
        jobs_files = walk(p2, dt)
        do_batch_reset(jobs_files)

        p2 = os.path.join(self._storage_root, 'data_source', self._task_name, 'dumped_example_id_anchor')
        jobs_files = walk(p2, dt)
        do_batch_reset(jobs_files)

        p2 = os.path.join(self._storage_root, 'data_source', self._task_name, 'checkpoints')
        jobs_files = walk(p2, dt)
        do_batch_reset(jobs_files)
        return p2

    def find_ckpt(self, base_dir):
        ckpt = os.path.join(base_dir, "*.ckpt")
        ckpt_path_list = djc.glob(ckpt).sort()
        if len(ckpt_path_list) > 0:
            f = tf.gfile.Stat(ckpt_path_list[-1])
            return f.mtime_nsec/1e9
        return None

def TrainingCheckpoint(Checkpoint):
    def __init__(self, storage_root, task_name):
        super(TrainingCheckpoint, self).__init__(storage_root, task_name, dt)
    def reset(self, dt):
        ckpt_path = os.path.join(self._storage_root, 'job_output', self._task_name, 'checkpoints')
        ckpt_files = walk(ckpt, dt)
        do_batch_reset(ckpt_files)
        jobs = os.path.join(self._storage_root, 'job_output', self._task_name, 'exported_models')
        jobs_files = walk(reduce_path, dt)
        do_batch_reset(jobs_files)
        return ckpt_path

    def find_ckpt(self, base_dir):
        ckpt = path.join(base_dir, "*.ckpt")
        ckpt_path_list = common.glob(ckpt).sort()
        if len(ckpt_path_list) > 0:
            f = tf.gfile.Stat(ckpt_path_list[-1])
            return f.mtime_nsec/1e9
        return None

if __name__ == "__main__":
    raw_data_name = os.environ.get("RAW_DATA_NAME", None)
    data_source_name = os.environ.get("DATA_SOURCE_NAME", None)
    training_name = os.environ.get("TRAINING_NAME", None)
    str_dt = os.environ.get('CHECKPOINT_DT', None)
    storage_root = os.environ.get('STORAGE_ROOT', None)
    assert storage_root is not None
    dt = time.mktime(time.strptime(dt, "%Y%m%d%H%M%S"))
    assert isinstance(dt, datetime), "Invalid datetime %s"%str_dt

    if training_name:
        task = TrainingCheckpoint()
        base_dir = task.reset(dt)
        dt = task.find_ckpt(base_dir)
    if data_source_name:
        task = DataSourceCheckpoint()
        base_dir = task.reset(dt)
        dt = task.find_ckpt(base_dir)
    if raw_data_name:
        task = RawDataCheckpoint()
        base_dir = task.reset(dt)
        #dt = task.find_ckpt(base_dir)

