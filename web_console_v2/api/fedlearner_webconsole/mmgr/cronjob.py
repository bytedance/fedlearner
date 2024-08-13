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
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from google.protobuf.struct_pb2 import Value

from fedlearner_webconsole.db import db
from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.composer.context import RunnerContext
from fedlearner_webconsole.composer.interface import IRunnerV2
from fedlearner_webconsole.composer.models import RunnerStatus
from fedlearner_webconsole.proto.composer_pb2 import RunnerOutput, ModelTrainingCronJobOutput
from fedlearner_webconsole.mmgr.service import ModelJobGroupService
from fedlearner_webconsole.mmgr.controller import LaunchModelJob
from fedlearner_webconsole.mmgr.models import ModelJobGroup
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition
from fedlearner_webconsole.proto.common_pb2 import Variable

LOAD_MODEL_NAME = 'load_model_name'


class ModelTrainingCronJob(IRunnerV2):
    """Launch model job periodically."""

    @staticmethod
    def _set_load_model_name(config: WorkflowDefinition, job_name: str):
        """Set variable of load_model_name inplace"""
        assert len(config.job_definitions) == 1
        for variable in config.job_definitions[0].variables:
            if variable.name == LOAD_MODEL_NAME:
                assert variable.value_type == Variable.ValueType.STRING
                variable.value = job_name
                variable.typed_value.MergeFrom(Value(string_value=job_name))

    def _update_local_and_peer_config(self, session: Session, group_id: int):
        group: ModelJobGroup = session.query(ModelJobGroup).get(group_id)
        model_job = group.latest_completed_job()
        if model_job is None:
            return
        job_name = model_job.job_name
        config = group.get_config()
        self._set_load_model_name(config=config, job_name=job_name)
        group.set_config(config)
        for party in group.project.participants:
            client = RpcClient.from_project_and_participant(project_name=group.project.name,
                                                            project_token=group.project.token,
                                                            domain_name=party.domain_name)
            config = client.get_model_job_group(model_job_group_uuid=group.uuid).config
            self._set_load_model_name(config=config, job_name=job_name)
            client.update_model_job_group(model_job_group_uuid=group.uuid, config=config)

    def _check_peer_auth_status(self, session: Session, group_id: int) -> Tuple[bool, Optional[str]]:
        group: ModelJobGroup = session.query(ModelJobGroup).get(group_id)
        for party in group.project.participants:
            client = RpcClient.from_project_and_participant(project_name=group.project.name,
                                                            project_token=group.project.token,
                                                            domain_name=party.domain_name)
            resp = client.get_model_job_group(model_job_group_uuid=group.uuid)
            if not resp.authorized:
                return False, party.domain_name
        return True, None

    def run(self, context: RunnerContext) -> Tuple[RunnerStatus, RunnerOutput]:
        output = ModelTrainingCronJobOutput()
        group_id = context.input.model_training_cron_job_input.group_id
        with db.session_scope() as session:
            authorized, domain_name = self._check_peer_auth_status(session=session, group_id=group_id)
            if not authorized:
                message = f'party {domain_name} is not authorized for group {group_id}'
                logging.warning(f'[ModelTrainingCronJob] {message}')
                return RunnerStatus.FAILED, RunnerOutput(error_message=message)
            group = ModelJobGroupService(session).lock_and_update_version(group_id)
            session.commit()
        with db.session_scope() as session:
            self._update_local_and_peer_config(session, group.id)
            session.commit()
        succeeded, msg = LaunchModelJob().run(project_id=group.project_id,
                                              group_id=group_id,
                                              version=group.latest_version)
        if not succeeded:
            message = f'launching model job for group {group_id} by 2PC with message: {msg}'
            output.message = message
            logging.warning(f'[ModelTrainingCronJob] {message}')
            return RunnerStatus.FAILED, RunnerOutput(model_training_cron_job_output=output)
        message = f'succeeded in launch model job for group {group_id}'
        logging.info(f'[ModelTrainingCronJob] {message}')
        output.message = message
        return RunnerStatus.DONE, RunnerOutput(model_training_cron_job_output=output)
