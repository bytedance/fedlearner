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
import random
import os
import time
import logging
from multiprocess import Process
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
    data_block_visitor, raw_data_manifest_manager
)

from fedlearner.common import (
    mysql_client, common_pb2 as common_pb,
    data_join_service_pb2 as dj_pb
)

from fedlearner.data_join.data_block_manager import DataBlockBuilder
from fedlearner.data_join.raw_data_iter_impl.tf_record_iter import TfExampleItem

from fedlearner.trainer_master.leader_tm import LeaderTrainerMaster
from fedlearner.trainer_master.follower_tm import FollowerTrainerMaster
from fedlearner.data_join.common import get_kvstore_config


from graph_def.leader import main as lm
from graph_def.follower import main as fm

debug_mode = False
local_mnist_path = "./mnist.npz"
output_path = "./output"
logging.getLogger().setLevel(logging.INFO)
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
        if isinstance(self._args[0], Args):
            logging.info("delete %s", self._args[0].export_path)
            if gfile.Exists(self._args[0].export_path):
                logging.info(" deleting")
                gfile.DeleteRecursively(self._args[0].export_path)
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

def run_leader_tm(app_id, data_source, port, env=None):
    if env is not None:
        os.environ = env 
    leader_tm = LeaderTrainerMaster(app_id, data_source,
                                    None, None,
                                    False,False, 1)
    leader_tm.run(listen_port=int(port))

def run_ps(port, env=None):
    if env is not None:
        os.environ = env
    addr = "0.0.0.0:{}".format(port)
    cluster_spec = tf.train.ClusterSpec({'local': {0: addr}})
    server = tf.train.Server(cluster_spec, job_name="local", task_index=0)
    server.join()

def run_follower_tm(app_id, data_source, port, env=None):
    if env is not None:
        os.environ = env
    follower_tm = FollowerTrainerMaster(app_id, data_source,
                                       None, None, False)
    follower_tm.run(listen_port=int(port))

def run_lm(args, env=None):
    if env is not None:
        os.environ = env
    lm(args)

def run_fm(args, env=None):
    if env is not None:
        os.environ = env
    fm(args)

class Args(object):
    def __init__(self, local_addr=None, peer_addr=None, app_id=None, master_addr=None,
            data_source=None, data_path=None, ckpt_path=None, export_path=None,
            start_time=None, end_time=None, tf_addr=None, cluster_spec=None, ps_addrs=None,
                 worker_rank=0):
        self.local_addr = local_addr
        self.peer_addr = peer_addr
        self.worker_rank = worker_rank
        self.cluster_spec = cluster_spec
        self.ps_addrs = ps_addrs
        self.data_source = data_source
        self.data_path = data_path
        self.application_id = app_id
        self.start_time = start_time
        self.end_time = end_time
        self.master_addr = master_addr
        self.tf_addr = tf_addr
        self.checkpoint_path = ckpt_path
        self.save_checkpoint_steps = 100
        self.save_checkpoint_secs = None
        self.export_path = export_path
        self.sparse_estimator = False
        self.mode = "train"
        self.summary_path = None
        self.summary_save_steps = None
        self.verbosity = 1;
        self.batch_size = 100
        self.learning_rate = 0.01


class TestNNTraining(unittest.TestCase):
    def _create_local_data(self, xl, xf, y):
        N = 10
        chunk_size = xl.shape[0]//N
        leader_worker_path = os.path.join(output_path, "data/leader")
        follower_worker_path = os.path.join(output_path, "data/follower")

        data_path = os.path.join(output_path, "data")
        if gfile.Exists(data_path):
            gfile.DeleteRecursively(data_path)
        os.makedirs(leader_worker_path)
        os.makedirs(follower_worker_path)

        for i in range(N):
            filename_l = os.path.join(leader_worker_path, '%02d.tfrecord'%i)
            filename_f = os.path.join(follower_worker_path, '%02d.tfrecord'%i)
            fl = tf.io.TFRecordWriter(filename_l)
            ff = tf.io.TFRecordWriter(filename_f)
            for j in range(chunk_size):
                idx = i*chunk_size + j
                features_l = {}
                features_l['example_id'] = Feature(
                    bytes_list=BytesList(value=[str(idx).encode('utf-8')]))
                features_l['y'] = Feature(int64_list=Int64List(value=[y[idx]]))
                features_l['x'] = Feature(float_list=FloatList(value=list(xl[idx])))
                fl.write(
                    Example(features=Features(feature=features_l)).SerializeToString())
                features_f = {}
                features_f['example_id'] = Feature(
                    bytes_list=BytesList(value=[str(idx).encode('utf-8')]))
                features_f['x'] = Feature(float_list=FloatList(value=list(xf[idx])))
                ff.write(
                    Example(features=Features(feature=features_f)).SerializeToString())
            fl.close()
            ff.close()

    def _create_data_block(self, data_source, partition_id, x, y):
        data_block_metas = []
        dbm = data_block_manager.DataBlockManager(data_source, partition_id)
        self.assertEqual(dbm.get_dumped_data_block_count(), 0)
        self.assertEqual(dbm.get_lastest_data_block_meta(), None)
        N = 200
        chunk_size = x.shape[0] // N

        leader_index = 0
        follower_index = N * chunk_size * 10
        for i in range(N):
            builder = DataBlockBuilder(
                common.data_source_data_block_dir(data_source),
                data_source.data_source_meta.name,
                partition_id, i,
                dj_pb.WriterOptions(output_writer="TF_RECORD"), None
            )
            builder.set_data_block_manager(dbm)
            for j in range(chunk_size):
                feat = {}
                idx =  i * chunk_size + j
                exam_id = '{}'.format(idx).encode()
                feat['example_id'] = Feature(
                    bytes_list=BytesList(value=[exam_id]))
                evt_time = random.randint(1, 1000)
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
            data_block_metas.append(builder.finish_data_block())
        self.max_index = follower_index
        return data_block_metas

    def _gen_ds_meta(self, role):
        data_source = common_pb.DataSource()
        data_source.data_source_meta.name = self.app_id
        data_source.data_source_meta.partition_num = 1
        data_source.data_source_meta.start_time = 0
        data_source.data_source_meta.end_time = 100000
        data_source.output_base_dir = "{}/{}_{}/data_source/".format(output_path,
                                                data_source.data_source_meta.name, role)
        data_source.role = role
        return data_source

    def setUp(self):
        self.sche = _TaskScheduler(30)
        self.kv_store = [None, None]
        self.app_id = "test_trainer_v1" 
        db_database, db_addr, db_username, db_password, db_base_dir = \
                get_kvstore_config("etcd")
        data_source = [self._gen_ds_meta(common_pb.FLRole.Leader),
                            self._gen_ds_meta(common_pb.FLRole.Follower)]
        for role in range(2):
           self.kv_store[role] = mysql_client.DBClient(data_source[role].data_source_meta.name,
               db_addr, db_username, db_password, db_base_dir, True)
        self.data_source = data_source
        (x, y) = (None, None)
        if debug_mode:
            (x, y), _ = tf.keras.datasets.mnist.load_data(local_mnist_path)
        else:
            (x, y), _ = tf.keras.datasets.mnist.load_data()
        x = x[:200,]

        x = x.reshape(x.shape[0], -1).astype(np.float32) / 255.0
        y = y.astype(np.int64)

        xl = x[:, :x.shape[1]//2]
        xf = x[:, x.shape[1]//2:]

        self._create_local_data(xl, xf, y)

        x = [xl, xf]
        for role in range(2):
            common.commit_data_source(self.kv_store[role], data_source[role])
            if gfile.Exists(data_source[role].output_base_dir):
                gfile.DeleteRecursively(data_source[role].output_base_dir)
            manifest_manager = raw_data_manifest_manager.RawDataManifestManager(
                        self.kv_store[role], data_source[role]
                    )
            partition_num = data_source[role].data_source_meta.partition_num
            for i in range(partition_num):
                self._create_data_block(data_source[role], i,
                                        x[role], y)
                                        #x[role], y if role == 0 else None)

                manifest_manager._finish_partition('join_example_rep',
                        dj_pb.JoinExampleState.UnJoined, dj_pb.JoinExampleState.Joined,
                        -1, i)

    #@unittest.skip("demonstrating skipping")
    def test_local_cluster(self):
        workers = []
        addr = ["localhost:20050", "localhost:20051"]

        role = 0
        ckpt_path, exp_path = make_ckpt_dir(role)
        args = Args(local_addr=addr[role],
                    peer_addr=addr[(role+1)%2],
                    app_id=self.app_id,
                    data_path=os.path.join(output_path, "data/leader"),
                    ckpt_path=ckpt_path,
                    export_path=exp_path)
        ftm = Process(name="RunLeaderTW", target=run_lm, args=(args, ),
                kwargs={'env' : child_env}, daemon=True)
        ftm.start()
        workers.append(ftm)

        role = 1
        ckpt_path, exp_path = make_ckpt_dir(role)
        args = Args(local_addr=addr[role],
                    peer_addr=addr[(role+1)%2],
                    app_id=self.app_id,
                    data_path=os.path.join(output_path, "data/follower"),
                    ckpt_path=ckpt_path,
                    export_path=exp_path)
        ftm = Process(name="RunFollowerTW", target=run_fm, args=(args, ),
                kwargs={'env' : child_env}, daemon=True)
        ftm.start()
        workers.append(ftm)

        for w in workers:
            w.join()

    #@unittest.skip("demonstrating skipping")
    def test_remote_cluster(self):
        self.sche.bye()
        master_addr = ["0.0.0.0:4050", "0.0.0.0:4051"]
        ps_addr     = ["0.0.0.0:5050", "0.0.0.0:5051"]
        ## launch master
        role = 0
        tml = _Task(name="RunLeaderTM", target=run_leader_tm, args=(self.app_id,
                self.data_source[role].data_source_meta.name,
                master_addr[role].split(":")[1],), weight=1, force_quit=True,
                kwargs={'env' : child_env}, daemon=True)
        self.sche.submit(tml)

        role = 1
        tml = _Task(name="RunFollowerTM", target=run_follower_tm, args=(self.app_id,
                self.data_source[role].data_source_meta.name,
                master_addr[role].split(":")[1], ),
                kwargs={'env' : child_env}, daemon=True, weight=1, force_quit=True)
        self.sche.submit(tml)

        ## launch PS
        for role in range(2):
            name = "PS_%d" % role
            psl = _Task(name=name, target=run_ps, args=(ps_addr[role].split(":")[1], ),
                          kwargs={'env' : child_env}, daemon=True, weight=1, force_quit=True)
            self.sche.submit(psl)

        ## launch worker

        worker_port, tf_port = 3050, 3150
        for rank in range(total_worker_num):
            port_fn = lambda port : ["0.0.0.0:%d" % port, "0.0.0.0:%d" % (port + 1)]
            worker_addr = port_fn(worker_port)
            tf_addr = port_fn(tf_port)

            worker_port += 2
            tf_port += 2

            role = 0
            ckpt_path, exp_path = make_ckpt_dir(role, "remote", rank)
            args = Args(local_addr=worker_addr[role],
                        peer_addr=worker_addr[(role+1)%2],
                        tf_addr=tf_addr[role],
                        ps_addrs=ps_addr[role],
                        app_id=self.app_id,
                        worker_rank = rank,
                        master_addr=master_addr[role],
                        ckpt_path=ckpt_path,
                        export_path=exp_path)
            ftm = _Task(name="RunLeaderTW" + str(rank), target=run_lm, args=(args, ),
                    kwargs={'env' : child_env}, daemon=True, weight=2)
            self.sche.submit(ftm)

            role = 1
            ckpt_path, exp_path = make_ckpt_dir(role, "remote", rank)
            args = Args(local_addr=worker_addr[role],
                        peer_addr=worker_addr[(role+1)%2],
                        tf_addr=tf_addr[role],
                        ps_addrs=ps_addr[role],
                        app_id=self.app_id,
                        worker_rank = rank,
                        master_addr=master_addr[role],
                        ckpt_path=ckpt_path,
                        export_path=exp_path)
            ftm = _Task(name="RunFollowerTW" + str(rank), target=run_fm, args=(args, ),
                    kwargs={'env' : child_env}, daemon=True, weight=2)
            self.sche.submit(ftm)

        # mimic the chaos monkey
        # case 1: worker restarts itself 
        #e = _Event("RunFollowerTW", _Signal.KILL, 10)
        #self.sche.recv(e)

        # case 1: as above
        #e = _Event("RunFollowerTM", _Signal.KILL, 10)
        #self.sche.recv(e)

        # case 2: master fails, but worker is running, master must not alloc data  
        #e = _Event("RunLeaderTM", _Signal.KILL, 35)
        #self.sche.recv(e)

        """case 3: master fails, then force worker to restart,  cluster get recovered 
           netstat  -apn | grep "0.0.0.0:40" | awk -F" " '{print $7}' | awk -F "\/" '{print $1}' | xargs kill
           netstat  -apn | grep "0.0.0.0:30" | awk -F" " '{print $7}' | awk -F "\/" '{print $1}' | xargs kill
           netstat  -apn | grep "0.0.0.0:50" | awk -F" " '{print $7}' | awk -F "\/" '{print $1}' | xargs kill
        """

        self.sche.run()

    def tearDown(self):
        self.sche.bye()
        #if not debug_mode and gfile.Exists(output_path):
        #    gfile.DeleteRecursively(output_path)

if __name__ == '__main__':
    unittest.main()
