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

from typing import Tuple, List
import logging
import grpc
from sqlalchemy.orm import Session

from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.two_pc.transaction_manager import TransactionManager
from fedlearner_webconsole.proto.two_pc_pb2 import TwoPcType, TransactionData, CreateTrustedJobGroupData, \
    LaunchTrustedJobData, StopTrustedJobData, LaunchTrustedExportJobData
from fedlearner_webconsole.participant.services import ParticipantService
from fedlearner_webconsole.tee.models import TrustedJobGroup, TrustedJob
from fedlearner_webconsole.tee.services import TrustedJobGroupService, check_tee_enabled
from fedlearner_webconsole.tee.utils import get_participant
from fedlearner_webconsole.proto.tee_pb2 import DomainNameDataset
from fedlearner_webconsole.proto.project_pb2 import ParticipantsInfo
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.rpc.v2.job_service_client import JobServiceClient
from fedlearner_webconsole.exceptions import InternalException
from fedlearner_webconsole.utils.resource_name import resource_uuid
from fedlearner_webconsole.rpc.v2.system_service_client import SystemServiceClient


def _get_transaction_manager(project_id: int, two_pc_type: TwoPcType) -> TransactionManager:
    with db.session_scope() as session:
        project = session.query(Project).get(project_id)
        participants = ParticipantService(session).get_platform_participants_by_project(project_id)
        tm = TransactionManager(project_name=project.name,
                                project_token=project.token,
                                two_pc_type=two_pc_type,
                                participants=[participant.domain_name for participant in participants])
        return tm


def create_trusted_job_group(group: TrustedJobGroup) -> Tuple[bool, str]:
    coordinator_pure_domain_name = SettingService.get_system_info().pure_domain_name
    with db.session_scope() as session:
        project = group.project
        if project is None:
            raise InternalException(f'project {group.project_id} of group {group.id} not found')
        domain_name_datasets = []
        dataset_self = group.dataset
        if dataset_self is not None:
            domain_name_datasets.append(
                DomainNameDataset(pure_domain_name=coordinator_pure_domain_name,
                                  dataset_uuid=dataset_self.uuid,
                                  dataset_name=dataset_self.name))
        participant_datasets = group.get_participant_datasets()
        if participant_datasets is not None:
            for pd in participant_datasets.items:
                participant = get_participant(session, pd.participant_id)
                domain_name_datasets.append(
                    DomainNameDataset(pure_domain_name=participant.pure_domain_name(),
                                      dataset_uuid=pd.uuid,
                                      dataset_name=pd.name))
        analyzer_id = group.analyzer_id
        if analyzer_id:
            analyzer_pure_domain_name = get_participant(session, analyzer_id).pure_domain_name()
        else:
            analyzer_pure_domain_name = coordinator_pure_domain_name
        tm = _get_transaction_manager(project_id=project.id, two_pc_type=TwoPcType.CREATE_TRUSTED_JOB_GROUP)
        create_trusted_job_group_data = CreateTrustedJobGroupData(
            name=group.name,
            uuid=group.uuid,
            ticket_uuid=group.ticket_uuid,
            project_name=project.name,
            creator_username=group.creator_username,
            algorithm_uuid=group.algorithm_uuid,
            domain_name_datasets=domain_name_datasets,
            coordinator_pure_domain_name=coordinator_pure_domain_name,
            analyzer_pure_domain_name=analyzer_pure_domain_name,
        )
    return tm.run(data=TransactionData(create_trusted_job_group_data=create_trusted_job_group_data))


def launch_trusted_job(project_id: int, group_uuid: str, version: int):
    initiator_pure_domain_name = SettingService.get_system_info().pure_domain_name
    tm = _get_transaction_manager(project_id=project_id, two_pc_type=TwoPcType.LAUNCH_TRUSTED_JOB)
    data = TransactionData(
        launch_trusted_job_data=LaunchTrustedJobData(uuid=resource_uuid(),
                                                     group_uuid=group_uuid,
                                                     version=version,
                                                     initiator_pure_domain_name=initiator_pure_domain_name))
    return tm.run(data)


def stop_trusted_job(project_id: int, uuid: str):
    tm = _get_transaction_manager(project_id=project_id, two_pc_type=TwoPcType.STOP_TRUSTED_JOB)
    data = TransactionData(stop_trusted_job_data=StopTrustedJobData(uuid=uuid))
    return tm.run(data)


def launch_trusted_export_job(project_id: int, uuid: str):
    tm = _get_transaction_manager(project_id=project_id, two_pc_type=TwoPcType.LAUNCH_TRUSTED_EXPORT_JOB)
    data = TransactionData(launch_trusted_export_job_data=LaunchTrustedExportJobData(uuid=uuid))
    return tm.run(data)


def get_tee_enabled_participants(session: Session, project_id: int) -> List[int]:
    enabled_pids = []
    if check_tee_enabled():
        enabled_pids.append(0)
    participants = ParticipantService(session).get_platform_participants_by_project(project_id)
    for p in participants:
        client = SystemServiceClient.from_participant(p.domain_name)
        try:
            resp = client.check_tee_enabled()
            if resp.tee_enabled:
                enabled_pids.append(p.id)
        except grpc.RpcError as e:
            raise InternalException(f'failed to get participant {p.id}\'s tee enabled status '
                                    f'with grpc code {e.code()} and details {e.details()}') from e
    return enabled_pids


class TrustedJobGroupController:

    def __init__(self, session: Session, project_id: int):
        self._session = session
        self._clients = []
        self._participant_ids = []
        project = session.query(Project).get(project_id)
        participants = ParticipantService(session).get_platform_participants_by_project(project_id)
        for p in participants:
            self._clients.append(JobServiceClient.from_project_and_participant(p.domain_name, project.name))
            self._participant_ids.append(p.id)

    def inform_trusted_job_group(self, group: TrustedJobGroup, auth_status: AuthStatus):
        group.auth_status = auth_status
        for client, pid in zip(self._clients, self._participant_ids):
            try:
                client.inform_trusted_job_group(group.uuid, auth_status)
            except grpc.RpcError as e:
                logging.warning(f'[trusted-job-group] failed to inform participant {pid}\'s '
                                f'trusted job group {group.uuid} with grpc code {e.code()} and details {e.details()}')

    def update_trusted_job_group(self, group: TrustedJobGroup, algorithm_uuid: str):
        for client, pid in zip(self._clients, self._participant_ids):
            try:
                client.update_trusted_job_group(group.uuid, algorithm_uuid)
            except grpc.RpcError as e:
                raise InternalException(f'failed to update participant {pid}\'s trusted job group {group.uuid} '
                                        f'with grpc code {e.code()} and details {e.details()}') from e
        group.algorithm_uuid = algorithm_uuid

    def delete_trusted_job_group(self, group: TrustedJobGroup):

        for client, pid in zip(self._clients, self._participant_ids):
            try:
                client.delete_trusted_job_group(group.uuid)
            except grpc.RpcError as e:
                raise InternalException(f'failed to delete participant {pid}\'s trusted job group {group.uuid} '
                                        f'with grpc code {e.code()} and details {e.details()}') from e
        TrustedJobGroupService(self._session).delete(group)

    def update_unauth_participant_ids(self, group: TrustedJobGroup):
        unauth_set = set(group.get_unauth_participant_ids())
        for client, pid in zip(self._clients, self._participant_ids):
            try:
                resp = client.get_trusted_job_group(group.uuid)
                status = AuthStatus[resp.auth_status]
                if status == AuthStatus.AUTHORIZED:
                    unauth_set.discard(pid)
                else:
                    unauth_set.add(pid)
            except grpc.RpcError as e:
                logging.warning(f'[trusted-job-group] failed to get participant {pid}\'s '
                                f'trusted job group {group.uuid} with grpc code {e.code()} and details {e.details()}')
        group.set_unauth_participant_ids(list(unauth_set))


class TrustedJobController:

    def __init__(self, session: Session, project_id: int):
        self._session = session
        self._clients = []
        self._participants = ParticipantService(session).get_platform_participants_by_project(project_id)
        project = session.query(Project).get(project_id)
        for p in self._participants:
            self._clients.append(JobServiceClient.from_project_and_participant(p.domain_name, project.name))

    def inform_auth_status(self, trusted_job: TrustedJob, auth_status: AuthStatus):
        trusted_job.auth_status = auth_status
        participants_info: ParticipantsInfo = trusted_job.get_participants_info()
        self_pure_dn = SettingService.get_system_info().pure_domain_name
        participants_info.participants_map[self_pure_dn].auth_status = auth_status.name
        trusted_job.set_participants_info(participants_info)
        for client, p in zip(self._clients, self._participants):
            try:
                client.inform_trusted_job(trusted_job.uuid, auth_status)
            except grpc.RpcError as e:
                logging.warning(f'[trusted-job] failed to inform participant {p.id}\'s '
                                f'trusted job {trusted_job.uuid} with grpc code {e.code()} and details {e.details()}')

    def update_participants_info(self, trusted_job: TrustedJob):
        participants_info = trusted_job.get_participants_info()
        for client, p in zip(self._clients, self._participants):
            try:
                resp = client.get_trusted_job(trusted_job.uuid)
                auth_status = AuthStatus[resp.auth_status]
                participants_info.participants_map[p.pure_domain_name()].auth_status = auth_status.name
            except grpc.RpcError as e:
                logging.warning(f'[trusted-job] failed to get participant {p.id}\'s '
                                f'trusted job {trusted_job.uuid} with grpc code {e.code()} and details {e.details()}')
        trusted_job.set_participants_info(participants_info)

    def create_trusted_export_job(self, tee_export_job: TrustedJob, tee_analyze_job: TrustedJob):
        # local trusted export job is already created by apis and this func is only used by runner
        for client, p in zip(self._clients, self._participants):
            try:
                client.create_trusted_export_job(tee_export_job.uuid, tee_export_job.name, tee_export_job.export_count,
                                                 tee_analyze_job.uuid, tee_export_job.ticket_uuid)
            except grpc.RpcError as e:
                raise InternalException(
                    f'failed to create participant {p.id}\'s trusted export job {tee_export_job.uuid} '
                    f'with grpc code {e.code()} and details {e.details()}') from e
