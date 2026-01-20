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
from functools import partial
from typing import Tuple, List

from sqlalchemy.orm import Session

from fedlearner_webconsole.composer.context import RunnerContext
from fedlearner_webconsole.composer.interface import IRunnerV2
from fedlearner_webconsole.composer.models import RunnerStatus
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.controllers import PendingProjectRpcController
from fedlearner_webconsole.project.models import PendingProject, ProjectRole, PendingProjectState
from fedlearner_webconsole.project.services import PendingProjectService
from fedlearner_webconsole.proto.composer_pb2 import RunnerOutput
from fedlearner_webconsole.rpc.v2.project_service_client import ProjectServiceClient
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus


def _get_ids_needed_schedule(session: Session) -> List[int]:
    return [
        p.id for p in session.query(PendingProject.id).filter_by(role=ProjectRole.COORDINATOR,
                                                                 ticket_status=TicketStatus.APPROVED,
                                                                 state=PendingProjectState.ACCEPTED).all()
    ]


def _if_pending_project_needed_create(p: PendingProject) -> bool:
    part_info_list = p.get_participants_info().participants_map.values()
    # coordinator can go next step only after all participants make their choices.
    if any(part_info.state == PendingProjectState.PENDING.name for part_info in part_info_list):
        return False
    return any(part_info.state == PendingProjectState.ACCEPTED.name
               for part_info in part_info_list
               if part_info.role == ProjectRole.PARTICIPANT.name)


def _if_all_participants_closed(p: PendingProject) -> bool:
    closed_part_count = 0
    part_info_list = p.get_participants_info().participants_map.values()
    for part_info in part_info_list:
        if part_info.role == ProjectRole.COORDINATOR.name:
            continue
        if part_info.state == PendingProjectState.CLOSED.name:
            closed_part_count += 1
    return closed_part_count > 0 and closed_part_count == len(part_info_list) - 1


class ScheduleProjectRunner(IRunnerV2):

    @staticmethod
    def _create_pending_project(ids: List[int]):
        for pid in ids:
            with db.session_scope() as session:
                p = session.query(PendingProject).get(pid)
            PendingProjectRpcController(p).send_to_participants(
                partial(ProjectServiceClient.create_pending_project, pending_project=p))
        return ids

    @staticmethod
    def _update_all_participants(ids: List[int]) -> List[int]:
        for pid in ids:
            with db.session_scope() as session:
                p = session.query(PendingProject).get(pid)
                PendingProjectRpcController(p).send_to_participants(
                    partial(ProjectServiceClient.update_pending_project,
                            uuid=p.uuid,
                            participants_map=p.get_participants_info().participants_map))
        return ids

    @staticmethod
    def _create_project(ids: List[int]) -> List[str]:
        p_needed_create = []
        with db.session_scope() as session:
            for pid in ids:
                p = session.query(PendingProject).get(pid)
                if _if_pending_project_needed_create(p):
                    p_needed_create.append(p)
        for p in p_needed_create:
            result = PendingProjectRpcController(p).send_to_participants(
                partial(ProjectServiceClient.create_project, uuid=p.uuid))
            if all(resp.succeeded for resp in result.values()):
                # the project of coordinator must be created at last when all participants finished,
                # to let scheduler be able to retry when some participant failed.
                with db.session_scope() as session:
                    session.connection(execution_options={'isolation_level': 'SERIALIZABLE'})
                    PendingProjectService(session).create_project_locally(p.uuid)
                    session.commit()
            else:
                logging.error(f'create project {p.uuid} failed: {result}')
        return [p.uuid for p in p_needed_create]

    @staticmethod
    def _fail_pending_project(ids: List[int]):
        failed_ids = []
        for p_id in ids:
            with db.session_scope() as session:
                p: PendingProject = session.query(PendingProject).get(p_id)
                if _if_all_participants_closed(p):
                    p.state = PendingProjectState.FAILED
                    failed_ids.append(p.id)
                session.commit()
        return failed_ids

    def run(self, context: RunnerContext) -> Tuple[RunnerStatus, RunnerOutput]:
        with db.session_scope() as session:
            ids = _get_ids_needed_schedule(session)
        output = RunnerOutput()
        output.pending_project_scheduler_output.pending_project_created_ids.extend(self._create_pending_project(ids))
        output.pending_project_scheduler_output.pending_project_updated_ids.extend(self._update_all_participants(ids))
        output.pending_project_scheduler_output.projects_created_uuids.extend(self._create_project(ids))
        output.pending_project_scheduler_output.pending_project_failed_ids.extend(self._fail_pending_project(ids))
        return RunnerStatus.DONE, output
