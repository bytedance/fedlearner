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
import re
import json
from typing import Union, Optional

from sqlalchemy import desc
from sqlalchemy.orm.session import Session
from google.protobuf.json_format import ParseDict, ParseError

from fedlearner_webconsole.proto.filtering_pb2 import FilterOp, FilterExpression
from fedlearner_webconsole.utils.filtering import SupportedField, FieldType, FilterBuilder
from fedlearner_webconsole.utils.paginate import Pagination, paginate
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.workflow_template.models import WorkflowTemplate, WorkflowTemplateRevision, \
    WorkflowTemplateKind
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition, WorkflowTemplateEditorInfo
from fedlearner_webconsole.exceptions import InvalidArgumentException, NotFoundException
from fedlearner_webconsole.workflow_template.slots_formatter import \
    generate_yaml_template
from fedlearner_webconsole.workflow_template.template_validaor\
    import check_workflow_definition
from fedlearner_webconsole.exceptions import ResourceConflictException


def _validate_variable(variable):
    if variable.value_type == 'CODE':
        try:
            json.loads(variable.value)
        except json.JSONDecodeError as e:
            raise InvalidArgumentException(str(e)) from e
    return variable


def _format_template_with_yaml_editor(template_proto, editor_info_proto, session):
    for job_def in template_proto.job_definitions:
        # if job is in editor_info, than use meta_yaml format with
        # slots instead of yaml_template
        yaml_editor_infos = editor_info_proto.yaml_editor_infos
        if job_def.easy_mode and job_def.name in yaml_editor_infos:
            yaml_editor_info = yaml_editor_infos[job_def.name]
            job_def.yaml_template = generate_yaml_template(yaml_editor_info.meta_yaml, yaml_editor_info.slots)
    try:
        check_workflow_definition(template_proto, session)
    except ValueError as e:
        raise InvalidArgumentException(details={'config.yaml_template': str(e)}) from e
    return template_proto


def _check_config_and_editor_info(config, editor_info):
    # TODO: needs tests
    if 'group_alias' not in config:
        raise InvalidArgumentException(details={'config.group_alias': 'config.group_alias is required'})

    # form to proto buffer
    editor_info_proto = dict_to_editor_info(editor_info)
    template_proto = dict_to_workflow_definition(config)
    for index, job_def in enumerate(template_proto.job_definitions):
        # pod label name must be no more than 63 characters.
        #  workflow.uuid is 20 characters, pod name suffix such as
        #  '-follower-master-0' is less than 19 characters, so the
        #  job name must be no more than 24
        if len(job_def.name) > 24:
            raise InvalidArgumentException(
                details={f'config.job_definitions[{index}].job_name': 'job_name must be no more than 24 characters'})
        # limit from k8s
        if not re.match('[a-z0-9-]*', job_def.name):
            raise InvalidArgumentException(
                details={
                    f'config.job_definitions[{index}].job_name': 'Only letters(a-z), numbers(0-9) '
                                                                 'and dashes(-) are supported.'
                })
    return template_proto, editor_info_proto


def dict_to_workflow_definition(config):
    try:
        if config is None:
            config = {}
        template_proto = ParseDict(config, WorkflowDefinition(), ignore_unknown_fields=True)
        for variable in template_proto.variables:
            _validate_variable(variable)
        for job in template_proto.job_definitions:
            for variable in job.variables:
                _validate_variable(variable)
    except ParseError as e:
        raise InvalidArgumentException(details={'config': str(e)}) from e
    return template_proto


def dict_to_editor_info(editor_info):
    try:
        editor_info_proto = ParseDict(editor_info, WorkflowTemplateEditorInfo())
    except ParseError as e:
        raise InvalidArgumentException(details={'editor_info': str(e)}) from e
    return editor_info_proto


class WorkflowTemplateService:
    FILTER_FIELDS = {
        'name': SupportedField(type=FieldType.STRING, ops={FilterOp.CONTAIN: None}),
        'group_alias': SupportedField(type=FieldType.STRING, ops={FilterOp.EQUAL: None}),
        'kind': SupportedField(type=FieldType.NUMBER, ops={FilterOp.EQUAL: None}),
    }

    def __init__(self, session: Session):
        self._session = session
        self._filter_builder = FilterBuilder(model_class=WorkflowTemplate, supported_fields=self.FILTER_FIELDS)

    def post_workflow_template(self, name: str, comment: str, config: WorkflowDefinition,
                               editor_info: WorkflowTemplateEditorInfo, kind: int,
                               creator_username: str) -> Union[WorkflowTemplate, None]:
        if self._session.query(WorkflowTemplate).filter_by(name=name).first() is not None:
            raise ResourceConflictException(f'Workflow template {name} already exists')
        template_proto = _format_template_with_yaml_editor(config, editor_info, self._session)
        template = WorkflowTemplate(name=name,
                                    comment=comment,
                                    group_alias=template_proto.group_alias,
                                    kind=kind,
                                    creator_username=creator_username)
        template.set_config(template_proto)
        template.set_editor_info(editor_info)
        self._session.add(template)
        return template

    def get_workflow_template(self, name: str) -> WorkflowTemplate:
        template = self._session.query(WorkflowTemplate).filter(WorkflowTemplate.name == name).first()
        if template is None:
            raise NotFoundException(message=f'failed to find workflow template {name}')
        return template

    def list_workflow_templates(self,
                                page: Optional[int] = None,
                                page_size: Optional[int] = None,
                                filter_exp: Optional[FilterExpression] = None) -> Pagination:
        """Lists workflow templates by filter expression and pagination."""
        query = self._session.query(WorkflowTemplate)
        if filter_exp:
            query = self._filter_builder.build_query(query, filter_exp)
        query = query.order_by(WorkflowTemplate.id.desc())
        return paginate(query, page, page_size)


class WorkflowTemplateRevisionService:

    def __init__(self, session: Session):
        self._session = session

    def get_latest_revision(self, template_id: int) -> Optional[WorkflowTemplateRevision]:
        return self._session.query(WorkflowTemplateRevision).filter_by(template_id=template_id).order_by(
            desc(WorkflowTemplateRevision.revision_index)).first()

    def create_new_revision_if_template_updated(self, template_id: int):
        # Ensure revision generation not occurring concurrent.
        template = self._session.query(WorkflowTemplate).with_for_update().get(template_id)
        if template is None:
            raise NotFoundException(message=f'failed to find workflow template {template_id}')
        latest_revision = self.get_latest_revision(template_id)
        if latest_revision and latest_revision.config == template.config:
            return latest_revision
        new_revision = WorkflowTemplateRevision(revision_index=latest_revision.revision_index +
                                                1 if latest_revision else 1,
                                                config=template.config,
                                                editor_info=template.editor_info,
                                                template_id=template_id)
        self._session.add(new_revision)
        return new_revision

    def delete_revision(self, revision_id: int):
        revision = self._session.query(WorkflowTemplateRevision).get(revision_id)
        if revision is None:
            raise NotFoundException(message=f'failed to find template revision {revision_id}')
        if revision.revision_index == self.get_latest_revision(revision.template_id).revision_index:
            raise ResourceConflictException('can not delete the latest_revision')
        # Checks if there is any related workflow
        workflow = self._session.query(Workflow).filter_by(template_revision_id=revision_id).first()
        if workflow is not None:
            raise ResourceConflictException('revision has been used by workflows')
        self._session.query(WorkflowTemplateRevision).filter_by(id=revision_id).delete()

    def create_revision(self,
                        name: str,
                        kind: str,
                        config: WorkflowDefinition,
                        revision_index: int,
                        comment: Optional[str] = None,
                        peer_pure_domain: Optional[str] = None):
        tpl: WorkflowTemplate = self._session.query(WorkflowTemplate).filter_by(
            name=name, coordinator_pure_domain_name=peer_pure_domain).first()
        if tpl is None:
            tpl = WorkflowTemplate(name=name,
                                   comment=comment,
                                   coordinator_pure_domain_name=peer_pure_domain,
                                   kind=WorkflowTemplateKind[kind].value,
                                   group_alias=config.group_alias)
            tpl.set_config(config)
            self._session.add(tpl)
            self._session.flush()
        revision: WorkflowTemplateRevision = self._session.query(WorkflowTemplateRevision).filter_by(
            template_id=tpl.id, revision_index=revision_index).first()
        if revision is not None:
            return
        revision = WorkflowTemplateRevision(revision_index=revision_index, template_id=tpl.id, comment=comment)
        revision.set_config(config)
        self._session.add(revision)
        self._session.flush()
        tpl.config = self.get_latest_revision(tpl.id).config
