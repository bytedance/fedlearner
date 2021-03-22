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

import multiprocessing
import os
import threading
import unittest

from tensorflow.compat.v1 import gfile
from fedlearner.common.file_lock import FileLock, atomic_create_file, \
    TimeOutError


class TestFileLock(unittest.TestCase):
    def setUp(self):
        self._base_dir = './tmp'
        gfile.MakeDirs(self._base_dir)
        self._lock_file = '{}/file.lock'.format(self._base_dir)
        if gfile.Exists(self._lock_file):
            gfile.DeleteRecursively(self._lock_file)

    def tearDown(self):
        if gfile.Exists(self._base_dir):
            gfile.DeleteRecursively(self._base_dir)

    def test_atomic_create_lock_file_mt(self):
        t_lock = threading.Lock()
        counter = []

        def func():
            succeeded = atomic_create_file(self._lock_file)
            with t_lock:
                if succeeded:
                    counter.append(1)

        num_threads = 200
        threads = [threading.Thread(target=func) for _ in range(num_threads)]
        for i in range(num_threads):
            threads[i].start()
        for i in range(num_threads):
            threads[i].join()
        self.assertEqual(len(counter), 1)

    def test_atomic_create_lock_file_mp(self):
        def worker(proc_idx, ret_dict):
            ret_dict[proc_idx] = atomic_create_file(self._lock_file)

        num_processes = 100
        manager = multiprocessing.Manager()
        return_dict = manager.dict()
        jobs = []
        for i in range(num_processes):
            p = multiprocessing.Process(target=worker, args=(i, return_dict))
            jobs.append(p)
            p.start()
        for proc in jobs:
            proc.join()
        counter = 0
        for i in range(num_processes):
            if return_dict[i]:
                counter += 1
        self.assertEqual(counter, 1)

    def test_simple_lock(self):
        with FileLock(self._lock_file) as lock:
            self.assertTrue(gfile.Exists(self._lock_file))
            self.assertTrue(lock.is_locked)
        self.assertFalse(gfile.Exists(self._lock_file))

        lock = FileLock(self._lock_file)
        lock.acquire()
        self.assertTrue(gfile.Exists(self._lock_file))
        self.assertTrue(lock.is_locked)
        lock.release()
        self.assertFalse(lock.is_locked)
        self.assertFalse(gfile.Exists(self._lock_file))

    def test_nested(self):
        lock = FileLock(self._lock_file)
        lock.acquire()
        lock.acquire()
        self.assertTrue(gfile.Exists(self._lock_file))
        self.assertTrue(lock.is_locked)
        lock.release()
        self.assertTrue(gfile.Exists(self._lock_file))
        self.assertTrue(lock.is_locked)
        lock.release()
        self.assertFalse(gfile.Exists(self._lock_file))
        self.assertFalse(lock.is_locked)

    def test_multiple_thread(self):
        lock = FileLock(self._lock_file)

        def func():
            for _ in range(1, 10):
                with lock:
                    self.assertTrue(lock.is_locked)

        num_threads = 100
        threads = [threading.Thread(target=func) for _ in range(num_threads)]
        for i in range(num_threads):
            threads[i].start()
        for i in range(num_threads):
            threads[i].join()
        self.assertFalse(lock.is_locked)

    def test_multiple_thread2(self):
        def func():
            lock = FileLock(self._lock_file)
            for _ in range(1, 10):
                with lock:
                    self.assertTrue(lock.is_locked)
            self.assertFalse(lock.is_locked)

        num_threads = 100
        threads = [threading.Thread(target=func) for _ in range(num_threads)]
        for i in range(num_threads):
            threads[i].start()
        for i in range(num_threads):
            threads[i].join()

    def test_multiple_process(self):
        target_file = os.path.join(self._base_dir, "target")

        def worker(proc_idx):
            lock = FileLock(self._lock_file)
            with lock:
                self.assertTrue(lock.is_locked)
                with gfile.GFile(target_file, 'a+') as f:
                    f.write("{}\n".format(proc_idx))
            self.assertFalse(lock.is_locked)

        num_processes = 100
        jobs = []
        for i in range(num_processes):
            p = multiprocessing.Process(target=worker, args=(i, ))
            jobs.append(p)
            p.start()
        for proc in jobs:
            proc.join()

        with gfile.GFile(target_file, 'r') as f:
            wanted_set = set([int(w.strip()) for w in f.readlines()])
        for i in range(num_processes):
            self.assertTrue(i in wanted_set)

    def test_timeout(self):
        lock1 = FileLock(self._lock_file)
        lock2 = FileLock(self._lock_file, timeout=0.5)

        lock1.acquire()
        self.assertTrue(lock1.is_locked)
        self.assertFalse(lock2.is_locked)

        self.assertRaises(TimeOutError, lock2.acquire)
        lock1.release()
        lock2.acquire()
        self.assertFalse(lock1.is_locked)
        self.assertTrue(lock2.is_locked)


if __name__ == '__main__':
    unittest.main()
