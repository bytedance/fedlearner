# Copyright 2021 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
"""file lock."""
import logging
import os
import time
import threading
import uuid

from tensorflow.compat.v1 import gfile
import tensorflow.compat.v1 as tf


def atomic_create_file(file_path):
    """Writes to path atomically, by writing to temp file and renaming it."""
    temp_path = "{}.{}_{}".format(file_path, 'tmp', uuid.uuid4().hex)
    gfile.MkDir(temp_path)
    with gfile.Open(os.path.join(temp_path, 'dummy'), 'w') as _file:
        _file.write('t')
    try:
        gfile.Rename(temp_path, file_path)
        return True
    except tf.OpError:
        if gfile.Exists(temp_path):
            gfile.DeleteRecursively(temp_path)
        return False


def atomic_remove_file(file_path):
    """Writes to path atomically, by writing to temp file and renaming it."""
    temp_path = "{}.{}_{}".format(file_path, 'tmp', uuid.uuid4().hex)
    while True:
        try:
            gfile.Rename(file_path, temp_path)
            gfile.DeleteRecursively(temp_path)
            break
        except tf.OpError:
            logging.warning("Remove %s file lock failed, waiting 0.05s...",
                            file_path)
            time.sleep(0.05)


class TimeOutError(OSError):
    def __init__(self, lock_file):
        self._lock_file = lock_file
        super().__init__()

    def __str__(self):
        return "Acquire lock {} time out".format(self._lock_file)


class FileLock(object):
    def __init__(self, lock_file, timeout=-1, poll_interval=0.05):
        self._lock_file = lock_file
        self._timeout = timeout
        self._poll_interval = poll_interval
        self._is_locked = False
        self._internal_lock = threading.Lock()
        # reenterable counter
        self._lock_count = 0

    @property
    def is_locked(self):
        return self._is_locked

    def _lock(self):
        self._is_locked = atomic_create_file(self._lock_file)

    def acquire(self, timeout=None, poll_interval=None):
        if not timeout:
            timeout = self._timeout
        if not poll_interval:
            poll_interval = self._poll_interval

        with self._internal_lock:
            self._lock_count += 1

        start_time = time.time()
        try:
            while True:
                with self._internal_lock:
                    if not self._is_locked:
                        self._lock()
                    if self._is_locked:
                        break
                if 0 <= timeout <= (time.time() - start_time):
                    raise TimeOutError(self._lock_file)
                logging.info("Acquire lock %s failed, waiting %s second...",
                             self._lock_file, poll_interval)
                time.sleep(poll_interval)
        except Exception as e:
            logging.warning(e)
            with self._internal_lock:
                self._lock_count = max(0, self._lock_count - 1)
            raise e

    def release(self):
        with self._internal_lock:
            if not self._is_locked:
                return
            self._lock_count = max(0, self._lock_count - 1)
            if self._lock_count == 0:
                atomic_remove_file(self._lock_file)
                self._is_locked = False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
