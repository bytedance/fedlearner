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
"""A tool to find workflow/templates related with an variable.

Execute internally:
```
export PRE_START_HOOK=hook:before_app_start
FLASK_APP=command:app flask find-variable <var_name>
```

Otherwise:
```
FLASK_APP=command:app flask find-variable <var_name>
```
"""
import logging
from typing import Union
from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState
from fedlearner_webconsole.workflow_template.models import WorkflowTemplate, WorkflowTemplateRevision


def _contains_var(config: Union[WorkflowDefinition, None], var_name: str) -> bool:
    if not config:
        return False
    for var in config.variables:
        if var.name == var_name:
            return True
    for job in config.job_definitions:
        for var in job.variables:
            if var.name == var_name:
                return True
    return False


def find(variable_name: str):
    with db.session_scope() as session:
        templates = session.query(WorkflowTemplate.id).all()
        for tid, *_ in templates:
            template: WorkflowTemplate = session.query(WorkflowTemplate).get(tid)
            if _contains_var(template.get_config(), variable_name):
                logging.info(f'[Found variable {variable_name}] template id: {template.id}, name: {template.name}')

        revisions = session.query(WorkflowTemplateRevision.id).all()
        for rid, *_ in revisions:
            revision: WorkflowTemplateRevision = session.query(WorkflowTemplateRevision).get(rid)
            if _contains_var(revision.get_config(), variable_name):
                logging.info(
                    f'[Found variable {variable_name}] revision id: {revision.id}, template id: {revision.template_id}')

        workflows = session.query(Workflow.id).filter(
            Workflow.state.in_((WorkflowState.NEW, WorkflowState.READY, WorkflowState.RUNNING))).all()
        for wid, *_ in workflows:
            workflow: Workflow = session.query(Workflow).get(wid)
            if _contains_var(workflow.get_config(), variable_name):
                logging.info(f'[Found variable {variable_name}] workflow id: {workflow.id}, name: {workflow.name},'
                             f' state: {workflow.get_state_for_frontend()}')
