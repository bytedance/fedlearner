# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import logging
from concurrent.futures import Future
from typing import Dict

from sqlalchemy import func
from sqlalchemy.engine import Engine

from fedlearner_webconsole.composer.context import PipelineContext
from fedlearner_webconsole.composer.interface import IRunnerV2
from fedlearner_webconsole.composer.models import RunnerStatus, SchedulerRunner
from fedlearner_webconsole.composer.op_locker import OpLocker
from fedlearner_webconsole.composer.thread_reaper import ThreadReaper
from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto import composer_pb2


class PipelineExecutor(object):

    def __init__(self, thread_reaper: ThreadReaper, db_engine: Engine, runner_fns: Dict[str, IRunnerV2]):
        self.thread_reaper = thread_reaper
        self.db_engine = db_engine
        self._runner_fns = runner_fns
        self._running_workers = {}

    def run(self, runner_id: int) -> bool:
        """Starts runner by submitting it to the thread reaper."""
        with db.session_scope() as session:
            runner: SchedulerRunner = session.query(SchedulerRunner).get(runner_id)
            pipeline: composer_pb2.Pipeline = runner.get_pipeline()
            if runner.status not in [RunnerStatus.RUNNING.value]:
                return False
            if self.thread_reaper.is_running(runner_id) or self.thread_reaper.is_full():
                return False
            pipeline_context = PipelineContext.build(pipeline=pipeline, data=runner.get_context())
            current_runner_context = pipeline_context.get_current_runner_context()
            runner_fn = self._runner_fns[current_runner_context.input.runner_type]()
            return self.thread_reaper.submit(
                runner_id=runner_id,
                fn=runner_fn,
                context=current_runner_context,
                done_callback=self._runner_done_callback,
            )

    def _runner_done_callback(self, runner_id: int, fu: Future):
        """Callback when one runner finishes.

        The callback will only update the status, other workers in pipeline will be
        triggered by the executor in the next round check."""
        with db.session_scope() as session:
            runner = session.query(SchedulerRunner).get(runner_id)
            pipeline = runner.get_pipeline()
            if pipeline.version != 2:
                return
            pipeline_context = PipelineContext.build(pipeline=pipeline, data=runner.get_context())
            current_runner_context = pipeline_context.get_current_runner_context()
            output = None
            try:
                status, output = fu.result()
                # Defensively confirming the status
                if status == RunnerStatus.RUNNING:
                    return
                pipeline_context.data.outputs[current_runner_context.index].MergeFrom(output)
                if status == RunnerStatus.DONE:
                    if current_runner_context.index == len(pipeline.queue) - 1:
                        # the whole pipeline is done
                        runner.status = RunnerStatus.DONE.value
                        runner.end_at = func.now()
                    else:
                        # mark to run next
                        pipeline_context.run_next()
                elif status == RunnerStatus.FAILED:
                    runner.status = RunnerStatus.FAILED.value
                    runner.end_at = func.now()
            except Exception as e:  # pylint: disable=broad-except
                logging.exception(f'[PipelineExecutor] failed to run {runner.id}')
                runner.status = RunnerStatus.FAILED.value
                runner.end_at = func.now()
                pipeline_context.data.outputs[current_runner_context.index].error_message = str(e)
            runner.set_context(pipeline_context.data)

            logging.info(f'[pipeline-executor] update runner, status: {runner.status}, '
                         f'pipeline: {runner.pipeline}, '
                         f'output: {output}, context: {runner.context}')
            # Retry 3 times
            for _ in range(3):
                try:
                    lock_name = f'update_running_runner_{runner_id}_lock'
                    lock = OpLocker(lock_name, self.db_engine).try_lock()
                    if lock.is_latest_version():
                        if lock.update_version():
                            session.commit()
                            break
                    else:
                        logging.error(f'[composer] {lock_name} is outdated, ignore updates to database')
                except Exception as e:  # pylint: disable=broad-except
                    logging.error(f'[composer] failed to update running runner status, exception: {e}')
            else:
                # Failed 3 times
                session.rollback()
