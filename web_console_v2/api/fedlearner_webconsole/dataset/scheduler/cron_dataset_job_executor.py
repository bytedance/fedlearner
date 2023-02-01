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

from typing import List, Optional
from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session

from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.scheduler.base_executor import BaseExecutor
from fedlearner_webconsole.dataset.scheduler.consts import ExecutorResult
from fedlearner_webconsole.dataset.models import DataBatch, Dataset, DatasetJob, DatasetJobSchedulerState, \
    DatasetKindV2
from fedlearner_webconsole.dataset.local_controllers import DatasetJobStageLocalController
from fedlearner_webconsole.dataset.util import get_oldest_daily_folder_time, parse_event_time_to_daily_folder_name, \
    check_batch_folder_ready, get_oldest_hourly_folder_time, parse_event_time_to_hourly_folder_name, \
    get_hourly_folder_not_ready_err_msg, get_daily_folder_not_ready_err_msg, get_hourly_batch_not_ready_err_msg, \
    get_daily_batch_not_ready_err_msg, get_certain_folder_not_ready_err_msg, get_certain_batch_not_ready_err_msg, \
    get_cron_succeeded_msg
from fedlearner_webconsole.dataset.auth_service import AuthService
from fedlearner_webconsole.utils.pp_datetime import now


class CronDatasetJobExecutor(BaseExecutor):

    def _get_next_event_time(self, session: Session, runnable_dataset_job: DatasetJob) -> Optional[datetime]:
        """get next event_time.

        1. If current event_time is None, next event_time is oldest event_time for input_dataset
        2. If current event_time is not None, next event_time is event_time + time_range
        """
        if runnable_dataset_job.event_time is None:
            input_dataset: Dataset = runnable_dataset_job.input_dataset
            if input_dataset.dataset_kind == DatasetKindV2.SOURCE:
                if runnable_dataset_job.is_hourly_cron():
                    return get_oldest_hourly_folder_time(input_dataset.path)
                return get_oldest_daily_folder_time(input_dataset.path)
            oldest_data_batch = session.query(DataBatch).filter(
                DataBatch.dataset_id == runnable_dataset_job.input_dataset_id).order_by(
                    DataBatch.event_time.asc()).first()
            return oldest_data_batch.event_time if oldest_data_batch else None
        return runnable_dataset_job.event_time + runnable_dataset_job.time_range

    def _should_run(self, session: Session, runnable_dataset_job: DatasetJob, next_event_time: datetime) -> bool:
        """check dependence to decide whether should create next stage.

        1. for input_dataset is data_source, check folder exists and _SUCCESS file exists
        2. for input_dataset is dataset, check data_batch exists and state is SUCCEEDED
        """
        input_dataset: Dataset = runnable_dataset_job.input_dataset
        if input_dataset.dataset_kind == DatasetKindV2.SOURCE:
            if runnable_dataset_job.is_hourly_cron():
                batch_name = parse_event_time_to_hourly_folder_name(next_event_time)
            else:
                batch_name = parse_event_time_to_daily_folder_name(next_event_time)
            return check_batch_folder_ready(folder=input_dataset.path, batch_name=batch_name)
        data_batch: DataBatch = session.query(DataBatch).filter(
            DataBatch.dataset_id == runnable_dataset_job.input_dataset_id).filter(
                DataBatch.event_time == next_event_time).first()
        if data_batch is None:
            return False
        return data_batch.is_available()

    def get_item_ids(self) -> List[int]:
        with db.session_scope() as session:
            runnable_dataset_job_ids = session.query(
                DatasetJob.id).filter(DatasetJob.scheduler_state == DatasetJobSchedulerState.RUNNABLE).all()
        return [runnable_dataset_job_id for runnable_dataset_job_id, *_ in runnable_dataset_job_ids]

    def run_item(self, item_id: int) -> ExecutorResult:
        with db.session_scope() as session:
            # we set isolation_level to SERIALIZABLE to make sure state won't be changed within this session
            session.connection(execution_options={'isolation_level': 'SERIALIZABLE'})
            runnable_dataset_job: DatasetJob = session.query(DatasetJob).get(item_id)
            if runnable_dataset_job.scheduler_state != DatasetJobSchedulerState.RUNNABLE:
                logging.warning('dataset_job scheduler_state is not runnable, ' \
                    f'dataset_job id: {item_id}')
                return ExecutorResult.SKIP
            # check authorization
            if not AuthService(session=session, dataset_job=runnable_dataset_job).check_participants_authorized():
                message = '[cron_dataset_job_executor] still waiting for participants authorized, ' \
                    f'dataset_job_id: {item_id}'
                logging.warning(message)
                return ExecutorResult.SKIP

            next_event_time = self._get_next_event_time(session=session, runnable_dataset_job=runnable_dataset_job)
            if next_event_time is None:
                if runnable_dataset_job.input_dataset.dataset_kind == DatasetKindV2.SOURCE:
                    logging.warning(f'input_dataset has no matched streaming folder, dataset_job id: {item_id}')
                    err_msg = get_hourly_folder_not_ready_err_msg() if runnable_dataset_job.is_hourly_cron() \
                        else get_daily_folder_not_ready_err_msg()
                    runnable_dataset_job.set_scheduler_message(scheduler_message=err_msg)
                else:
                    logging.warning(f'input_dataset has no matched batch, dataset_job id: {item_id}')
                    err_msg = get_hourly_batch_not_ready_err_msg() if runnable_dataset_job.is_hourly_cron() \
                        else get_daily_batch_not_ready_err_msg()
                    runnable_dataset_job.set_scheduler_message(scheduler_message=err_msg)
                session.commit()
                return ExecutorResult.SKIP
            # if next_event_time is 20220801, we wouldn't schedule it until 2022-08-01 00:00:00
            if next_event_time.replace(tzinfo=timezone.utc) > now():
                return ExecutorResult.SKIP
            next_batch_name = parse_event_time_to_hourly_folder_name(event_time=next_event_time) \
                if runnable_dataset_job.is_hourly_cron() \
                else parse_event_time_to_daily_folder_name(event_time=next_event_time)
            if not self._should_run(
                    session=session, runnable_dataset_job=runnable_dataset_job, next_event_time=next_event_time):
                if runnable_dataset_job.input_dataset.dataset_kind == DatasetKindV2.SOURCE:
                    runnable_dataset_job.set_scheduler_message(scheduler_message=get_certain_folder_not_ready_err_msg(
                        folder_name=next_batch_name))
                else:
                    runnable_dataset_job.set_scheduler_message(scheduler_message=get_certain_batch_not_ready_err_msg(
                        batch_name=next_batch_name))
                logging.info(
                    f'[cron_dataset_job_executor] dataset job {item_id} is not should run, ' \
                        f'next_event_time: {next_event_time.strftime("%Y%m%d")}'
                )
                session.commit()
                return ExecutorResult.SKIP
            DatasetJobStageLocalController(session=session).create_data_batch_and_job_stage_as_coordinator(
                dataset_job_id=item_id,
                global_configs=runnable_dataset_job.get_global_configs(),
                event_time=next_event_time)
            runnable_dataset_job.event_time = next_event_time
            runnable_dataset_job.set_scheduler_message(scheduler_message=get_cron_succeeded_msg(
                batch_name=next_batch_name))
            session.commit()
        return ExecutorResult.SUCCEEDED
