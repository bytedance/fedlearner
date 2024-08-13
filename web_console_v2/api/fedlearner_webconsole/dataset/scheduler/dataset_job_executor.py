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

from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.scheduler.base_executor import BaseExecutor
from fedlearner_webconsole.dataset.scheduler.consts import ExecutorResult
from fedlearner_webconsole.dataset.models import DatasetJob, DatasetJobSchedulerState
from fedlearner_webconsole.dataset.services import DatasetJobService
from fedlearner_webconsole.dataset.job_configer.dataset_job_configer import DatasetJobConfiger
from fedlearner_webconsole.dataset.local_controllers import DatasetJobStageLocalController
from fedlearner_webconsole.dataset.auth_service import AuthService
from fedlearner_webconsole.proto import dataset_pb2
from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.rpc.v2.system_service_client import SystemServiceClient
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.flag.models import Flag


class DatasetJobExecutor(BaseExecutor):

    def get_item_ids(self) -> List[int]:
        with db.session_scope() as session:
            pending_dataset_job_ids = session.query(
                DatasetJob.id).filter(DatasetJob.scheduler_state == DatasetJobSchedulerState.PENDING).all()
        return [pending_dataset_job_id for pending_dataset_job_id, *_ in pending_dataset_job_ids]

    def run_item(self, item_id: int) -> ExecutorResult:
        with db.session_scope() as session:
            dataset_job: DatasetJob = session.query(DatasetJob).get(item_id)
            # TODO(liuhehan): remove this func after remove DATASET_JOB_STAGE_ENABLED flag
            if not dataset_job.get_context().has_stages:
                dataset_job.scheduler_state = DatasetJobSchedulerState.STOPPED
                session.commit()
                return ExecutorResult.SKIP
            if dataset_job.scheduler_state != DatasetJobSchedulerState.PENDING:
                return ExecutorResult.SKIP
            if dataset_job.output_dataset.ticket_status != TicketStatus.APPROVED:
                return ExecutorResult.SKIP
            if dataset_job.is_coordinator():
                # create participant dataset_job
                participants = DatasetJobService(session).get_participants_need_distribute(dataset_job)
                for participant in participants:
                    client = RpcClient.from_project_and_participant(dataset_job.project.name, dataset_job.project.token,
                                                                    participant.domain_name)
                    dataset_job_parameter = dataset_job.to_proto()
                    dataset_job_parameter.workflow_definition.MergeFrom(
                        DatasetJobConfiger.from_kind(dataset_job.kind, session).get_config())
                    dataset_parameter = dataset_pb2.Dataset(
                        participants_info=dataset_job.output_dataset.get_participants_info())
                    client.create_dataset_job(dataset_job=dataset_job_parameter,
                                              ticket_uuid=dataset_job.output_dataset.ticket_uuid,
                                              dataset=dataset_parameter)
                    # check flags, if participants donot check authstatus, just set authorized
                    system_client = SystemServiceClient.from_participant(domain_name=participant.domain_name)
                    flag_resp = system_client.list_flags()
                    if not flag_resp.get(Flag.DATASET_AUTH_STATUS_CHECK_ENABLED.name):
                        AuthService(session=session, dataset_job=dataset_job).update_auth_status(
                            domain_name=participant.pure_domain_name(), auth_status=AuthStatus.AUTHORIZED)
            else:
                # participant scheduler state always set to stopped,
                # and never created data_batch and dataset_job_stage itself
                dataset_job.scheduler_state = DatasetJobSchedulerState.STOPPED
            session.commit()
        with db.session_scope() as session:
            # we set isolation_level to SERIALIZABLE to make sure state won't be changed within this session
            session.connection(execution_options={'isolation_level': 'SERIALIZABLE'})
            dataset_job: DatasetJob = session.query(DatasetJob).get(item_id)
            if dataset_job.scheduler_state != DatasetJobSchedulerState.PENDING:
                return ExecutorResult.SKIP
            if dataset_job.is_cron():
                # if dataset_job is cron, we set scheduler state to runnable,
                # and it will be scheduler again by cron_dataset_job_executor
                dataset_job.scheduler_state = DatasetJobSchedulerState.RUNNABLE
            else:
                if dataset_job.get_context().need_create_stage:
                    # check authorization
                    if not AuthService(session=session, dataset_job=dataset_job).check_participants_authorized():
                        message = '[dataset_job_executor] still waiting for participants authorized, ' \
                            f'dataset_job_id: {item_id}'
                        logging.warning(message)
                        return ExecutorResult.SKIP
                    DatasetJobStageLocalController(session).create_data_batch_and_job_stage_as_coordinator(
                        dataset_job_id=dataset_job.id, global_configs=dataset_job.get_global_configs())
                dataset_job.scheduler_state = DatasetJobSchedulerState.STOPPED
            session.commit()
        return ExecutorResult.SUCCEEDED
