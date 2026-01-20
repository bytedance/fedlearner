# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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
from typing import List, Dict, Optional

from google.protobuf.struct_pb2 import Value
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from envs import Envs
from fedlearner_webconsole.exceptions import ResourceConflictException
from fedlearner_webconsole.participant.models import ProjectParticipant, Participant, ParticipantType
from fedlearner_webconsole.participant.services import ParticipantService
from fedlearner_webconsole.project.models import Project, PendingProject, PendingProjectState, ProjectRole
from fedlearner_webconsole.proto.filtering_pb2 import FilterExpression, FilterOp
from fedlearner_webconsole.proto.common_pb2 import Variable
from fedlearner_webconsole.proto.project_pb2 import ProjectRef, ProjectConfig, ParticipantsInfo, ParticipantInfo
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.utils.filtering import FilterBuilder, SupportedField, FieldType
from fedlearner_webconsole.utils.paginate import Pagination, paginate
from fedlearner_webconsole.utils.resource_name import resource_uuid
from fedlearner_webconsole.workflow.models import Workflow


class ProjectService(object):

    def __init__(self, session: Session):
        self._session = session

    def get_projects_by_participant(self, participant_id: int) -> List[Dict]:
        projects = self._session.query(Project).join(
            ProjectParticipant, ProjectParticipant.project_id == Project.id).filter(
            ProjectParticipant.participant_id == participant_id). \
            order_by(Project.created_at.desc()).all()
        return projects

    def get_projects(self) -> List[ProjectRef]:
        """Gets all projects in the platform."""
        # TODO(linfan.fine): Not count soft-deleted workflow
        # Project left join workflow to get workflow counts
        projects = self._session.query(
            Project, func.count(Workflow.id).label('num_workflow')) \
            .options(joinedload(Project.participants)) \
            .outerjoin(Workflow, Workflow.project_id == Project.id) \
            .group_by(Project.id) \
            .order_by(Project.created_at.desc()) \
            .all()
        refs = []
        for row in projects:
            ref: ProjectRef = row.Project.to_ref()
            ref.num_workflow = row.num_workflow
            refs.append(ref)
        return refs


class PendingProjectService(object):
    FILTER_FIELDS = {
        'name': SupportedField(type=FieldType.STRING, ops={FilterOp.CONTAIN: None}),
        'role': SupportedField(type=FieldType.STRING, ops={FilterOp.EQUAL: None}),
        'state': SupportedField(type=FieldType.STRING, ops={
            FilterOp.EQUAL: None,
            FilterOp.IN: None
        }),
    }

    def __init__(self, session: Session):
        self._session = session
        self._filter_builder = FilterBuilder(model_class=PendingProject, supported_fields=self.FILTER_FIELDS)

    def build_participants_info(self, participant_ids: List[int]) -> ParticipantInfo:
        participants_info = ParticipantsInfo()
        for p_id in participant_ids:
            participant = self._session.query(Participant).get(p_id)
            assert participant is not None, f'participant with id {p_id} is not found'
            p_info = ParticipantInfo(name=participant.name,
                                     role=ProjectRole.PARTICIPANT.name,
                                     state=PendingProjectState.PENDING.name if participant.get_type()
                                     == ParticipantType.PLATFORM else PendingProjectState.ACCEPTED.name,
                                     type=participant.get_type().name)
            participants_info.participants_map[participant.pure_domain_name()].CopyFrom(p_info)

        sys_info = SettingService(self._session).get_system_info()
        coordinator_info = ParticipantInfo(name=sys_info.name,
                                           state=PendingProjectState.ACCEPTED.name,
                                           role=ProjectRole.COORDINATOR.name,
                                           type=ParticipantType.PLATFORM.name)
        participants_info.participants_map[sys_info.pure_domain_name].CopyFrom(coordinator_info)
        return participants_info

    def get_ids_from_participants_info(self, participants_info: ParticipantInfo) -> List[int]:
        participant_ids = []
        for pure_domain, p_info in participants_info.participants_map.items():
            if p_info.role == ProjectRole.COORDINATOR:
                continue
            participant = ParticipantService(self._session).get_participant_by_pure_domain_name(pure_domain)
            if participant is not None:
                participant_ids.append(participant.id)
        return participant_ids

    def create_pending_project(self,
                               name: str,
                               config: ProjectConfig,
                               participants_info: ParticipantInfo,
                               comment: str,
                               creator_username: str,
                               uuid: Optional[str] = None,
                               role: ProjectRole = ProjectRole.PARTICIPANT,
                               state: PendingProjectState = PendingProjectState.PENDING) -> PendingProject:
        pending_project = PendingProject(
            name=name,
            uuid=uuid if uuid else resource_uuid(),
            comment=comment,
            role=role,
            state=state,
            creator_username=creator_username,
        )
        pending_project.set_config(config)
        pending_project.set_participants_info(participants_info)
        self._session.add(pending_project)
        self._session.flush()
        return pending_project

    def update_state_as_participant(self, pending_project_id: int, state: str) -> PendingProject:
        pending_project: PendingProject = self._session.query(PendingProject).get(pending_project_id)
        assert pending_project is not None, f'pending project with id {pending_project_id} is not found'
        assert pending_project.role == ProjectRole.PARTICIPANT, 'only participant can accept or refuse'

        # TODO(xiangyuxuan.prs): remove after using token instead of name to ensure consistency of project
        if PendingProjectState(state) == PendingProjectState.ACCEPTED and self.duplicated_name_exists(
                pending_project.name):
            raise ResourceConflictException(f'{pending_project.name} has already existed')

        pending_project.state = PendingProjectState(state)
        return pending_project

    def list_pending_projects(self,
                              page: Optional[int] = None,
                              page_size: Optional[int] = None,
                              filter_exp: Optional[FilterExpression] = None) -> Pagination:
        """Lists pending project by filter expression and pagination.

        Raises:
            ValueError: if the expression is unsupported.
        """
        query = self._session.query(PendingProject)
        if filter_exp:
            query = self._filter_builder.build_query(query, filter_exp)
        query = query.order_by(PendingProject.id.desc())
        return paginate(query, page, page_size)

    def create_project_locally(self, pending_project_uuid: str):
        pending_project: PendingProject = self._session.query(PendingProject).filter_by(
            uuid=pending_project_uuid).first()
        project = Project(name=pending_project.name,
                          token=pending_project.uuid,
                          role=pending_project.role,
                          creator=pending_project.creator_username,
                          comment=pending_project.comment)
        project.set_participants_info(pending_project.get_participants_info())
        project_config: ProjectConfig = pending_project.get_config()
        # init storage root path variable to make user use config in environment by default.
        project_config.variables.append(
            Variable(name='storage_root_path',
                     typed_value=Value(string_value=Envs.STORAGE_ROOT),
                     value=Envs.STORAGE_ROOT))
        project.set_config(project_config)
        self._session.add(project)
        self._session.flush()
        part_ids = self.get_ids_from_participants_info(pending_project.get_participants_info())
        for participant_id in part_ids:
            # insert a relationship into the table
            new_relationship = ProjectParticipant(project_id=project.id, participant_id=participant_id)
            self._session.add(new_relationship)
        self._session.flush()
        pending_project.state = PendingProjectState.CLOSED

    def duplicated_name_exists(self, name: str) -> bool:
        p = self._session.query(Project.id).filter_by(name=name).first()
        if p is not None:
            return True
        pending_p = self._session.query(PendingProject.id).filter_by(name=name,
                                                                     state=PendingProjectState.ACCEPTED).first()
        if pending_p is not None:
            return True
        return False
