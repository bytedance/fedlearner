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

import os
import argparse
import json
import threading
import time

import tensorflow.compat.v1 as tf
from fedlearner.common import fl_logging, stats
from fedlearner.common.argparse_util import str_as_bool
from fedlearner.common import trainer_master_service_pb2 as tm_pb
from fedlearner.trainer.bridge import Bridge
from fedlearner.trainer.estimator import FLEstimator
from fedlearner.trainer.sparse_estimator import SparseFLEstimator
from fedlearner.trainer.trainer_master_client \
    import LocalTrainerMasterClient, TrainerMasterClient
from fedlearner.trainer.trainer_master \
    import LeaderTrainerMaster, FollowerTrainerMaster, ExportModelHook
from fedlearner.trainer.data_visitor import DataPathVisitor, DataSourceVisitor
from fedlearner.trainer.cluster_server import ClusterServer
from fedlearner.trainer._global_context import global_context as _gctx
from fedlearner.trainer.run_hooks import StepLossAucMetricsHook, StepMetricsHook #pylint: disable=unused-import


LEADER = "leader"
FOLLOER = "follower"


def create_argument_parser():
    parser = argparse.ArgumentParser(description='FedLearner Trainer.')
    parser.add_argument('--master',
                        action='store_true',
                        help='Run as trainer master only')
    parser.add_argument('--worker',
                        action='store_true',
                        help='Run as trainer worker only')
    parser.add_argument('--application-id',
                        type=str,
                        default=None,
                        help='application id on distributed training.')
    parser.add_argument('--master-addr',
                        type=str,
                        help='Address of trainer master, ' \
                             'in [IP]:[PORT] format. ' \
                             'Use local master for testing if set to None.')
    parser.add_argument('--local-addr',
                        type=str,
                        help='Listen address of the local bridge, ' \
                             'in [IP]:[PORT] format')
    parser.add_argument('--peer-addr',
                        type=str,
                        help='Address of peer\'s bridge, ' \
                             'in [IP]:[PORT] format')
    parser.add_argument('--cluster-spec',
                        type=str,
                        help='ClusterSpec description for master/ps/worker, '\
                            'in json format')
    parser.add_argument('--worker-rank',
                        type=int,
                        default=0,
                        help='the rank of this worker.')
    parser.add_argument('--ps-addrs',
                        type=str,
                        help='Comma-separated list of parameter server ' \
                             'addresses in [IP]:[PORT] format. ' \
                             'value for this argument must be identical ' \
                             'for all workers.')
    parser.add_argument('--data-source',
                        type=str,
                        help='path to data source for training')
    parser.add_argument('--local-data-source',
                        type=str,
                        help='path to local data source for training')
    parser.add_argument('--data-path',
                        type=str,
                        help='path to data block files for training.'
                             'Ignore if data-source is set')
    parser.add_argument('--start-date',
                        type=int,
                        help='training data start time')
    parser.add_argument('--end-date',
                        type=int,
                        help='training data end time')
    parser.add_argument('--local-start-date',
                        type=int,
                        help='local training data start time')
    parser.add_argument('--local-end-date',
                        type=int,
                        help='local training data end time')
    parser.add_argument('--epoch-num',
                        type=int,
                        default=1,
                        help='number of epoch for training, not '\
                             'support in online training')
    parser.add_argument('--shuffle',
                        type=str_as_bool,
                        default=False, const=True, nargs='?',
                        help='shuffle the data block or not')
    parser.add_argument('--export-path',
                        type=str,
                        help='Path to save exported models.')
    parser.add_argument('--checkpoint-path',
                        type=str,
                        help='path to save and load model checkpoints.')
    parser.add_argument('--load-checkpoint-path',
                        type=str,
                        help='path to load model checkpoints.')
    parser.add_argument('--load-checkpoint-filename',
                        type=str,
                        help='filename to load model checkpoints, ' \
                             'relative path to load-checkpoint-path ' \
                             'or checkpoint-path')
    parser.add_argument('--load-checkpoint-filename-with-path',
                        type=str,
                        help='filename with path to load model checkpoints')
    parser.add_argument('--save-checkpoint-steps',
                        type=int,
                        default=1000,
                        help='Number of steps between checkpoints.')
    parser.add_argument('--save-checkpoint-secs',
                        type=int,
                        help='Number of secs between checkpoints.')
    parser.add_argument('--summary-path',
                        type=str,
                        help='Path to save summary files used by tensorboard.')
    parser.add_argument('--summary-save-steps',
                        type=int,
                        help='Number of steps to save summary files.')
    parser.add_argument('--summary-save-secs',
                        type=int,
                        help='Number of secs to save summary files.')
    parser.add_argument('--sparse-estimator',
                        type=str_as_bool,
                        default=False, const=True, nargs='?',
                        help='Whether using sparse estimator.')
    parser.add_argument('--mode',
                        type=str,
                        default='train',
                        help='Train or eval.')
    parser.add_argument('--loglevel',
                        type=str,
                        default=None,
                        help="Specify verbosity level. It can be one of "
                             "'debug', 'info', 'warning', 'error', 'critical'")

    return parser

def _run_master(role,
                args,
                input_fn,
                model_fn,
                serving_input_receiver_fn,
                export_model_hook=None):
    if not args.master_addr:
        raise ValueError("master-addr is required")
    mode = args.mode.lower()

    try:
        cluster_spec = _create_cluster_spec(args, require_ps=True)
    except ValueError:
        cluster_spec = None

    cluster_server = None
    if cluster_spec:
        cluster_server = ClusterServer(cluster_spec, "master")

    checkpoint_filename_with_path = _get_checkpoint_filename_with_path(args)
    data_visitor = _create_data_visitor(args)
    master_factory = LeaderTrainerMaster \
        if role == LEADER else FollowerTrainerMaster

    master = master_factory(
             cluster_server,
             data_visitor,
             mode,
             model_fn,
             input_fn,
             serving_input_receiver_fn,
             checkpoint_filename_with_path,
             checkpoint_path=args.checkpoint_path,
             save_checkpoint_steps=args.save_checkpoint_steps,
             save_checkpoint_secs=args.save_checkpoint_secs,
             summary_path=args.summary_path,
             summary_save_steps=args.summary_save_steps,
             summary_save_secs=args.summary_save_secs,
             export_path=args.export_path,
             sparse_estimator=args.sparse_estimator,
             export_model_hook=export_model_hook)
    master.run_forever(args.master_addr)

def _run_worker(role, args, input_fn, model_fn):
    if not args.master_addr:
        raise ValueError("master-addr is required")
    mode = args.mode.lower()

    worker_type = tm_pb.WorkerType.REMOTE_WORKER
    bridge = None
    if args.is_local_worker:
        worker_type = tm_pb.WorkerType.LOCAL_WORKER
    else:
        if not args.local_addr:
            raise ValueError("local-addr is required")
        if not args.peer_addr:
            raise ValueError("peer-addr is required")
        bridge = Bridge(role,
                        int(args.local_addr.split(':')[1]),
                        args.peer_addr,
                        args.application_id,
                        args.worker_rank)

    fl_logging.info("Start worker rank %d with type %s", args.worker_rank,
                    worker_type)

    cluster_spec = _create_cluster_spec(args, require_ps=True)
    cluster_server = ClusterServer(cluster_spec,
                                   "worker",
                                   task_index=args.worker_rank)
    trainer_master = TrainerMasterClient(args.master_addr,
                                         args.worker_rank,
                                         worker_type)
    if not trainer_master.worker_register(cluster_spec.as_cluster_def()):
        return

    estimator_factory = SparseFLEstimator \
        if args.sparse_estimator else FLEstimator
    estimator = estimator_factory(cluster_server,
                                  trainer_master,
                                  bridge,
                                  role,
                                  model_fn,
                                  is_chief=args.worker_rank == 0)

    if mode == 'train':
        estimator.train(input_fn)
    elif mode == 'eval':
        estimator.evaluate(input_fn)

    if bridge:
        trainer_master.worker_complete(bridge.terminated_at)
    else:
        trainer_master.worker_complete(int(time.time()))
    trainer_master.wait_master_complete()

def _run_local(role,
               args,
               input_fn,
               model_fn,
               serving_input_receiver_fn,
               export_model_hook=None):
    if not args.local_addr:
        raise ValueError("local-addr is required")
    if not args.peer_addr:
        raise ValueError("peer-addr is required")
    mode = args.mode.lower()

    cluster_spec = _create_cluster_spec(args)
    cluster_server = ClusterServer(cluster_spec, "local")

    # run master
    checkpoint_filename_with_path = _get_checkpoint_filename_with_path(args)
    data_visitor = _create_data_visitor(args)
    master_factory = LeaderTrainerMaster \
        if role == LEADER else FollowerTrainerMaster
    local_master = master_factory(
             cluster_server,
             data_visitor,
             mode,
             model_fn,
             input_fn,
             serving_input_receiver_fn,
             checkpoint_filename_with_path,
             checkpoint_path=args.checkpoint_path,
             save_checkpoint_steps=args.save_checkpoint_steps,
             save_checkpoint_secs=args.save_checkpoint_secs,
             summary_path=args.summary_path,
             summary_save_steps=args.summary_save_steps,
             summary_save_secs=args.summary_save_secs,
             export_path=args.export_path,
             sparse_estimator=args.sparse_estimator,
             export_model_hook=export_model_hook)
    master_thread = threading.Thread(target=local_master.run_forever)
    master_thread.setDaemon(True)
    master_thread.start()

    # run worker
    trainer_master = LocalTrainerMasterClient(local_master, 0)
    if not trainer_master.worker_register():
        return
    bridge = Bridge(role,
                    int(args.local_addr.split(':')[1]),
                    args.peer_addr,
                    args.application_id,
                    0)

    estimator_factory = \
        SparseFLEstimator if args.sparse_estimator else FLEstimator
    estimator = estimator_factory(cluster_server,
                                  trainer_master,
                                  bridge,
                                  role,
                                  model_fn)

    if mode == 'train':
        estimator.train(input_fn)
    elif mode == 'eval':
        estimator.evaluate(input_fn)

    trainer_master.worker_complete(bridge.terminated_at)
    trainer_master.wait_master_complete()

def _get_checkpoint_filename_with_path(args):
    checkpoint_filename_with_path = None

    if args.load_checkpoint_filename_with_path:
        checkpoint_filename_with_path = args.load_checkpoint_filename_with_path

    elif args.load_checkpoint_filename:
        load_checkpoint_path = args.load_checkpoint_path or args.checkpoint_path
        if not load_checkpoint_path:
            raise ValueError("load_checkpoint_path or checkpoint_path is "
                             "required when provide load_checkpoint_filename")
        checkpoint_filename_with_path = \
            os.path.join(load_checkpoint_path, args.checkpoint_filename)
    elif args.load_checkpoint_path or args.checkpoint_path:
        load_checkpoint_path = args.load_checkpoint_path or args.checkpoint_path
        checkpoint_filename_with_path = \
            tf.train.latest_checkpoint(load_checkpoint_path)

    if not checkpoint_filename_with_path:
        return None

    if not tf.train.checkpoint_exists(checkpoint_filename_with_path):
        raise RuntimeError("not a valid checkpoint file: %s" \
                           %checkpoint_filename_with_path)

    return checkpoint_filename_with_path

def _create_cluster_spec(args, require_ps=False):
    cluster_spec_dict = dict()
    if args.cluster_spec:
        cluster_spec = json.loads(args.cluster_spec)["clusterSpec"]
        if "Master" in cluster_spec \
            and isinstance(cluster_spec['Master'], list):
            cluster_spec_dict["master"] = cluster_spec["Master"]
        if "PS" in cluster_spec \
            and isinstance(cluster_spec['PS'], list):
            cluster_spec_dict["ps"] = cluster_spec["PS"]
        if "Worker" in cluster_spec \
            and isinstance(cluster_spec['Worker'], list):
            cluster_spec_dict["worker"] = cluster_spec["Worker"]
    elif args.ps_addrs:
        cluster_spec_dict["ps"] = \
            [addr.strip() for addr in args.ps_addrs.split(",")]
    if require_ps:
        if "ps" not in cluster_spec_dict or len(cluster_spec_dict["ps"]) == 0:
            raise ValueError("ps is required")

    return tf.train.ClusterSpec(cluster_spec_dict)

def _create_data_visitor(args):
    visitor = None
    start_date = int(args.start_date) if args.start_date else None
    end_date = int(args.end_date) if args.end_date else None
    local_start_date = int(args.local_start_date) if args.local_start_date \
        else None
    local_end_date = int(args.local_end_date) if args.local_end_date \
        else None
    if args.data_source:
        visitor = DataSourceVisitor(args.data_source,
                                    start_date=start_date,
                                    end_date=end_date,
                                    local_data_source=args.local_data_source,
                                    local_start_date=local_start_date,
                                    local_end_date=local_end_date,
                                    epoch_num=args.epoch_num,
                                    shuffle=args.shuffle)
    elif args.data_path:
        visitor = DataPathVisitor(args.data_path,
                                  epoch_num=args.epoch_num,
                                  shuffle=args.shuffle)
    if not visitor:
        raise ValueError("cannot found any data to train, "
                   "please specify --data-source or --data-path")
    return visitor

def train(role,
          args,
          input_fn,
          model_fn,
          serving_input_receiver_fn,
          export_model_hook=None):
    if isinstance(args.application_id, str):
        _gctx.job = args.application_id

    if not isinstance(role, str) or role.lower() not in (LEADER, FOLLOER):
        raise ValueError("--role must set one of %s or %s"%(LEADER, FOLLOER))

    if args.loglevel:
        fl_logging.set_level(args.loglevel)

    if export_model_hook is not None:
        if not isinstance(export_model_hook, ExportModelHook):
            raise ValueError("model_export_hook must be a "
                             "ExportModelHook, but get %r"%export_model_hook)

    mode = args.mode.lower()
    if mode not in ('train', 'eval'):
        raise ValueError("--mode must set one of 'train' or 'eval'")

    if not (args.master or args.worker):
        _gctx.task = "local"
        _gctx.task_index = 0
    elif args.master:
        _gctx.task = "master"
        _gctx.task_index = 0
    elif args.worker:
        _gctx.task = "worker"
        _gctx.task_index = args.worker_rank
    else:
        raise ValueError("duplication specify --master and --worker")

    stats.enable_cpu_stats(_gctx.stats_client)
    stats.enable_mem_stats(_gctx.stats_client)

    if _gctx.task == "local":
        _run_local(role, args, input_fn, model_fn,
                   serving_input_receiver_fn,
                   export_model_hook=export_model_hook)
    elif _gctx.task == "master":
        _run_master(role, args, input_fn, model_fn,
                    serving_input_receiver_fn,
                    export_model_hook=export_model_hook)
    elif _gctx.task == "worker":
        _run_worker(role, args, input_fn, model_fn)
    else:
        raise ValueError("unknow task mode: %s"%_gctx.task)
