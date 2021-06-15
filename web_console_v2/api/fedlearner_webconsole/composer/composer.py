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
from datetime import datetime
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.engine import Engine

from fedlearner_webconsole.db import get_session
from fedlearner_webconsole.composer.runner import global_runner_fn
from fedlearner_webconsole.composer.runner_cache import RunnerCache
from fedlearner_webconsole.composer.interface import IItem
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
    def __init__(self, name: str, deps: List[str], meta: dict):
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
    # attributes that you can patch
    MUTABLE_ITEM_KEY = ['interval_time', 'retry_cnt']

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
        self.runner_cache = RunnerCache(runner_fn=config.runner_fn)
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
                logging.debug(f'[composer] checking at {datetime.now()}')
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

    def collect(self,
                name: str,
                items: List[IItem],
                metadata: dict,
                interval: int = -1):
        """Collect scheduler item

        Args:
             name: item name, should be unique
             items: specify dependencies
             metadata: pass metadata to share with item dependencies each other
             interval: if value is -1, it's run-once job, or run
                every interval time in seconds
        """
        if len(name) == 0:
            return
        valid_interval = interval == -1 or interval >= 10
        if not valid_interval:  # seems non-sense if interval is less than 10
            raise ValueError('interval should not less than 10 if not -1')
        with get_session(self.db_engine) as session:
            # check name if exists
            existed = session.query(SchedulerItem).filter_by(name=name).first()
            if existed:
                return
            item = SchedulerItem(
                name=name,
                pipeline=PipelineEncoder().encode(
                    self._build_pipeline(name, items, metadata)),
                interval_time=interval,
            )
            session.add(item)
            try:
                session.commit()
            except Exception as e:  # pylint: disable=broad-except
                logging.error(f'[composer] failed to create scheduler_item, '
                              f'name: {name}, exception: {e}')
                session.rollback()

    def finish(self, name: str):
        """Finish item

        Args:
            name: item name
        """
        with get_session(self.db_engine) as session:
            existed = session.query(SchedulerItem).filter_by(
                name=name, status=ItemStatus.ON.value).first()
            if not existed:
                return
            existed.status = ItemStatus.OFF.value
            try:
                session.commit()
            except Exception as e:  # pylint: disable=broad-except
                logging.error(f'[composer] failed to finish scheduler_item, '
                              f'name: {name}, exception: {e}')
                session.rollback()

    def get_item_status(self, name: str) -> Optional[ItemStatus]:
        """Get item status

        Args:
            name: item name
        """
        with get_session(self.db_engine) as session:
            existed = session.query(SchedulerItem).filter(
                SchedulerItem.name == name).first()
            if not existed:
                return None
            return ItemStatus(existed.status)

    def patch_item_attr(self, name: str, key: str, value: str):
        """ patch item args

        Args:
            name (str): name of this item
            key (str): key you want to update
            value (str): value you wnat to set

        Returns:
            Raise if some check violates
        """
        if key not in self.__class__.MUTABLE_ITEM_KEY:
            raise ValueError(f'fail to change attribute {key}')

        with get_session(self.db_engine) as session:
            item: SchedulerItem = session.query(SchedulerItem).filter(
                SchedulerItem.name == name).first()
            if not item:
                raise ValueError(f'cannot find item {name}')
            setattr(item, key, value)
            session.add(item)
            try:
                session.commit()
            except Exception as e:  # pylint: disable=broad-except
                logging.error(f'[composer] failed to patch item attr, '
                              f'name: {name}, exception: {e}')
                session.rollback()

    def get_recent_runners(self,
                           name: str,
                           count: int = 10) -> List[SchedulerRunner]:
        """Get recent runners order by created_at in desc

        Args:
            name: item name
            count: the number of runners
        """
        with get_session(self.db_engine) as session:
            runners = session.query(SchedulerRunner).join(
                SchedulerItem,
                SchedulerItem.id == SchedulerRunner.item_id).filter(
                    SchedulerItem.name == name).order_by(
                        SchedulerRunner.created_at.desc()).limit(count)
            if not runners:
                return []
            return runners

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
                if item.interval_time < 0:
                    # finish run-once item automatically
                    item.status = ItemStatus.OFF.value
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
                runner_fn = self.runner_cache.find_runner(runner.id, first)
                self.thread_reaper.enqueue(name=lock_name,
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
                runner_fn = self.runner_cache.find_runner(runner.id, current)
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
                        next_runner_fn = self.runner_cache.find_runner(
                            runner.id, next_one)
                        self.thread_reaper.enqueue(name=lock_name,
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

                updated_db = False
                try:
                    logging.info(
                        f'[composer] update runner, status: {runner.status}, '
                        f'pipeline: {runner.pipeline}, '
                        f'output: {output}, context: {runner.context}')
                    if check_lock.is_latest_version():
                        if check_lock.update_version():
                            session.commit()
                            updated_db = True
                    else:
                        logging.error(f'[composer] {lock_name} is outdated, '
                                      f'ignore updates to database')
                except Exception as e:  # pylint: disable=broad-except
                    logging.error(f'[composer] failed to update running '
                                  f'runner status, exception: {e}')
                    session.rollback()

                # delete useless runner obj in runner cache
                if status in (RunnerStatus.DONE,
                              RunnerStatus.FAILED) and updated_db:
                    self.runner_cache.del_runner(runner.id, current)

    @staticmethod
    def _build_pipeline(name: str, items: List[IItem],
                        metadata: dict) -> Pipeline:
        deps = []
        for item in items:
            deps.append(f'{item.type().value}_{item.get_id()}')
        return Pipeline(name=name, deps=deps, meta=metadata)


composer = Composer(config=ComposerConfig(
    runner_fn=global_runner_fn(), name='scheduler for fedlearner webconsole'))
