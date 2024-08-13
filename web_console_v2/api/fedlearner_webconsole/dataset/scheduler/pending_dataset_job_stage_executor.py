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
from typing import List
import grpc
from sqlalchemy.orm import Session

from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.controllers import DatasetJobStageController
from fedlearner_webconsole.dataset.services import DatasetJobService
from fedlearner_webconsole.dataset.scheduler.base_executor import BaseExecutor
from fedlearner_webconsole.dataset.scheduler.consts import ExecutorResult
from fedlearner_webconsole.dataset.models import DatasetJob, DatasetJobSchedulerState, DatasetJobStage, DatasetJobState
from fedlearner_webconsole.exceptions import InternalException
from fedlearner_webconsole.rpc.v2.job_service_client import JobServiceClient


class PendingDatasetJobStageExecutor(BaseExecutor):

    def _process_pending_dataset_job_stage(self, session: Session,
                                           dataset_job_stage: DatasetJobStage) -> ExecutorResult:
        """Schedules pending dataset job stage, same logic as _process_pending_dataset_job.

        1. If is not coordinator, return
        2. check whether participant is ready, if not, try to create it and return
        3. try to start the dataset_job_stage
        """
        if not dataset_job_stage.is_coordinator():
            return ExecutorResult.SUCCEEDED
        # create participant dataset_job_stage
        dataset_job: DatasetJob = dataset_job_stage.dataset_job
        participants = DatasetJobService(session).get_participants_need_distribute(dataset_job)
        # if all participants which need distribute have created dataset_job_stage and related workflow,
        # is_peer_ready is True
        is_peer_ready = True
        for participant in participants:
            client = JobServiceClient.from_project_and_participant(domain_name=participant.domain_name,
                                                                   project_name=dataset_job_stage.project.name)
            try:
                response = client.get_dataset_job_stage(dataset_job_stage_uuid=dataset_job_stage.uuid)
                if response.dataset_job_stage.is_ready:
                    logging.info(
                        '[pending dataset_job_stage executor]: participant dataset_job_stage is ready, ' \
                            f'participant name: {participant.name}'
                    )
                else:
                    is_peer_ready = False
            except grpc.RpcError as err:
                if err.code() != grpc.StatusCode.NOT_FOUND:
                    raise InternalException(
                        details=f'failed to call GetDatasetJobStage with status code {err.code()} ' \
                            f'and details {err.details()}'
                    ) from err
                # participant has no dataset_job_stage
                logging.info(
                    f'[pending dataset_job_stage executor]: dataset_job_stage in participant {participant.name} ' \
                        'not found, start to create')
                is_peer_ready = False
                client.create_dataset_job_stage(dataset_job_uuid=dataset_job.uuid,
                                                dataset_job_stage_uuid=dataset_job_stage.uuid,
                                                name=dataset_job_stage.name,
                                                event_time=dataset_job_stage.event_time)
        if not is_peer_ready:
            return ExecutorResult.SKIP
        # start dataset_job
        try:
            DatasetJobStageController(session=session).start(uuid=dataset_job_stage.uuid)
            logging.info(
                '[pending dataset_job_stage executor]: start dataset_job_stage successfully, ' \
                    f'dataset_job_stage_id: {dataset_job_stage.id}'
            )
        except InternalException as e:
            logging.error(
                f'[pending dataset_job_stage executor]: start dataset_job_stage {dataset_job_stage.id} failed, ' \
                    f'exception: {e}'
            )
            # reset dataset_job_stage state to PENDING,
            # in order to make sure it will be scheduled to start again next time
            dataset_job_stage.state = DatasetJobState.PENDING
            return ExecutorResult.FAILED
        return ExecutorResult.SUCCEEDED

    def get_item_ids(self) -> List[int]:
        with db.session_scope() as session:
            pending_dataset_job_stage_ids = session.query(DatasetJobStage.id).outerjoin(
                DatasetJob, DatasetJob.id == DatasetJobStage.dataset_job_id).filter(
                    DatasetJobStage.state == DatasetJobState.PENDING).filter(
                        DatasetJob.scheduler_state != DatasetJobSchedulerState.PENDING).all()
        return [pending_dataset_job_stage_id for pending_dataset_job_stage_id, *_ in pending_dataset_job_stage_ids]

    def run_item(self, item_id: int) -> ExecutorResult:
        with db.session_scope() as session:
            # we set isolation_level to SERIALIZABLE to make sure state won't be changed within this session
            session.connection(execution_options={'isolation_level': 'SERIALIZABLE'})
            dataset_job_stage: DatasetJobStage = session.query(DatasetJobStage).get(item_id)
            if dataset_job_stage.state != DatasetJobState.PENDING:
                return ExecutorResult.SKIP
            if not dataset_job_stage.workflow:
                DatasetJobStageController(session=session).create_ready_workflow(dataset_job_stage)
            session.commit()
        with db.session_scope() as session:
            dataset_job_stage: DatasetJobStage = session.query(DatasetJobStage).get(item_id)
            executor_result = self._process_pending_dataset_job_stage(session, dataset_job_stage)
            session.commit()
        return executor_result
