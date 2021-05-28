# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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

import unittest
import threading
import os
import time
import logging
import json
from datetime import datetime, timedelta
from multiprocessing import Process
import tensorflow.compat.v1 as tf
from tensorflow.compat.v1 import gfile
from queue import PriorityQueue
import enum
from tensorflow.core.example.feature_pb2 import FloatList, Features, Feature, \
                                                Int64List, BytesList

from tensorflow.core.example.example_pb2 import Example

import numpy as np

from fedlearner.data_join import (
    data_block_manager, common,
    raw_data_manifest_manager
)

from fedlearner.common import (
    db_client, common_pb2 as common_pb,
    data_join_service_pb2 as dj_pb
)

from fedlearner.data_join.data_block_manager import DataBlockBuilder
from fedlearner.data_join.raw_data_iter_impl.tf_record_iter import TfExampleItem
import fedlearner.trainer as flt

from graph_def.horizontal_leader import main as lm
from graph_def.horizontal_follower import main as fm

debug_mode = False
local_mnist_path = "./mnist.npz"
output_path = "./output"
total_worker_num = 1

child_env = os.environ.copy()
child_env["KVSTORE_USE_MOCK"] = "on"
child_env["KVSTORE_MOCK_DISK_SYNC"] = "on"
os.environ = child_env

class _Task(object):
    def __init__(self, name, weight, target, args=None, kwargs=None, daemon=None, force_quit=False):
        self.name = name
        self.weight = 0 - weight
        self._target = target
        self._args = args
        self._kwargs = kwargs
        self.force_quit = force_quit
        self._daemon = True
        self._lock = threading.Lock()
        self._task = None
        self._stop = False
        self._start_new()

    def _start_new(self):
        if self._task is not None and self._task.is_alive():
            logging.info(" %s is alive, no need to start new" % self.name)
            return
        self._task = Process(target=self._target, name=self.name,
                             args=self._args, kwargs=self._kwargs, daemon=self._daemon)
        self._task.start()
        logging.info("Task starts %s" % self.name)
        time.sleep(10)

    def __gt__(self, o):
        return self.weight > o.weight

    def kill(self, force = False):
        with self._lock:
            logging.info("Kill task %s", self.name)
            if self._task is None or not self._task.is_alive():
                return
            if force or self.force_quit:
                self._task.terminate()
            elif self._task.is_alive():
                raise ValueError("can not kill by force")
    def start(self):
        logging.info("begin to start")
        with self._lock:
            if self._stop:
                return
            if self._task.is_alive():
                logging.info("  %s is alive, no need to start" % self.name)
                return
            self._start_new()
            time.sleep(2)

    def is_alive(self):
        with self._lock:
            if self._task is None:
                return True
            return self._task.is_alive()

class _Signal(enum.Enum):
    KILL = 1
    RUN = 2

class _Event(object):
    def __init__(self, name, action, timeout):
        self.name = name
        self.action = action
        self.timeout = timeout
        self._start_time = time.time()
        self._trigged = False

    def handle(self, task):
        if self._trigged:
            return
        if self.timeout + self._start_time > time.time():
            return
        logging.info("handle event: %s=%s", task.name, self.action)
        self._trigged = True
        if self.action == _Signal.KILL:
            task.kill(True)
        elif self.action == _Signal.RUN:
            task.start()
        else:
            raise ValueError("unknown event %d" % self.action)

class _TaskScheduler(object):
    def __init__(self, timeout):
        self._task_queue = PriorityQueue()
        self._task_done = {}
        self._start_time = time.time()
        self._event_queue = []
        self._task_killed = {}
        self._keepalive = []
        self._timeout = timeout

    def submit(self, task):
        self._keepalive.append(task.name)
        self._task_queue.put(task)

    def recv(self, ev):
        self._event_queue.append(ev)

    def _handle_events(self, name, task):
        for e in self._event_queue:
            if e.name == name:
                e.handle(task)

    def bye(self):
        while not self._task_queue.empty():
            task = self._task_queue.get()
            if task.is_alive():
                task.kill(True)

    def run(self):
        while not self._task_queue.empty():
            task = []
            done = {}
            while not self._task_queue.empty():
                next_task = self._task_queue.get()
                logging.info("handle queue: %s", next_task.name)
                if not next_task.is_alive():
                    done[next_task.name] = next_task
                    continue
                self._handle_events(next_task.name, next_task)
                if next_task.is_alive():
                    task.append(next_task)
                else:
                    done[next_task.name] = next_task
            for t in task:
                self._task_queue.put(t)

            for k, v in done.items():
                if k in self._keepalive:
                    if v._task.exitcode != 0:
                        v.start()
                        self._task_queue.put(v)
                        continue
                self._task_done[k] = v
            time.sleep(1)
            if self._timeout + self._start_time < time.time():
                logging.info("stop!!!!!")
                return


def make_ckpt_dir(role, remote="local", rank=None):
    if rank is None:
        rank = "N"
    ckpt_path = "{}/{}_ckpt_{}_{}".format(output_path, remote, role, rank)
    exp_path = "{}/saved_model".format(ckpt_path)
    if gfile.Exists(ckpt_path):
        gfile.DeleteRecursively(ckpt_path)
    return ckpt_path, exp_path

def run_ps(port, env=None):
    if env is not None:
        os.environ = env
    addr = "0.0.0.0:{}".format(port)
    cluster_spec = tf.train.ClusterSpec({'local': {0: addr}})
    server = tf.train.Server(cluster_spec, job_name="local", task_index=0)
    server.join()

def run_lm(args, env=None):
    if env is not None:
        os.environ = env
    lm(args)

def run_fm(args, env=None):
    if env is not None:
        os.environ = env
    fm(args)


class TestHorizontalNNTraining(unittest.TestCase):
    def _create_data_block(self, data_source, partition_id, x, y, N):
        data_block_metas = []
        dbm = data_block_manager.DataBlockManager(data_source, partition_id)
        self.assertEqual(dbm.get_dumped_data_block_count(), 0)
        self.assertEqual(dbm.get_lastest_data_block_meta(), None)
        print(data_source.data_source_meta.name, data_source.output_base_dir,
              x.shape)
        chunk_size = x.shape[0] // N

        leader_index = 0
        follower_index = N * chunk_size * 10
        event_time = datetime.strptime('20210101', '%Y%m%d')
        delta = timedelta(minutes=1)
        for i in range(N):
            builder = DataBlockBuilder(
                common.data_source_data_block_dir(data_source),
                data_source.data_source_meta.name,
                partition_id, i,
                dj_pb.WriterOptions(output_writer="TF_RECORD",
                                    compressed_type="GZIP"), None
            )
            builder.set_data_block_manager(dbm)
            for j in range(chunk_size):
                feat = {}
                idx = i * chunk_size + j
                exam_id = '{}'.format(idx).encode()
                feat['example_id'] = Feature(
                    bytes_list=BytesList(value=[exam_id]))
                evt_time =int(event_time.strftime('%Y%m%d%H%M%S'))
                feat['event_time'] = Feature(
                    int64_list = Int64List(value=[evt_time])
                )
                feat['x'] = Feature(float_list=FloatList(value=list(x[idx])))
                if y is not None:
                    feat['y'] = Feature(int64_list=Int64List(value=[y[idx]]))

                feat['leader_index'] = Feature(
                    int64_list = Int64List(value=[leader_index])
                )
                feat['follower_index'] = Feature(
                    int64_list = Int64List(value=[follower_index])
                )
                example = Example(features=Features(feature=feat))
                builder.append_item(TfExampleItem(example.SerializeToString()),
                                    leader_index, follower_index)
                leader_index += 1
                follower_index += 1
                event_time += delta
            data_block_metas.append(builder.finish_data_block())
        self.max_index = follower_index
        return data_block_metas

    def _gen_ds_meta(self, role, index, data_source_name):
        data_source = common_pb.DataSource()
        data_source.data_source_meta.name = data_source_name
        data_source.data_source_meta.partition_num = 1
        data_source.data_source_meta.start_time = 0
        data_source.data_source_meta.end_time = 100000
        data_source.output_base_dir = "{}/{}_{}_{}/data_source/".format(
            output_path, data_source.data_source_meta.name, role, index)
        data_source.role = role
        return data_source

    def setUp(self):
        self.sche = _TaskScheduler(150)
        self.app_id = "test_trainer_v1"
        if debug_mode:
            (x, y), _ = tf.keras.datasets.mnist.load_data(local_mnist_path)
        else:
            (x, y), _ = tf.keras.datasets.mnist.load_data()

        x = x.reshape(x.shape[0], -1).astype(np.float32) / 255.0
        y = y.astype(np.int64)

        num_parts = 3
        num_sample = x.shape[0]
        chunk_size = (num_sample // 2) + 1
        xs = [x[:chunk_size], x[chunk_size:num_sample], x[:chunk_size]]
        ys = [y[:chunk_size], y[chunk_size:num_sample], y[:chunk_size]]

        self.kv_store = [None, None, None]
        self._local_data_source = "test-liuqi-mnist-local"
        data_source = [self._gen_ds_meta(common_pb.FLRole.Leader, 0, "test-liuqi-mnist-v1"),
                       self._gen_ds_meta(common_pb.FLRole.Leader, 1, self._local_data_source),
                       self._gen_ds_meta(common_pb.FLRole.Follower, 0, "test-liuqi-mnist-v1")]
        self._etcd_base_dirs = ["fedlearner0", "fedlearner0", "fedlearner2"]
        for role in range(num_parts):
            os.environ['ETCD_BASE_DIR'] = self._etcd_base_dirs[role]
            self.kv_store[role] = db_client.DBClient("etcd", True)
        self.data_source = data_source
        for role in range(num_parts):
            common.commit_data_source(self.kv_store[role], data_source[role])
            if gfile.Exists(data_source[role].output_base_dir):
                gfile.DeleteRecursively(data_source[role].output_base_dir)
            manifest_manager = raw_data_manifest_manager.RawDataManifestManager(
                        self.kv_store[role], data_source[role]
                    )
            partition_num = data_source[role].data_source_meta.partition_num
            #num_data_blocks = 100 if role == 1 else 2
            num_data_blocks = 100 if role == 1 else 20
            for i in range(partition_num):
                self._create_data_block(data_source[role], i,
                                        xs[role], ys[role], num_data_blocks)
                                        #x[role], y if role == 0 else None)

                manifest_manager._finish_partition('join_example_rep',
                        dj_pb.JoinExampleState.UnJoined, dj_pb.JoinExampleState.Joined,
                        -1, i)

    #@unittest.skip("demonstrating skipping")
    def test_remote_cluster(self):
        parser = flt.trainer_worker.create_argument_parser()
        parser.add_argument('--is-local-worker',
                            action='store_true',
                            help='is local worker')

        leader_master_address = "0.0.0.0:4051"
        leader_cluster_spec = {
            "clusterSpec": {
                "Master": ["0.0.0.0:4050"],
                "PS": ["0.0.0.0:4060"],
                "Worker": ["0.0.0.0:4070", "0.0.0.0:4071"]
            }
        }
        leader_cluster_spec_str = json.dumps(leader_cluster_spec)
        follower_master_address = "0.0.0.0:5051"
        follower_cluster_spec = {
            "clusterSpec": {
                "Master": ["0.0.0.0:5050"],
                "PS": ["0.0.0.0:5060"],
                "Worker": ["0.0.0.0:5070", "0.0.0.0:5071"]
            }
        }
        follower_cluster_spec_str = json.dumps(follower_cluster_spec)

        self.sche.bye()
        # launch leader/follower master
        ckpt_path, exp_path = make_ckpt_dir("leader", "remote")
        args = parser.parse_args((
            "--master",
            "--application-id", self.app_id,
            "--master-addr", leader_master_address,
            "--data-source", self.data_source[0].data_source_meta.name,
            "--local-data-source", self.data_source[1].data_source_meta.name,
            "--cluster-spec", leader_cluster_spec_str,
            "--checkpoint-path", ckpt_path,
            "--export-path", exp_path,
        ))
        child_env['ETCD_BASE_DIR'] = self._etcd_base_dirs[0]
        tml = _Task(name="RunLeaderMaster", target=run_lm, args=(args,),
                    weight=1, force_quit=True,
                    kwargs={'env' : child_env}, daemon=True)
        self.sche.submit(tml)

        ckpt_path, exp_path = make_ckpt_dir("follower", "remote")
        args = parser.parse_args((
            "--master",
            "--application-id", self.app_id,
            "--master-addr", follower_master_address,
            "--data-source", self.data_source[2].data_source_meta.name,
            "--cluster-spec", follower_cluster_spec_str,
            "--checkpoint-path", ckpt_path,
            "--export-path", exp_path,
        ))
        child_env['ETCD_BASE_DIR'] = self._etcd_base_dirs[2]
        tml = _Task(name="RunFollowerMaster", target=run_fm, args=(args,),
                    weight=1, force_quit=True,
                    kwargs={'env' : child_env}, daemon=True)
        self.sche.submit(tml)

        # launch leader/follower PS
        for i, addr in enumerate(leader_cluster_spec["clusterSpec"]["PS"]):
            psl = _Task(name="RunLeaderPS_%d"%i, target=run_ps, args=(addr, ),
                        weight=1, force_quit=True,
                        kwargs={'env' : child_env}, daemon=True)
            self.sche.submit(psl)
        for i, addr in enumerate(follower_cluster_spec["clusterSpec"]["PS"]):
            psl = _Task(name="RunFollowerPS_%d"%i, target=run_ps, args=(addr, ),
                        weight=1, force_quit=True,
                        kwargs={'env' : child_env}, daemon=True)
            self.sche.submit(psl)

        # launch leader/follower worker
        assert len(leader_cluster_spec["clusterSpec"]["Worker"]) == \
               len(follower_cluster_spec["clusterSpec"]["Worker"])
        for i in range(len(leader_cluster_spec["clusterSpec"]["Worker"])):
            _, leader_worker_port = \
                leader_cluster_spec["clusterSpec"]["Worker"][i].split(':')
            leader_worker_port = int(leader_worker_port) + 10000
            _, follower_worker_port = \
                follower_cluster_spec["clusterSpec"]["Worker"][i].split(':')
            follower_worker_port = int(follower_worker_port) + 10000

            # leader worker
            args = parser.parse_args((
                "--worker",
                "--application-id", self.app_id,
                "--master-addr", leader_master_address,
                "--local-addr", "0.0.0.0:%d"%leader_worker_port,
                "--peer-addr", "0.0.0.0:%d"%follower_worker_port,
                "--cluster-spec", leader_cluster_spec_str,
                "--worker-rank", str(i),
            ))
            ftm = _Task(name="RunLeaderWorker_%d"%i, target=run_lm, args=(args, ),
                        weight=1, force_quit=True,
                        kwargs={'env' : child_env}, daemon=True)
            self.sche.submit(ftm)

            # follower worker
            args = parser.parse_args((
                "--worker",
                "--application-id", self.app_id,
                "--master-addr", follower_master_address,
                "--local-addr", "0.0.0.0:%d"%follower_worker_port,
                "--peer-addr", "0.0.0.0:%d"%leader_worker_port,
                "--cluster-spec", follower_cluster_spec_str,
                "--worker-rank", str(i),
            ))
            ftm = _Task(name="RunLeaderWorker_%d"%i, target=run_fm, args=(args, ),
                        weight=1, force_quit=True,
                        kwargs={'env' : child_env}, daemon=True)
            self.sche.submit(ftm)
        local_worker_rank = len(leader_cluster_spec["clusterSpec"]["Worker"])
        for _ in range(len(leader_cluster_spec["clusterSpec"]["Worker"])):
            # leader worker
            args = parser.parse_args((
                "--worker",
                "--is-local-worker",
                "--application-id", self.app_id,
                "--master-addr", leader_master_address,
                "--cluster-spec", leader_cluster_spec_str,
                "--worker-rank", str(local_worker_rank),
            ))
            ftm = _Task(name="RunLeaderWorker_%d"%local_worker_rank,
                        target=run_lm,
                        args=(args, ),
                        weight=1, force_quit=True,
                        kwargs={'env' : child_env}, daemon=True)
            self.sche.submit(ftm)
            local_worker_rank += 1

        self.sche.run()

    def tearDown(self):
        self.sche.bye()
        if not debug_mode and gfile.Exists(output_path):
           gfile.DeleteRecursively(output_path)

if __name__ == '__main__':
    unittest.main()
