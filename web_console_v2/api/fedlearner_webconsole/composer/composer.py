# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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
import logging
import threading
import traceback
from datetime import datetime
from envs import Envs

from sqlalchemy import func
from sqlalchemy.engine import Engine

from fedlearner_webconsole.composer.strategy import SingletonStrategy
from fedlearner_webconsole.proto import composer_pb2
from fedlearner_webconsole.proto.composer_pb2 import PipelineContextData
from fedlearner_webconsole.utils import pp_time
from fedlearner_webconsole.db import get_session
from fedlearner_webconsole.composer.runner import global_runner_fn
from fedlearner_webconsole.composer.models import SchedulerItem, ItemStatus, SchedulerRunner, RunnerStatus
from fedlearner_webconsole.composer.pipeline import PipelineExecutor
from fedlearner_webconsole.composer.op_locker import OpLocker
from fedlearner_webconsole.composer.thread_reaper import ThreadReaper
import grpc
from concurrent import futures
from grpc_health.v1 import health
from grpc_health.v1 import health_pb2_grpc


class ComposerConfig(object):

    def __init__(
        self,
        runner_fn: dict,
        name: str = 'default_name',
        worker_num: int = 20,
    ):
        """Config for composer

        Args:
            runner_fn (dict): runner functions
            name (str): composer name
            worker_num (int): number of worker doing heavy job
        """
        self.runner_fn = runner_fn
        self.name = name
        self.worker_num = worker_num


class Composer(object):
    LOOP_INTERVAL = 5

    def __init__(self, config: ComposerConfig):
        """Composer

        Args:
            config: config
        """
        self.config = config
        self.name = config.name
        self.db_engine = None
        self.thread_reaper = ThreadReaper(worker_num=config.worker_num)
        self.pipeline_executor = PipelineExecutor(
            thread_reaper=self.thread_reaper,
            db_engine=self.db_engine,
            runner_fns=config.runner_fn,
        )
        self.lock = threading.Lock()
        self._stop = False
        self._loop_thread = None
        self._grpc_server_thread = None

    def run(self, db_engine: Engine):
        self.db_engine = db_engine
        self.pipeline_executor.db_engine = db_engine
        logging.info(f'[composer] starting {self.name}...')
        self._loop_thread = threading.Thread(target=self._loop, args=[], daemon=True)
        self._loop_thread.start()
        self._grpc_server_thread = threading.Thread(target=self._run, args=[], daemon=True)
        self._grpc_server_thread.start()

    def wait_for_termination(self):
        self._loop_thread.join()
        self._grpc_server_thread.join()

    def _run(self):
        grpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
        health_pb2_grpc.add_HealthServicer_to_server(health.HealthServicer(), grpc_server)
        grpc_server.add_insecure_port(f'[::]:{Envs.COMPOSER_LISTEN_PORT}')
        grpc_server.start()
        grpc_server.wait_for_termination()

    def _loop(self):
        while True:
            with self.lock:
                if self._stop:
                    logging.info('[composer] stopping...')
                    self.thread_reaper.stop(True)
                    return
            try:
                logging.debug(f'[composer] checking at {datetime.now()}')
                self._check_items()
                self._check_init_runners()
                self._check_running_runners()
            except Exception as e:  # pylint: disable=broad-except
                logging.error(f'[composer] something wrong, exception: {e}, ' f'trace: {traceback.format_exc()}')
            pp_time.sleep(self.LOOP_INTERVAL)

    def stop(self):
        logging.info(f'[composer] stopping {self.name}...')
        with self.lock:
            self._stop = True
        if self._loop_thread is not None:
            self._loop_thread.join(timeout=self.LOOP_INTERVAL * 2)

    def _check_items(self):
        with get_session(self.db_engine) as session:
            items = session.query(SchedulerItem).filter_by(status=ItemStatus.ON.value).all()
            for item in items:
                if not SingletonStrategy(session).should_run(item):
                    continue

                pipeline: composer_pb2.Pipeline = item.get_pipeline()
                if pipeline.version != 2:
                    logging.error(f'[Composer] Invalid pipeline in item {item.id}')
                    item.status = ItemStatus.OFF.value
                    session.commit()
                    continue
                runner = SchedulerRunner(item_id=item.id)
                runner.set_pipeline(pipeline)
                runner.set_context(PipelineContextData())
                session.add(runner)

                # NOTE: use sqlalchemy's `func.now()` to let it handles
                # the timezone.
                item.last_run_at = func.now()
                if not item.cron_config:
                    # finish run-once item automatically
                    item.status = ItemStatus.OFF.value

                logging.info(f'[composer] insert runner, item_id: {item.id}')
                session.commit()

    def _check_init_runners(self):
        with get_session(self.db_engine) as session:
            init_runner_ids = session.query(SchedulerRunner.id).filter_by(status=RunnerStatus.INIT.value).all()
            # TODO: support priority
        for runner_id, *_ in init_runner_ids:
            # if thread_reaper is full, skip this round and
            # wait next checking
            if self.thread_reaper.is_full():
                logging.info('[composer] thread_reaper is full now, waiting for other item finish')
                return
            lock_name = f'check_init_runner_{runner_id}_lock'
            check_lock = OpLocker(lock_name, self.db_engine).try_lock()
            if not check_lock:
                logging.error(f'[composer] failed to lock, ignore current init_runner_{runner_id}')
                continue
            with get_session(self.db_engine) as session:
                runner: SchedulerRunner = session.query(SchedulerRunner).get(runner_id)
                # update status
                runner.start_at = func.now()
                runner.status = RunnerStatus.RUNNING.value
                pipeline: composer_pb2.Pipeline = runner.get_pipeline()
                if pipeline.version != 2:
                    logging.error(f'[Composer] Invalid pipeline in runner {runner.id}')
                    runner.status = RunnerStatus.FAILED.value
                    session.commit()
                    continue
                try:
                    logging.info(f'[composer] update runner, status: {runner.status}, '
                                 f'pipeline: {runner.pipeline}, '
                                 f'context: {runner.context}')
                    if check_lock.is_latest_version() and \
                            check_lock.update_version():
                        session.commit()
                    else:
                        logging.error(f'[composer] {lock_name} is outdated, ignore updates to database')
                except Exception as e:  # pylint: disable=broad-except
                    logging.error(f'[composer] failed to update init runner status, exception: {e}')
                    session.rollback()

    def _check_running_runners(self):
        with get_session(self.db_engine) as session:
            running_runner_ids = session.query(SchedulerRunner.id).filter_by(status=RunnerStatus.RUNNING.value).all()
        for runner_id, *_ in running_runner_ids:
            if self.thread_reaper.is_full():
                logging.info('[composer] thread_reaper is full now, waiting for other item finish')
                return
            lock_name = f'check_running_runner_{runner_id}_lock'
            check_lock = OpLocker(lock_name, self.db_engine).try_lock()
            if not check_lock:
                logging.error(f'[composer] failed to lock, ' f'ignore current running_runner_{runner_id}')
                continue
            with get_session(self.db_engine) as session:
                # TODO: restart runner if exit unexpectedly
                runner = session.query(SchedulerRunner).get(runner_id)
                pipeline = runner.get_pipeline()
                if pipeline.version != 2:
                    logging.error(f'[Composer] Invalid pipeline in runner {runner.id}')
                    runner.status = RunnerStatus.FAILED.value
                    session.commit()
                    continue
                # If the runner is running, we always try to run it.
                self.pipeline_executor.run(runner_id)


composer = Composer(config=ComposerConfig(runner_fn=global_runner_fn(), name='scheduler for fedlearner webconsole'))
