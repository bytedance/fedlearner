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

import json
import logging
import time
import threading
import traceback

from sqlalchemy import func
from sqlalchemy.engine import Engine

from fedlearner_webconsole.db import get_session
from fedlearner_webconsole.composer.runner import global_runner_fn
from fedlearner_webconsole.composer.interface import IItem, IRunner
from fedlearner_webconsole.composer.models import Context, decode_context, \
    ContextEncoder, SchedulerItem, ItemStatus, SchedulerRunner, RunnerStatus
from fedlearner_webconsole.composer.op_locker import OpLocker
from fedlearner_webconsole.composer.thread_reaper import ThreadReaper


class ComposerConfig(object):
    def __init__(
        self,
        runner_fn: dict,
        name='default_name',
        worker_num=10,
    ):
        """Config for composer

        Args:
            runner_fn: runner functions
            name: composer name
            worker_num: number of worker doing heavy job
        """
        self.runner_fn = runner_fn
        self.name = name
        self.worker_num = worker_num


class Pipeline(object):
    def __init__(self, name: str, deps: [str], meta: dict):
        """Define the deps of scheduler item

        Fields:
             name: pipeline name
             deps: items to be processed in order
             meta: additional info
        """
        self.name = name
        self.deps = deps
        self.meta = meta


class PipelineEncoder(json.JSONEncoder):
    def default(self, obj):
        return obj.__dict__


class Composer(object):
    def __init__(self, config: ComposerConfig):
        """Composer

        Args:
            config: config
        """
        self.config = config
        self.name = config.name
        self.runner_fn = config.runner_fn
        self.db_engine = None
        self.thread_reaper = ThreadReaper(worker_num=config.worker_num)
        self.lock = threading.Lock()
        self._stop = False

    def run(self, db_engine: Engine):
        self.db_engine = db_engine
        logging.info(f'[composer] starting {self.name}...')
        loop = threading.Thread(target=self._loop, args=[], daemon=True)
        loop.start()

    def _loop(self):
        while True:
            with self.lock:
                if self._stop:
                    logging.info('[composer] stopping...')
                    self.thread_reaper.stop(True)
                    return
            try:
                self._check_items()
                self._check_init_runners()
                self._check_running_runners()
            except Exception as e:  # pylint: disable=broad-except
                logging.error(f'[composer] something wrong, exception: {e}, '
                              f'trace: {traceback.format_exc()}')
            time.sleep(5)

    def stop(self):
        logging.info(f'[composer] stopping {self.name}...')
        with self.lock:
            self._stop = True

    # collect items
    def collect(self, name: str, items: [IItem], options: dict):
        if len(name) == 0:
            return
        with get_session(self.db_engine) as session:
            # check name if exists
            existed = session.query(SchedulerItem).filter_by(name=name).first()
            if existed:
                return
            item = SchedulerItem(
                name=name,
                pipeline=PipelineEncoder().encode(
                    self._build_pipeline(name, items, options)),
            )
            session.add(item)
            try:
                session.commit()
            except Exception as e:  # pylint: disable=broad-except
                logging.error(f'[composer] failed to create scheduler_item, '
                              f'name: {name}, exception: {e}')
                session.rollback()

    def _check_items(self):
        with get_session(self.db_engine) as session:
            items = session.query(SchedulerItem).filter_by(
                status=ItemStatus.ON.value).all()
            for item in items:
                if not item.need_run():
                    continue
                # NOTE: use `func.now()` to let sqlalchemy handles
                # the timezone.
                item.last_run_at = func.now()
                pp = Pipeline(**(json.loads(item.pipeline)))
                context = Context(data=pp.meta,
                                  internal={},
                                  db_engine=self.db_engine)
                runner = SchedulerRunner(
                    item_id=item.id,
                    pipeline=item.pipeline,
                    context=ContextEncoder().encode(context),
                )
                session.add(runner)
                try:
                    logging.info(
                        f'[composer] insert runner, item_id: {item.id}')
                    session.commit()
                except Exception as e:  # pylint: disable=broad-except
                    logging.error(
                        f'[composer] failed to create scheduler_runner, '
                        f'item_id: {item.id}, exception: {e}')
                    session.rollback()

    def _check_init_runners(self):
        with get_session(self.db_engine) as session:
            init_runners = session.query(SchedulerRunner).filter_by(
                status=RunnerStatus.INIT.value).all()
            # TODO: support priority
            for runner in init_runners:
                # if thread_reaper is full, skip this round and
                # wait next checking
                if self.thread_reaper.is_full():
                    return
                lock_name = f'check_init_runner_{runner.id}_lock'
                check_lock = OpLocker(lock_name, self.db_engine).try_lock()
                if not check_lock:
                    logging.error(f'[composer] failed to lock, '
                                  f'ignore current init_runner_{runner.id}')
                    continue
                pipeline = Pipeline(**(json.loads(runner.pipeline)))
                context = decode_context(val=runner.context,
                                         db_engine=self.db_engine)
                # find the first job in pipeline
                first = pipeline.deps[0]
                # update status
                runner.start_at = func.now()
                runner.status = RunnerStatus.RUNNING.value
                output = json.loads(runner.output)
                output[first] = {'status': RunnerStatus.RUNNING.value}
                runner.output = json.dumps(output)
                # record current running job
                context.set_internal('current', first)
                runner.context = ContextEncoder().encode(context)
                # start runner
                runner_fn = self._find_runner_fn(first)
                self.thread_reaper.enqueue(name=lock_name,
                                           timeout=-1,
                                           fn=runner_fn,
                                           context=context)
                try:
                    logging.info(
                        f'[composer] update runner, status: {runner.status}, '
                        f'pipeline: {runner.pipeline}, '
                        f'output: {output}, context: {runner.context}')
                    if check_lock.is_latest_version() and \
                            check_lock.update_version():
                        session.commit()
                    else:
                        logging.error(f'[composer] {lock_name} is outdated, '
                                      f'ignore updates to database')
                except Exception as e:  # pylint: disable=broad-except
                    logging.error(f'[composer] failed to update init runner'
                                  f'status, exception: {e}')
                    session.rollback()

    def _check_running_runners(self):
        with get_session(self.db_engine) as session:
            running_runners = session.query(SchedulerRunner).filter_by(
                status=RunnerStatus.RUNNING.value).all()
            for runner in running_runners:
                if self.thread_reaper.is_full():
                    return
                lock_name = f'check_running_runner_{runner.id}_lock'
                check_lock = OpLocker(lock_name, self.db_engine).try_lock()
                if not check_lock:
                    logging.error(f'[composer] failed to lock, '
                                  f'ignore current running_runner_{runner.id}')
                    continue
                # TODO: restart runner if exit unexpectedly
                pipeline = Pipeline(**(json.loads(runner.pipeline)))
                output = json.loads(runner.output)
                context = decode_context(val=runner.context,
                                         db_engine=self.db_engine)
                current = context.internal['current']
                runner_fn = self._find_runner_fn(current)
                # check status of current one
                status, current_output = runner_fn.result(context)
                if status == RunnerStatus.RUNNING:
                    continue  # ignore
                if status == RunnerStatus.DONE:
                    output[current] = {'status': RunnerStatus.DONE.value}
                    context.set_internal(f'output_{current}', current_output)
                    current_idx = pipeline.deps.index(current)
                    if current_idx == len(pipeline.deps) - 1:  # all done
                        runner.status = RunnerStatus.DONE.value
                        runner.end_at = func.now()
                    else:  # run next one
                        next_one = pipeline.deps[current_idx + 1]
                        output[next_one] = {
                            'status': RunnerStatus.RUNNING.value
                        }
                        context.set_internal('current', next_one)
                        next_runner_fn = self._find_runner_fn(next_one)
                        self.thread_reaper.enqueue(name=lock_name,
                                                   timeout=-1,
                                                   fn=next_runner_fn,
                                                   context=context)
                elif status == RunnerStatus.FAILED:
                    # TODO: abort now, need retry
                    output[current] = {'status': RunnerStatus.FAILED.value}
                    context.set_internal(f'output_{current}', current_output)
                    runner.status = RunnerStatus.FAILED.value
                    runner.end_at = func.now()

                runner.pipeline = PipelineEncoder().encode(pipeline)
                runner.output = json.dumps(output)
                runner.context = ContextEncoder().encode(context)
                try:
                    logging.info(
                        f'[composer] update runner, status: {runner.status}, '
                        f'pipeline: {runner.pipeline}, '
                        f'output: {output}, context: {runner.context}')
                    if check_lock.is_latest_version():
                        if check_lock.update_version():
                            session.commit()
                    else:
                        logging.error(f'[composer] {lock_name} is outdated, '
                                      f'ignore updates to database')
                except Exception as e:  # pylint: disable=broad-except
                    logging.error(f'[composer] failed to update running '
                                  f'runner status, exception: {e}')
                    session.rollback()

    def _find_runner_fn(self, runner_id: str) -> IRunner:
        item_type, item_id = runner_id.split('_')
        return self.runner_fn[item_type](int(item_id))

    @staticmethod
    def _build_pipeline(name: str, items: [IItem], options: dict) -> Pipeline:
        deps = []
        for item in items:
            deps.append(f'{item.type().value}_{item.get_id()}')
        return Pipeline(name=name, deps=deps, meta=options)


composer = Composer(config=ComposerConfig(
    runner_fn=global_runner_fn, name='scheduler for fedlearner webconsole'))
