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

import grpc
import logging
from sqlalchemy.orm import Session

from fedlearner_webconsole.proto.two_pc_pb2 import LaunchDatasetJobData, LaunchDatasetJobStageData, \
    StopDatasetJobData, StopDatasetJobStageData, TransactionData, TwoPcType
from fedlearner_webconsole.rpc.v2.job_service_client import JobServiceClient
from fedlearner_webconsole.rpc.v2.resource_service_client import ResourceServiceClient
from fedlearner_webconsole.rpc.v2.system_service_client import SystemServiceClient
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.utils.workflow import fill_variables
from fedlearner_webconsole.dataset.models import Dataset, DatasetJob, DatasetJobStage, DatasetJobState
from fedlearner_webconsole.dataset.job_configer.dataset_job_configer import DatasetJobConfiger
from fedlearner_webconsole.dataset.services import DatasetJobService
from fedlearner_webconsole.dataset.auth_service import AuthService
from fedlearner_webconsole.exceptions import InvalidArgumentException, InternalException
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.workflow.workflow_controller import create_ready_workflow
from fedlearner_webconsole.two_pc.transaction_manager import TransactionManager
from fedlearner_webconsole.flag.models import Flag


class DatasetJobController:

    def __init__(self, session: Session):
        self._session = session

    def _transfer_state(self, uuid: str, target_state: DatasetJobState):
        dataset_job = self._session.query(DatasetJob).filter_by(uuid=uuid).first()

        participants = DatasetJobService(session=self._session).get_participants_need_distribute(dataset_job)
        if target_state == DatasetJobState.RUNNING:
            data = LaunchDatasetJobData(dataset_job_uuid=dataset_job.uuid)
            two_pc_type = TwoPcType.LAUNCH_DATASET_JOB
            transaction_data = TransactionData(launch_dataset_job_data=data)
        elif target_state == DatasetJobState.STOPPED:
            data = StopDatasetJobData(dataset_job_uuid=dataset_job.uuid)
            two_pc_type = TwoPcType.STOP_DATASET_JOB
            transaction_data = TransactionData(stop_dataset_job_data=data)
        else:
            raise InternalException(f'cannot transfer dataset_job state to {target_state.name} by two_pc')

        tm = TransactionManager(project_name=dataset_job.project.name,
                                project_token=dataset_job.project.token,
                                participants=[participant.domain_name for participant in participants],
                                two_pc_type=two_pc_type)
        successed, message = tm.run(data=transaction_data)
        if not successed:
            err_msg = f'error when try to transfer dataset_job state to {target_state.name} by 2PC, ' \
                f'dataset_job_id: {dataset_job.id}, message: {message}'
            logging.error(err_msg)
            raise InternalException(err_msg)

    def start(self, uuid: str):
        self._transfer_state(uuid=uuid, target_state=DatasetJobState.RUNNING)

    def stop(self, uuid: str):
        self._transfer_state(uuid=uuid, target_state=DatasetJobState.STOPPED)

        # stop all related dataset_job_stage
        dataset_job_stage_ids = self._session.query(DatasetJobStage.id).outerjoin(
            DatasetJob, DatasetJobStage.dataset_job_id == DatasetJob.id).filter(DatasetJob.uuid == uuid).all()
        for dataset_job_stage_id, *_ in dataset_job_stage_ids:
            # check each dataset_job_stage, stop by 2pc if is not finished.
            # we don't recheck job_stage state as TransactionManager will check dataset_job_stage state in new session.
            dataset_job_stage = self._session.query(DatasetJobStage).get(dataset_job_stage_id)
            if not dataset_job_stage.is_finished():
                DatasetJobStageController(self._session).stop(uuid=dataset_job_stage.uuid)

    def inform_auth_status(self, dataset_job: DatasetJob, auth_status: AuthStatus):
        participants = DatasetJobService(self._session).get_participants_need_distribute(dataset_job)
        for participant in participants:
            client = ResourceServiceClient.from_project_and_participant(domain_name=participant.domain_name,
                                                                        project_name=dataset_job.project.name)
            try:
                client.inform_dataset(dataset_uuid=dataset_job.output_dataset.uuid, auth_status=auth_status)
            except grpc.RpcError as err:
                logging.warning(
                    f'[dataset_job_controller]: failed to inform particiapnt {participant.name} dataset auth_status, '\
                    f'dataset name: {dataset_job.output_dataset.name}, exception: {err}'
                )

    def update_auth_status_cache(self, dataset_job: DatasetJob):
        participants = DatasetJobService(self._session).get_participants_need_distribute(dataset_job)
        for participant in participants:
            try:
                # check flag
                client = SystemServiceClient.from_participant(domain_name=participant.domain_name)
                resp = client.list_flags()
                # if participant not supports list dataset rpc, just set AUTHORIZED
                if not resp.get(Flag.LIST_DATASETS_RPC_ENABLED.name):
                    AuthService(self._session,
                                dataset_job=dataset_job).update_auth_status(domain_name=participant.pure_domain_name(),
                                                                            auth_status=AuthStatus.AUTHORIZED)
                    continue
                client = ResourceServiceClient.from_project_and_participant(domain_name=participant.domain_name,
                                                                            project_name=dataset_job.project.name)
                resp = client.list_datasets(uuid=dataset_job.output_dataset.uuid)
                if len(resp.participant_datasets) == 0 or not resp.participant_datasets[0].auth_status:
                    logging.warning(
                        '[dataset_job_controller]: update auth_status cache failed as dataset not found, ' \
                        f'or auth_status is None, particiapnt name: {participant.name}, ' \
                        f'dataset name: {dataset_job.output_dataset.name}'
                    )
                    continue
                participant_auth_status = AuthStatus[resp.participant_datasets[0].auth_status]
                AuthService(self._session,
                            dataset_job=dataset_job).update_auth_status(domain_name=participant.pure_domain_name(),
                                                                        auth_status=participant_auth_status)
            except grpc.RpcError as err:
                logging.warning(
                    '[dataset_job_controller]: failed to update dataset auth_status_cache, ' \
                    f'particiapnt name: {participant.name}, ' \
                    f'dataset name: {dataset_job.output_dataset.name}, exception: {err}'
                )


class DatasetJobStageController:

    def __init__(self, session: Session):
        self._session = session

    def create_ready_workflow(self, dataset_job_stage: DatasetJobStage) -> Workflow:
        dataset_job: DatasetJob = dataset_job_stage.dataset_job
        if not dataset_job_stage.is_coordinator():
            coordinator = self._session.query(Participant).get(dataset_job_stage.coordinator_id)
            if coordinator is None:
                raise InvalidArgumentException(f'failed to find participant {dataset_job_stage.coordinator_id}')
            try:
                client = JobServiceClient.from_project_and_participant(coordinator.domain_name,
                                                                       dataset_job_stage.project.name)
                pulled_dataset_job_stage = client.get_dataset_job_stage(dataset_job_stage_uuid=dataset_job_stage.uuid)
            except grpc.RpcError as err:
                logging.error(f'failed to call GetDatasetJobStage with status code {err.code()}, \
                        and details {err.details()}')
                raise
            config = pulled_dataset_job_stage.dataset_job_stage.workflow_definition
            global_configs = pulled_dataset_job_stage.dataset_job_stage.global_configs

        else:
            # TODO(liuhehan): refactor to use rpc get config
            config = DatasetJobConfiger.from_kind(dataset_job.kind, self._session).get_config()
            global_configs = dataset_job_stage.get_global_configs()

        result_dataset = self._session.query(Dataset).get(dataset_job.output_dataset_id)
        global_configs = DatasetJobConfiger.from_kind(dataset_job.kind, self._session).config_local_variables(
            global_configs, result_dataset.uuid, dataset_job_stage.event_time)

        domain_name = SettingService.get_system_info().pure_domain_name
        filled_config = fill_variables(config=config, variables=global_configs.global_configs[domain_name].variables)
        workflow = create_ready_workflow(
            session=self._session,
            name=f'{dataset_job.kind.value}-{dataset_job_stage.uuid}',
            config=filled_config,
            project_id=dataset_job_stage.project_id,
            uuid=dataset_job_stage.uuid,
        )
        self._session.flush()
        dataset_job_stage.workflow_id = workflow.id

        return workflow

    def _transfer_state(self, uuid: str, target_state: DatasetJobState):
        dataset_job_stage: DatasetJobStage = self._session.query(DatasetJobStage).filter_by(uuid=uuid).first()

        assert target_state in [DatasetJobState.RUNNING, DatasetJobState.STOPPED]
        if target_state == DatasetJobState.RUNNING:
            data = LaunchDatasetJobStageData(dataset_job_stage_uuid=uuid)
            two_pc_type = TwoPcType.LAUNCH_DATASET_JOB_STAGE
            transaction_data = TransactionData(launch_dataset_job_stage_data=data)
        else:
            data = StopDatasetJobStageData(dataset_job_stage_uuid=uuid)
            two_pc_type = TwoPcType.STOP_DATASET_JOB_STAGE
            transaction_data = TransactionData(stop_dataset_job_stage_data=data)

        participants = DatasetJobService(session=self._session).get_participants_need_distribute(
            dataset_job_stage.dataset_job)
        tm = TransactionManager(project_name=dataset_job_stage.project.name,
                                project_token=dataset_job_stage.project.token,
                                participants=[participant.domain_name for participant in participants],
                                two_pc_type=two_pc_type)
        succeeded, message = tm.run(data=transaction_data)
        if not succeeded:
            err_msg = f'error when try to transfer dataset_job_stage state to {target_state.name} by 2PC, ' \
                f'dataset_job_stage_id: {dataset_job_stage.id}, message: {message}'
            logging.error(err_msg)
            raise InternalException(err_msg)

    def start(self, uuid: str):
        self._transfer_state(uuid=uuid, target_state=DatasetJobState.RUNNING)

    def stop(self, uuid: str):
        self._transfer_state(uuid=uuid, target_state=DatasetJobState.STOPPED)
