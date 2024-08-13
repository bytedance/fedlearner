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

from fedlearner_webconsole.db import db
from fedlearner_webconsole.workflow.models import Workflow, WorkflowState


def migrate_workflow_completed_failed_state():
    logging.info('[migration]: start migrate workflow completed and failed state')
    with db.session_scope() as session:
        w_ids = session.query(Workflow.id).filter_by(state=WorkflowState.STOPPED).all()
        logging.info(f'[migration]: {len(w_ids)} STOPPED workflows need to be migrated')
    failed_ids = []
    for w_id in w_ids:
        try:
            with db.session_scope() as session:
                workflow = session.query(Workflow).get(w_id)
                if workflow.is_finished():
                    logging.info(f'[migration]: {workflow.name} workflow state change to COMPLETED')
                    workflow.state = WorkflowState.COMPLETED
                elif workflow.is_failed():
                    logging.info(f'[migration]: {workflow.name} workflow state change to FAILED')
                    workflow.state = WorkflowState.FAILED
                session.commit()
        except Exception as e:  # pylint: disable=broad-except
            failed_ids.append(w_id)
            logging.error(f'[migration]: {workflow.name} workflow state changed failed: {str(e)}')
    if failed_ids:
        logging.error(f'[migration]: {failed_ids} failed')
    logging.info('[migration]: finish migrate workflow completed and failed state')
