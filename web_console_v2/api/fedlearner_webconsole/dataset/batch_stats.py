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
from typing import Tuple
from envs import Envs
import enum
from multiprocessing import get_context, Queue
import queue

from fedlearner_webconsole.composer.context import RunnerContext
from fedlearner_webconsole.db import db
from fedlearner_webconsole.composer.interface import IRunnerV2
from fedlearner_webconsole.composer.models import RunnerStatus
from fedlearner_webconsole.proto.composer_pb2 import RunnerOutput
from fedlearner_webconsole.dataset.models import DataBatch, BatchState
from fedlearner_webconsole.dataset.services import DataReader
from fedlearner_webconsole.dataset.data_path import get_batch_data_path
from fedlearner_webconsole.utils.file_operator import FileOperator
from fedlearner_webconsole.utils.hooks import pre_start_hook

_BATCH_STATS_LOG = 'batch stats'


class BatchStatsItemState(enum.Enum):
    SUCCESSED = 'SUCCESSED'
    FAILED = 'FAILED'


def batch_stats_sub_process(batch_id: int, q: Queue):
    # as we need connect to db in sub process, we should pre-set environment in hook
    # TODO(wangsen.0914): support start process in a unify func
    pre_start_hook()
    with db.session_scope() as session:
        batch: DataBatch = session.query(DataBatch).get(batch_id)
        batch_path = get_batch_data_path(batch)
        batch_name = batch.batch_name
        dataset_path = batch.dataset.path
    meta = DataReader(dataset_path).metadata(batch_name=batch_name)
    batch_num_feature = meta.num_feature
    batch_num_example = meta.num_example
    batch_file_size = FileOperator().getsize(batch_path)
    q.put([batch_num_feature, batch_num_example, batch_file_size])


class BatchStatsRunner(IRunnerV2):

    def _set_batch_stats(self, batch_id: int):
        try:
            context = get_context('spawn')
            internal_queue = context.Queue()
            # The memory will not release after batch stats, so a new process is initialized to do that.
            batch_stats_process = context.Process(target=batch_stats_sub_process,
                                                  kwargs={
                                                      'batch_id': batch_id,
                                                      'q': internal_queue,
                                                  },
                                                  daemon=True)
            batch_stats_process.start()
            try:
                # wait 10 min as some customer hdfs system may cause long time to read
                batch_num_feature, batch_num_example, batch_file_size = internal_queue.get(timeout=600)
            except queue.Empty as e:
                batch_stats_process.terminate()
                raise RuntimeError('run batch_stats_sub_process failed') from e
            finally:
                batch_stats_process.join()
                batch_stats_process.close()
                internal_queue.close()
            with db.session_scope() as session:
                batch = session.query(DataBatch).get(batch_id)
                batch.num_feature = batch_num_feature
                batch.num_example = batch_num_example
                batch.file_size = batch_file_size
                logging.info(f'[{_BATCH_STATS_LOG}]: total batch data size is {batch.file_size}')
                batch.state = BatchState.SUCCESS
                session.commit()
            logging.info(f'[{_BATCH_STATS_LOG}]: finish batch stats task')
        except Exception:  # pylint: disable=broad-except
            with db.session_scope() as session:
                batch = session.query(DataBatch).get(batch_id)
                batch.state = BatchState.FAILED
                session.commit()
                raise

    def run(self, context: RunnerContext) -> Tuple[RunnerStatus, RunnerOutput]:
        logging.info(f'[{_BATCH_STATS_LOG}]: start batch stats task')
        try:
            batch_id = context.input.batch_stats_input.batch_id
            logging.info(f'[{_BATCH_STATS_LOG}]: collect raw dataset stats info, batch id: {batch_id}')
            self._set_batch_stats(batch_id)
            return RunnerStatus.DONE, RunnerOutput()
        except Exception as e:  # pylint: disable=broad-except
            error_message = str(e)
            logging.error(f'[{_BATCH_STATS_LOG}] err: {error_message}, envs: {Envs.__dict__}')
            return RunnerStatus.FAILED, RunnerOutput(error_message=error_message)
