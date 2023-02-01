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
from typing import List, Tuple, Union, Optional

from sqlalchemy import or_, and_
from sqlalchemy.orm import Session, Query

from fedlearner_webconsole.composer.interface import ItemType
from fedlearner_webconsole.job.service import JobService
from fedlearner_webconsole.proto.composer_pb2 import RunnerInput, WorkflowCronJobInput
from fedlearner_webconsole.proto.filtering_pb2 import FilterExpression, FilterOp, SimpleExpression
from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.utils.const import SYSTEM_WORKFLOW_CREATOR_USERNAME
from fedlearner_webconsole.utils.filtering import SupportedField, FilterBuilder, FieldType
from fedlearner_webconsole.utils.metrics import emit_store
from fedlearner_webconsole.composer.composer_service import CronJobService
from fedlearner_webconsole.exceptions import InvalidArgumentException, ResourceConflictException
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition
from fedlearner_webconsole.job.yaml_formatter import YamlFormatterService
from fedlearner_webconsole.utils.workflow import build_job_name
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState, TransactionState
from fedlearner_webconsole.workflow_template.models import WorkflowTemplate
from fedlearner_webconsole.workflow.utils import is_local, is_peer_job_inheritance_matched
from fedlearner_webconsole.job.models import Job, JobType, JobState, JobDependency
from fedlearner_webconsole.proto import common_pb2
from fedlearner_webconsole.participant.services import ParticipantService
from fedlearner_webconsole.utils.resource_name import resource_uuid


def update_cronjob_config(workflow_id: int, cron_config: str, session: Session):
    """Starts a cronjob for workflow if cron_config is valid.

    Args:
        workflow_id (int): id of the workflow
        cron_config (str): cron expression;
            if cron_config is None or '', cancel previous cron setting
        session: db session
    Raises:
        Raise if some check violates
        InvalidArgumentException: if some check violates
    """
    item_name = f'workflow_cron_job_{workflow_id}'
    if cron_config:
        rinput = RunnerInput(workflow_cron_job_input=WorkflowCronJobInput(workflow_id=workflow_id))
        items = [(ItemType.WORKFLOW_CRON_JOB, rinput)]
        CronJobService(session).start_cronjob(item_name=item_name, items=items, cron_config=cron_config)
    else:
        CronJobService(session).stop_cronjob(item_name=item_name)


class ForkWorkflowParams(object):

    def __init__(self, fork_from_id: int, fork_proposal_config: WorkflowDefinition, peer_create_job_flags: List[int]):
        self.fork_from_id = fork_from_id
        self.fork_proposal_config = fork_proposal_config
        self.peer_create_job_flags = peer_create_job_flags


class CreateNewWorkflowParams(object):

    def __init__(self, project_id: int, template_id: Optional[int], template_revision_id: Optional[int] = None):
        self.project_id = project_id
        self.template_id = template_id
        self.template_revision_id = template_revision_id


def _filter_system_workflow(exp: SimpleExpression):
    if exp.bool_value:
        return Workflow.creator == SYSTEM_WORKFLOW_CREATOR_USERNAME
    # != Null or == Null will always return Null in mysql.
    return or_(Workflow.creator != SYSTEM_WORKFLOW_CREATOR_USERNAME, Workflow.creator.is_(None))


class WorkflowService:
    FILTER_FIELDS = {'system': SupportedField(type=FieldType.BOOL, ops={FilterOp.EQUAL: _filter_system_workflow})}

    def __init__(self, session):
        self._session = session
        self._filter_builder = FilterBuilder(model_class=Workflow, supported_fields=self.FILTER_FIELDS)

    def build_filter_query(self, query: Query, exp: FilterExpression) -> Query:
        return self._filter_builder.build_query(query, exp)

    def validate_workflow(self, workflow: Workflow) -> Tuple[bool, tuple]:
        for job in workflow.owned_jobs:
            try:
                YamlFormatterService(self._session).generate_job_run_yaml(job)
            except Exception as e:  # pylint: disable=broad-except
                return False, (job.name, e)
        return True, ()

    @staticmethod
    def filter_workflows(query: Query, states: List[str]) -> Query:
        query_states = []
        filters = []
        for state in states:
            query_states.append(state.upper())
            # TODO(xiangyuxuan.prs): simplify Workflow create to remove the specific process for states below.
            #  The logic of process is same as get_state_for_frontend.
            if state == 'warmup':
                filters.append(
                    and_(
                        Workflow.state == WorkflowState.NEW, Workflow.target_state == WorkflowState.READY,
                        Workflow.transaction_state.in_([
                            TransactionState.PARTICIPANT_COMMITTABLE, TransactionState.PARTICIPANT_COMMITTING,
                            TransactionState.COORDINATOR_COMMITTING
                        ])))
            if state == 'pending':
                filters.append(
                    and_(Workflow.state == WorkflowState.NEW, Workflow.target_state == WorkflowState.READY,
                         Workflow.transaction_state == TransactionState.PARTICIPANT_PREPARE))
            if state == 'configuring':
                filters.append(
                    and_(
                        Workflow.state == WorkflowState.NEW, Workflow.target_state == WorkflowState.READY,
                        Workflow.transaction_state.in_([
                            TransactionState.READY, TransactionState.COORDINATOR_COMMITTABLE,
                            TransactionState.COORDINATOR_PREPARE
                        ])))
        filters.append(Workflow.state.in_(query_states))
        query = query.filter(or_(*filters))
        return query

    def _check_conflict(self, workflow_name: str, project_id: int):
        if self._session.query(Workflow).filter_by(name=workflow_name).filter_by(
                project_id=project_id).first() is not None:
            raise ResourceConflictException(f'Workflow {workflow_name} already exists in project: {project_id}.')

    def create_workflow(self,
                        name: str,
                        config: WorkflowDefinition,
                        params: Union[CreateNewWorkflowParams, ForkWorkflowParams],
                        forkable: bool = False,
                        comment: Optional[str] = None,
                        create_job_flags: Optional[List[int]] = None,
                        cron_config: Optional[str] = None,
                        creator_username: str = None,
                        uuid: Optional[str] = None,
                        state: WorkflowState = WorkflowState.NEW,
                        target_state: WorkflowState = WorkflowState.READY):
        # Parameter validations
        parent_workflow = None
        template = None
        project_id = None
        if isinstance(params, ForkWorkflowParams):
            # Fork mode
            parent_workflow = self._session.query(Workflow).get(params.fork_from_id)
            if parent_workflow is None:
                raise InvalidArgumentException('fork_from_id is not valid')
            if not parent_workflow.forkable:
                raise InvalidArgumentException('workflow not forkable')
            project_id = parent_workflow.project_id
            self._check_conflict(name, project_id)
            # it is possible that parent_workflow.template is None
            template = parent_workflow.template
            if not is_local(config, create_job_flags):
                participants = ParticipantService(self._session).get_platform_participants_by_project(
                    parent_workflow.project.id)
                if not is_peer_job_inheritance_matched(project=parent_workflow.project,
                                                       workflow_definition=config,
                                                       job_flags=create_job_flags,
                                                       peer_job_flags=params.peer_create_job_flags,
                                                       parent_uuid=parent_workflow.uuid,
                                                       parent_name=parent_workflow.name,
                                                       participants=participants):
                    raise ValueError('Forked workflow has federated job with ' 'unmatched inheritance')
        else:
            # Create new mode
            project_id = params.project_id
            self._check_conflict(name, project_id)
            if params.template_id:
                template = self._session.query(WorkflowTemplate).get(params.template_id)
                assert template is not None
        assert project_id is not None
        if uuid is None:
            uuid = resource_uuid()
        workflow = Workflow(name=name,
                            uuid=uuid,
                            comment=comment,
                            project_id=project_id,
                            forkable=forkable,
                            forked_from=None if parent_workflow is None else parent_workflow.id,
                            state=state,
                            target_state=target_state,
                            transaction_state=TransactionState.READY,
                            creator=creator_username,
                            template_revision_id=parent_workflow.template_revision_id
                            if parent_workflow else params.template_revision_id)
        if template:
            workflow.template_id = template.id
            workflow.editor_info = template.editor_info
        self.update_config(workflow, config)
        workflow.set_create_job_flags(create_job_flags)
        if isinstance(params, ForkWorkflowParams):
            # Fork mode
            # TODO(hangweiqiang): more validations
            workflow.set_fork_proposal_config(params.fork_proposal_config)
            workflow.set_peer_create_job_flags(params.peer_create_job_flags)
        self._session.add(workflow)
        # To get workflow id
        self._session.flush()
        if cron_config is not None:
            workflow.cron_config = cron_config
            update_cronjob_config(workflow.id, cron_config, self._session)
        self.setup_jobs(workflow)
        return workflow

    def config_workflow(self,
                        workflow: Workflow,
                        template_id: int,
                        config: Optional[WorkflowDefinition] = None,
                        forkable: bool = False,
                        comment: Optional[str] = None,
                        cron_config: Optional[str] = None,
                        create_job_flags: Optional[List[int]] = None,
                        creator_username: Optional[str] = None,
                        template_revision_id: Optional[int] = None) -> Workflow:
        if workflow.config:
            raise ValueError('Resetting workflow is not allowed')
        workflow.comment = comment
        workflow.forkable = forkable
        workflow.creator = creator_username
        workflow.set_config(config)
        workflow.set_create_job_flags(create_job_flags)
        workflow.update_target_state(WorkflowState.READY)
        workflow.template_id = template_id
        workflow.template_revision_id = template_revision_id
        self._session.flush()
        if workflow.template is None:
            emit_store('template_not_found', 1)
            raise ValueError('template not found')
        workflow.editor_info = workflow.template.editor_info
        if cron_config is not None:
            workflow.cron_config = cron_config
            update_cronjob_config(workflow.id, cron_config, self._session)
        self.setup_jobs(workflow)
        return workflow

    def patch_workflow(self,
                       workflow: Workflow,
                       forkable: Optional[bool] = None,
                       metric_is_public: Optional[bool] = None,
                       config: Optional[WorkflowDefinition] = None,
                       template_id: Optional[int] = None,
                       create_job_flags: List[int] = None,
                       cron_config: Optional[str] = None,
                       favour: Optional[bool] = None,
                       template_revision_id: Optional[int] = None):
        if forkable is not None:
            workflow.forkable = forkable
        if metric_is_public is not None:
            workflow.metric_is_public = metric_is_public

        if config:
            if workflow.target_state != WorkflowState.INVALID or \
                    workflow.state not in \
                    [WorkflowState.READY, WorkflowState.STOPPED, WorkflowState.COMPLETED,
                     WorkflowState.FAILED]:
                raise ValueError('Cannot edit running workflow')
            self.update_config(workflow, config)
            workflow.template_id = template_id
            self._session.flush()
            if workflow.template is not None:
                workflow.editor_info = workflow.template.editor_info
            self._session.flush()

        if create_job_flags:
            jobs = [self._session.query(Job).get(i) for i in workflow.get_job_ids()]
            if len(create_job_flags) != len(jobs):
                raise ValueError(f'Number of job defs does not match number of '
                                 f'create_job_flags {len(jobs)} vs {len(create_job_flags)}')
            workflow.set_create_job_flags(create_job_flags)
            flags = workflow.get_create_job_flags()
            for i, job in enumerate(jobs):
                if job.workflow_id == workflow.id:
                    job.is_disabled = flags[i] == \
                                      common_pb2.CreateJobFlag.DISABLED

        # start workflow periodically.
        # Session.commit inside, so this part must be the last of the api
        # to guarantee atomicity.
        if cron_config is not None:
            workflow.cron_config = cron_config
            update_cronjob_config(workflow.id, cron_config, self._session)

        if favour is not None:
            workflow.favour = favour

        if template_revision_id is not None:
            workflow.template_revision_id = template_revision_id

    def setup_jobs(self, workflow: Workflow):
        if workflow.forked_from is not None:
            trunk = self._session.query(Workflow).get(workflow.forked_from)
            assert trunk is not None, \
                f'Source workflow {workflow.forked_from} not found'
            trunk_job_defs = trunk.get_config().job_definitions
            trunk_name2index = {job.name: i for i, job in enumerate(trunk_job_defs)}

        job_defs = workflow.get_config().job_definitions
        flags = workflow.get_create_job_flags()
        assert len(job_defs) == len(flags), \
            f'Number of job defs does not match number of create_job_flags {len(job_defs)} vs {len(flags)}'
        jobs = []
        for i, (job_def, flag) in enumerate(zip(job_defs, flags)):
            if flag == common_pb2.CreateJobFlag.REUSE:
                assert job_def.name in trunk_name2index, \
                    f'Job {job_def.name} not found in base workflow'
                j = trunk.get_job_ids()[trunk_name2index[job_def.name]]
                job = self._session.query(Job).get(j)
                assert job is not None, f'Job {j} not found'
                # TODO: check forked jobs does not depend on non-forked jobs
            else:
                job = Job(name=build_job_name(workflow.uuid, job_def.name),
                          job_type=JobType(job_def.job_type),
                          workflow_id=workflow.id,
                          project_id=workflow.project_id,
                          state=JobState.NEW,
                          is_disabled=(flag == common_pb2.CreateJobFlag.DISABLED))
                self._session.add(job)
                self._session.flush()
                JobService(self._session).set_config_and_crd_info(job, job_def)
            jobs.append(job)
        self._session.refresh(workflow)
        name2index = {job.name: i for i, job in enumerate(job_defs)}
        for i, (job, flag) in enumerate(zip(jobs, flags)):
            if flag == common_pb2.CreateJobFlag.REUSE:
                continue
            for j, dep_def in enumerate(job.get_config().dependencies):
                dep = JobDependency(src_job_id=jobs[name2index[dep_def.source]].id, dst_job_id=job.id, dep_index=j)
                self._session.add(dep)

        workflow.set_job_ids([job.id for job in jobs])

    def get_peer_workflow(self, workflow: Workflow):
        service = ParticipantService(self._session)
        participants = service.get_platform_participants_by_project(workflow.project.id)
        # TODO: find coordinator for multiparty
        client = RpcClient.from_project_and_participant(workflow.project.name, workflow.project.token,
                                                        participants[0].domain_name)
        return client.get_workflow(workflow.uuid, workflow.name)

    def is_federated_workflow_finished(self, workflow: Workflow):
        if not workflow.is_finished():
            return False
        return workflow.is_local() or self.get_peer_workflow(workflow).is_finished

    def should_auto_stop(self, workflow: Workflow):
        return workflow.is_failed() or self.is_federated_workflow_finished(workflow)

    def update_config(self, workflow: Workflow, proto: WorkflowDefinition):
        workflow.set_config(proto)
        if proto is not None:
            job_defs = {i.name: i for i in proto.job_definitions}
            for job in workflow.owned_jobs:
                name = job.get_config().name
                assert name in job_defs, \
                    f'Invalid workflow template: job {name} is missing'
                JobService(self._session).set_config_and_crd_info(job, job_defs[name])
