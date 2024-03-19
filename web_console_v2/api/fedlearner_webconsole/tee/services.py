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

from typing import Optional
from google.protobuf.text_format import MessageToString
from envs import Envs
from sqlalchemy.orm import Session
from fedlearner_webconsole.tee.models import TrustedJobGroup, TrustedJob, TrustedJobStatus, TrustedJobType
from fedlearner_webconsole.tee.tee_job_template import TEE_YAML_TEMPLATE
from fedlearner_webconsole.tee.utils import get_pure_path
from fedlearner_webconsole.utils.pp_datetime import now
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.flag.models import Flag
from fedlearner_webconsole.workflow_template.utils import make_variable
from fedlearner_webconsole.proto.workflow_definition_pb2 import JobDefinition
from fedlearner_webconsole.proto.project_pb2 import ParticipantsInfo, ParticipantInfo
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.participant.services import ParticipantService
from fedlearner_webconsole.job.controller import create_job_without_workflow,  stop_job, \
    schedule_job, start_job_if_ready
from fedlearner_webconsole.algorithm.fetcher import AlgorithmFetcher
from fedlearner_webconsole.dataset.data_path import get_batch_data_path


def check_tee_enabled() -> bool:
    # TODO(liuledian): call k8s api to check whether it has sgx machines instead of using system variables
    return Flag.TEE_MACHINE_DEPLOYED.value


def creat_tee_analyze_job_definition(session: Session, job_name: str, trusted_job: TrustedJob,
                                     group: TrustedJobGroup) -> JobDefinition:
    domain_name = SettingService.get_system_info().domain_name
    analyzer_domain = domain_name
    if group.analyzer_id:
        analyzer_domain = session.query(Participant).get(group.analyzer_id).domain_name
    provider_domain_ls = []
    pds = group.get_participant_datasets()
    if pds:
        for pd in pds.items:
            provider_domain_ls.append(session.query(Participant).get(pd.participant_id).domain_name)
    input_data_path = ''
    if group.dataset_id:
        input_data_path = get_pure_path(get_batch_data_path(group.dataset.get_single_batch()))
        provider_domain_ls.append(domain_name)
    algorithm = AlgorithmFetcher(trusted_job.project_id).get_algorithm(trusted_job.algorithm_uuid)
    variables_dict = {
        'project_name': group.project.name,
        'data_role': 'PROVIDER' if group.analyzer_id else 'ANALYZER',
        'task_type': 'ANALYZE',
        'input_data_path': input_data_path,
        'output_data_path': f'{get_pure_path(Envs.STORAGE_ROOT)}/job_output/{job_name}/output',
        'algorithm': {
            'path': get_pure_path(algorithm.path),
            'config': MessageToString(algorithm.parameter, as_one_line=True),
        },
        'domain_name': domain_name,
        'analyzer_domain': analyzer_domain,
        'providers_domain': ','.join(provider_domain_ls),
        'pccs_url': 'https://sgx-dcap-server.bytedance.com/sgx/certification/v3/',
        'sgx_mem': '' if group.analyzer_id else '100',
        'worker_cpu': f'{trusted_job.get_resource().cpu}m',
        'worker_mem': f'{trusted_job.get_resource().memory}Gi',
        'worker_replicas': 1,
    }
    variables = [make_variable(name=k, typed_value=v) for k, v in variables_dict.items()]
    return JobDefinition(name=job_name,
                         job_type=JobDefinition.CUSTOMIZED,
                         is_federated=False,
                         variables=variables,
                         yaml_template=TEE_YAML_TEMPLATE)


def creat_tee_export_job_definition(session: Session, job_name: str, tee_export_job: TrustedJob,
                                    tee_analyze_job: TrustedJob, group: TrustedJobGroup) -> JobDefinition:
    domain_name = SettingService.get_system_info().domain_name
    analyzer_domain = domain_name
    if group.analyzer_id:
        analyzer_domain = session.query(Participant).get(group.analyzer_id).domain_name
    receiver_domain = domain_name
    if tee_export_job.coordinator_id:
        receiver_domain = session.query(Participant).get(tee_export_job.coordinator_id).domain_name
    variables_dict = {
        'data_role': 'PROVIDER' if group.analyzer_id else 'ANALYZER',
        'task_type': 'EXPORT',
        'output_data_path': f'{get_pure_path(Envs.STORAGE_ROOT)}/job_output/{tee_analyze_job.job.name}/output',
        'export_data_path': f'{get_pure_path(Envs.STORAGE_ROOT)}/job_output/{job_name}/export/batch/0',
        'algorithm': {
            'path': '',
            'config': '',
        },
        'domain_name': domain_name,
        'receiver_domain': receiver_domain,
        'analyzer_domain': analyzer_domain,
        'worker_cpu': f'{tee_export_job.get_resource().cpu}m',
        'worker_mem': f'{tee_export_job.get_resource().memory}Gi',
        'worker_replicas': 1,
    }
    variables = [make_variable(name=k, typed_value=v) for k, v in variables_dict.items()]
    return JobDefinition(name=job_name,
                         job_type=JobDefinition.CUSTOMIZED,
                         is_federated=False,
                         variables=variables,
                         yaml_template=TEE_YAML_TEMPLATE)


class TrustedJobGroupService:

    def __init__(self, session: Session):
        self._session = session

    def delete(self, group: TrustedJobGroup):
        for trusted_job in group.trusted_jobs:
            self._session.delete(trusted_job.job)
        self._session.query(TrustedJob).filter_by(trusted_job_group_id=group.id).delete()
        self._session.delete(group)

    def lock_and_update_version(self, group_id: int, version: Optional[int] = None) -> TrustedJobGroup:
        """
        If param version is None, increment the latest version by 1.
        Otherwise, set the latest version as param version only if param version is larger
        """
        group: TrustedJobGroup = self._session.query(TrustedJobGroup).populate_existing().with_for_update().get(
            group_id)
        if version is None:
            group.latest_version = group.latest_version + 1
        elif version > group.latest_version:
            group.latest_version = version
        return group

    def launch_trusted_job(self, group: TrustedJobGroup, uuid: str, version: int, coordinator_id: int):
        self.lock_and_update_version(group.id, version)
        name = f'V{version}'
        trusted_job = TrustedJob(
            name=name,
            uuid=uuid,
            version=version,
            coordinator_id=coordinator_id,
            project_id=group.project_id,
            trusted_job_group_id=group.id,
            started_at=now(),
            status=TrustedJobStatus.CREATED,
            algorithm_uuid=group.algorithm_uuid,
            resource=group.resource,
        )
        job_name = f'trusted-job-{version}-{uuid}'
        job_definition = creat_tee_analyze_job_definition(self._session, job_name, trusted_job, group)
        job = create_job_without_workflow(self._session, job_definition, group.project_id, job_name)
        schedule_job(self._session, job)
        start_job_if_ready(self._session, job)
        trusted_job.job_id = job.id
        trusted_job.update_status()
        self._session.add(trusted_job)
        self._session.flush()


class TrustedJobService:

    def __init__(self, session: Session):
        self._session = session

    def lock_and_update_export_count(self, trusted_job_id: int) -> TrustedJob:
        trusted_job = self._session.query(TrustedJob).populate_existing().with_for_update().get(trusted_job_id)
        if not trusted_job.export_count:
            trusted_job.export_count = 1
        else:
            trusted_job.export_count += 1
        return trusted_job

    def stop_trusted_job(self, trusted_job: TrustedJob):
        if trusted_job.get_status() != TrustedJobStatus.RUNNING:
            return
        if trusted_job.job is not None:
            stop_job(self._session, trusted_job.job)
        self._session.flush()

    def create_external_export(self, uuid: str, name: str, coordinator_id: int, export_count: int, ticket_uuid: str,
                               tee_analyze_job: TrustedJob):
        """Create trusted export job for non-coordinator, called by rpc server layer"""
        tee_export_job = TrustedJob(
            name=name,
            type=TrustedJobType.EXPORT,
            uuid=uuid,
            version=tee_analyze_job.version,
            export_count=export_count,
            project_id=tee_analyze_job.project_id,
            trusted_job_group_id=tee_analyze_job.trusted_job_group_id,
            coordinator_id=coordinator_id,
            ticket_uuid=ticket_uuid,
            ticket_status=TicketStatus.APPROVED,
            auth_status=AuthStatus.PENDING,
            status=TrustedJobStatus.CREATED,
            resource=tee_analyze_job.resource,
            result_key=tee_analyze_job.result_key,
        )
        participants = ParticipantService(self._session).get_participants_by_project(tee_analyze_job.project_id)
        participants_info = ParticipantsInfo()
        for p in participants:
            participants_info.participants_map[p.pure_domain_name()].CopyFrom(
                ParticipantInfo(auth_status=AuthStatus.PENDING.name))
        self_pure_dn = SettingService.get_system_info().pure_domain_name
        participants_info.participants_map[self_pure_dn].auth_status = AuthStatus.PENDING.name
        coordinator_pure_dn = self._session.query(Participant).get(coordinator_id).pure_domain_name()
        participants_info.participants_map[coordinator_pure_dn].auth_status = AuthStatus.AUTHORIZED.name
        tee_export_job.set_participants_info(participants_info)
        self._session.add(tee_export_job)
        self._session.flush()

    def create_internal_export(self, uuid: str, tee_analyze_job: TrustedJob):
        """Create trusted export job for coordinator, called by api layer"""
        self_pure_dn = SettingService.get_system_info().pure_domain_name
        tee_export_job = TrustedJob(
            name=f'V{tee_analyze_job.version}-{self_pure_dn}-{tee_analyze_job.export_count}',
            type=TrustedJobType.EXPORT,
            uuid=uuid,
            version=tee_analyze_job.version,
            export_count=tee_analyze_job.export_count,
            project_id=tee_analyze_job.project_id,
            trusted_job_group_id=tee_analyze_job.trusted_job_group_id,
            coordinator_id=0,
            auth_status=AuthStatus.AUTHORIZED,
            status=TrustedJobStatus.NEW,
            resource=tee_analyze_job.resource,
            result_key=tee_analyze_job.result_key,
        )
        participants = ParticipantService(self._session).get_participants_by_project(tee_analyze_job.project_id)
        participants_info = ParticipantsInfo()
        for p in participants:
            participants_info.participants_map[p.pure_domain_name()].auth_status = AuthStatus.PENDING.name
        participants_info.participants_map[self_pure_dn].auth_status = AuthStatus.AUTHORIZED.name
        tee_export_job.set_participants_info(participants_info)
        self._session.add(tee_export_job)
        self._session.flush()

    def launch_trusted_export_job(self, tee_export_job: TrustedJob):
        job_name = f'trusted-job-{tee_export_job.version}-{tee_export_job.uuid}'
        tee_analyze_job = self._session.query(TrustedJob).filter_by(
            type=TrustedJobType.ANALYZE,
            trusted_job_group_id=tee_export_job.trusted_job_group_id,
            version=tee_export_job.version).first()
        job_definition = creat_tee_export_job_definition(self._session, job_name, tee_export_job, tee_analyze_job,
                                                         tee_export_job.group)
        job = create_job_without_workflow(self._session, job_definition, tee_export_job.project_id, job_name)
        tee_export_job.started_at = now()
        schedule_job(self._session, job)
        start_job_if_ready(self._session, job)
        tee_export_job.job_id = job.id
        tee_export_job.update_status()
        self._session.flush()
