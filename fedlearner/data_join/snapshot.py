import os
import json
import threading
import tempfile
import logging
from collections import OrderedDict
from collections import namedtuple
from enum import Enum

import tensorflow.compat.v1 as tf

from fedlearner.common import dfs_client as dfsc

SNAP_BASE_DIR="/snaphot"
SNAP_SUFFIX = ".snap"
SNAP_ANCHOR_FILE = "anchor_snap_id"

class CheckpointDataType(Enum):
    RAWDATA = 1
    DATASOURCE = 2
    TRAINING = 3

def decode_checkpoint_file(filename):
    parts = filename.split("/")
    assert len(parts) < 3, 'Invalid file[%s] to decode'%filename
    snap_id = parts[-1].split(".")[0]
    task_flow = parts[-2]
    return task_flow, snap_id

class SingletonMetaclass(type):
    def __init__(self, *args, **kwargs):
        self.__instance = None
        super().__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        if self.__instance is None:
            self.__instance = super(
                SingletonMetaclass, self).__call__(*args, **kwargs)
            return self.__instance
        else:
            return self.__instance

CheckpointMeta = namedtuple('CheckpointMeta',
                            ['current_snap_id', 'parent_snap_id',
                             'anchor_snap_id', 'create_time',
                             'update_time', 'commited'])

FileCheckpointItem = namedtuple('FileCheckpointItem', ['filename', 'snap_id'])
class CheckpointData(object):
    def __init__(self, snap_id, task_name, data):
        self._snap_id = snap_id
        self._task_name = task_name
        self._data = data #type:  FileCheckpointItem

    def encode(self, data):
        return json.dumps(data)

    def decode(self, data):
        raise NotImplementedError

class RawDataCheckpointData(CheckpointData):
    def decode(self):
        data = json.loads(self._data)
        # job_id 
        return int(data)


class DataSourceCheckpointData(CheckpointData):
    def decode(self):
        data = json.loads(self._data)
        # datablock_index: snap_id
        return dict(data)

class TrainingCheckpointData(CheckpointData):
    def decode(self):
        data = json.loads(self._data)
        # model_ckpt: snap_id 
        return dict(data)


class CheckpointManager(metaclass=SingletonMetaclass):
    class Checkpoint(object):
        def __init__(self, path, snap_id, json_meta):
            assert json_meta is not None, 'Invalid checkpoint'
            assert snap_id == json_meta['current_snap_id']
            self._path = path
            self._meta = json_meta
            self._data = OrderedDict()
            assert self.check_valid(path)

        def __getitem__(self, key):
            assert key in self._meta
            return self._meta[key]

        def add_context(self, task_name, key, value):
            if task_name not in self._data:
                self._data[task_name] = {}
            self._data[task_name][key] = value
            return True

        def get_context(self, task_name):
            assert task_name in self._data,\
                    "invalid task name[%s] when recovering"%task_name
            assert key in self._data[task_name],\
                    "invalid key[%s] when recovering"%key
            return self._data[task_name]

        def commit(self):
            json_meta = json.dumps(self._meta)
            tmp_file = tempfile.TemporaryFile()
            with tf.gfile.Open(tmp_file, "w") as f:
                f.write(json_meta)
            base_path = self.encode_checkpoint_path(
                self._meta.storage_root, self._meta.task_flow)
            tf.gfile.Rename(tmp_file, os.path.join(base_path, SNAP_SUFFIX))

            json_data = json.dumps(self._data)
            tmp_file_data = tempfile.TemporaryFile()
            with tf.gfile.Open(tmp_file_data, "w") as f:
                f.write(json_data)
            tf.gfile.Rename(tmp_file_data, os.path.join(base_path, ".data"))

        def __getattr__(self, key):
            return self._meta.get(key)

        def check_valid(self, snap_path):
            self._meta['anchor_snap_id'] < self._meta['parent_snap_id']\
                    and not tf.gfile.Exists(os.path.join(snap_path, "_lock"))

    def __init__(self, task_flow):
        self._storage_root = os.environ.get('STORAGE_ROOT_PATH', '/fedlearner'),
        self._task_flow = task_flow
        self._lock = threading.Lock()
        self._latest_ckpt = self.get_checkpoint(None)
        self._global_anchor_snap_id = self.get_anchor_snap()
        self._reset_mark = False
        if self._global_anchor_snap_id != self._latest_ckpt.anchor_snap_id:
           self._reset_mark = True 
           self.reset()

    @property
    def reset_mark(self):
        return self._reset_mark

    @reset_mark.setter
    def reset_mark(self, b_mark):
        self._reset_mark = b_mark

    def get_checkpoint(self, snap_id):
        meta = None
        with self._lock:
            if not snap_id:
                base_path = self.encode_checkpoint_path()
                snap_list = tf.gfile.Glob(
                    os.path.join(base_path, "*", SNAP_SUFFIX))
                if not snap_list:
                    ### FIXME 
                    meta = {
                        'current_snap_id': 0,
                        'anchor_snap_id': 0,
                        'parent_snap_id': 0,
                        'create_time': 0,
                        'update_time': 0
                    }
                    snap_id = 0
                    json_meta = json.dumps(meta)
                    fpath = self.encode_checkpoint_file(snap_id)
                    with tf.gfile.Open(fpath, "w") as f:
                        f.write(json_meta)
                    snap_list = [fpath]
                snap_list.sort()
                task_flow, snap_id = decode_checkpoint_file(snap_list[-1])
                snap_id = int(snap_id)
            snap_path = self.encode_checkpoint_file(snap_id)
            meta = json.loads(snap_path)
            return self.Checkpoint(snap_path, snap_id, meta)

    def is_lock(self):
        with self._lock:
            return tf.gfile.Exists(self.encode_checkpoint_file(''))


    def encode_checkpoint_path(self, storage_root=None, flow_name=None):
        if storage_root is None:
            storage_root = self._storage_root
        if flow_name is None:
            flow_name = self._task_flow
        return os.path.join(storage_root, SNAP_BASE_DIR, flow_name)

    def encode_checkpoint_file(self, snap_id):
        return os.path.join(self.encode_checkpoint_path(),
                            snap_id, SNAP_SUFFIX)

    def acquire(self):
        """ Allocate a new checkpoint """
        with self._lock:
            next_snap_id = self._latest_ckpt.current_snap_id + 1
            ## finalize the last snap
            self._latest_ckpt.commit()
            self._latest_ckpt == self.get_checkpoint(None)

    def add_context(self, task_name, key, data):
        return self._latest_ckpt.add_context(task_name, key, data)

    def get_context(self, task_name):
        value = self._latest_ckpt.get_context(task_name)

    def commit(self):
        self._latest_ckpt.commit()

    def lock_file(self):
        path = self.encode_checkpoint_path()
        return os.path.join(path, "_lock")

    def get_anchor_snap(self):
        anchor_path = self.encode_checkpoint_path()
        anchor_path = os.path.join(anchor_path, SNAP_ANCHOR_FILE)
        if not tf.gfile.Exists(anchor_path):
            return 0
        with tf.gfile.Open(anchor_path, "r") as f:
            data = f.read()
            return int(data)

    def set_anchor_snap(self,snap_id):
        anchor_path = self.encode_checkpoint_path()
        anchor_path = os.path.join(anchor_path, SNAP_ANCHOR_FILE)
        with tf.gfile.Open(anchor_path, "w") as f:
            f.write(snap_id)

    def reset(self):
        """Rollback to a old checkpoint"""
        snap_id = self.get_anchor_snap()
        with self._lock:
            if tf.gfile.Exists(self.lock_file()):
                return False

        assert snap_id is not None
        with tf.gfile.Open(self.lock_file(), "w") as f:
            f.write(str(self._latest_ckpt.current_snap_id))

        ckpt = self.get_checkpoint(snap_id)
        ### commit current checkpoint
        self._latest_ckpt.commit()
        self._latest_ckpt = ckpt
        tf.gfile.Remove(self.lock_file())
