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

import hashlib
import json
import logging
import os
import traceback
from typing import Tuple

from google.protobuf.json_format import MessageToDict
from multiprocessing import Queue
from sqlalchemy.orm import Session, joinedload

from fedlearner_webconsole.composer.composer_service import ComposerService
from fedlearner_webconsole.composer.context import RunnerContext
from fedlearner_webconsole.composer.interface import ItemType, IRunnerV2
from fedlearner_webconsole.composer.models import RunnerStatus
from fedlearner_webconsole.db import db
from fedlearner_webconsole.exceptions import NotFoundException
from fedlearner_webconsole.proto import serving_pb2
from fedlearner_webconsole.proto.composer_pb2 import RunnerInput, RunnerOutput
from fedlearner_webconsole.proto.serving_pb2 import ServingServiceType
from fedlearner_webconsole.serving.models import ServingModel, ServingNegotiator, ServingModelStatus, ServingDeployment
from fedlearner_webconsole.serving.services import NegotiatorServingService, SavedModelService, \
    TensorflowServingService, ServingModelService
from fedlearner_webconsole.utils import pp_datetime
from fedlearner_webconsole.utils.file_manager import FileManager
from fedlearner_webconsole.utils.pp_time import sleep
from fedlearner_webconsole.utils.process_utils import get_result_by_sub_process
from fedlearner_webconsole.mmgr.service import ModelJobGroupService
from fedlearner_webconsole.project.models import Project


def _update_parsed_signature(q: Queue, model_path: str):
    file_manager = FileManager()
    exported_dirs = file_manager.ls(model_path, include_directory=True)
    newest_version = max([int(os.path.basename(v.path)) for v in exported_dirs if os.path.basename(v.path).isnumeric()])
    pb_path = os.path.join(model_path, str(newest_version), 'saved_model.pb')
    saved_model_bytes = file_manager.read_bytes(pb_path)
    signature_from_saved_model = SavedModelService.get_parse_example_details(saved_model_bytes)
    q.put(signature_from_saved_model)


class ModelSignatureParser(IRunnerV2):
    """ Parse example from model saved path
    """

    def __init__(self) -> None:
        self.PARSE_TIMES = 10

    def run(self, context: RunnerContext) -> Tuple[RunnerStatus, RunnerOutput]:
        serving_model_id = context.input.model_signature_parser_input.serving_model_id
        try:
            for num in range(0, self.PARSE_TIMES):
                with db.session_scope() as session:
                    # update parsed signature in serving model
                    serving_model = session.query(ServingModel).filter_by(id=serving_model_id).one_or_none()
                    if not serving_model:
                        raise NotFoundException(f'Failed to find serving model: {serving_model_id}')
                    signature_from_saved_model = get_result_by_sub_process(name='serving parse signature',
                                                                           target=_update_parsed_signature,
                                                                           kwargs={
                                                                               'model_path': serving_model.model_path,
                                                                           })
                    signature_dict = MessageToDict(signature_from_saved_model)
                    # update raw signature in serving negotiator
                    deployment_name = serving_model.serving_deployment.deployment_name
                    tf_serving_service = TensorflowServingService(deployment_name)
                    signature_from_tf = tf_serving_service.get_model_signature()
                    raw_signature = json.dumps(signature_from_tf)
                    if len(raw_signature) > 0 and raw_signature != '{}':
                        update_serving_negotiator = session.query(ServingNegotiator).filter_by(
                            serving_model_id=serving_model.id).one_or_none()
                        update_serving_negotiator.raw_signature = raw_signature
                        # add outputs to parsed signature
                        signature_dict['outputs'] = signature_from_tf['outputs']
                        signature_dict['from_participants'] = signature_from_tf['inputs']
                        if 'examples' in signature_dict['from_participants']:
                            signature_dict['from_participants'].pop('examples')
                        serving_model.signature = json.dumps(signature_dict)
                        session.commit()
                        return RunnerStatus.DONE, RunnerOutput()
                sleep(3)
        except Exception:  # pylint: disable=broad-except
            error_message = f'[ModelSignatureParser] failed to run, serving id={serving_model_id}'
            logging.exception(error_message)
        return RunnerStatus.FAILED, RunnerOutput(error_message='[ModelSignatureParser] failed to get signature from tf')

    @staticmethod
    def generate_task_name(serving_model_id: int, name: str):
        hash_value = hashlib.sha256(str(pp_datetime.now()).encode('utf8'))
        return f'parse_signature_{serving_model_id}_{name}_{hash_value.hexdigest()[0:6]}'


class QueryParticipantStatusRunner(IRunnerV2):

    def run(self, context: RunnerContext) -> Tuple[RunnerStatus, RunnerOutput]:
        self._auto_run_query()
        return RunnerStatus.DONE, RunnerOutput()

    @staticmethod
    def _auto_run_query():
        with db.session_scope() as session:
            query = session.query(ServingNegotiator)
            query = query.filter(ServingNegotiator.is_local.is_(False))
            query = query.outerjoin(ServingNegotiator.serving_model).options(joinedload(
                ServingNegotiator.serving_model)).filter(ServingModel.status == ServingModelStatus.PENDING_ACCEPT)
            query = query.outerjoin(Project, Project.id == ServingNegotiator.project_id).options(
                joinedload(ServingNegotiator.project))
            all_records = query.all()
        for serving_negotiator in all_records:
            with db.session_scope() as session:
                serving_model = serving_negotiator.serving_model
                try:
                    result = NegotiatorServingService(session).operate_participant_serving_service(
                        serving_negotiator, ServingServiceType.SERVING_SERVICE_QUERY)
                    if result == serving_pb2.SERVING_SERVICE_SUCCESS:
                        serving_model.status = ServingModelStatus.LOADING
                        session.add(serving_model)
                        session.commit()
                except Exception as e:  # pylint: disable=broad-except
                    logging.warning(f'[QueryParticipantStatusRunner] auto run query participant'
                                    f' for {serving_model.name} with error {e}, trace: {traceback.format_exc()}')


class UpdateModelRunner(IRunnerV2):

    def run(self, context: RunnerContext) -> Tuple[RunnerStatus, RunnerOutput]:
        self._auto_run_update()
        return RunnerStatus.DONE, RunnerOutput()

    @staticmethod
    def _auto_run_update():
        with db.session_scope() as session:
            all_records = session.query(ServingModel).filter(ServingModel.model_group_id.isnot(None)).outerjoin(
                ServingDeployment, ServingDeployment.id == ServingModel.serving_deployment_id).options(
                    joinedload(ServingModel.serving_deployment)).all()
        for serving_model in all_records:
            with db.session_scope() as session:
                try:
                    model = ModelJobGroupService(session).get_latest_model_from_model_group(
                        serving_model.model_group_id)
                    if serving_model.model_id == model.id:
                        # already serving the latest model
                        continue
                    serving_model.model_id = model.id
                    serving_model.model_path = model.get_exported_model_path()
                    if serving_model.serving_deployment.is_remote_serving():
                        ServingModelService(session).update_remote_serving_model(serving_model)
                    session.add(serving_model)
                    session.commit()
                except Exception as e:  # pylint: disable=broad-except
                    logging.warning(
                        f'[UpdateModelRunner] auto run update model for {serving_model.name} with error {e}, '
                        f'trace: {traceback.format_exc()}')


def start_query_participant(session: Session):
    composer_service_name = 'serving_model_query_participant_status_v2'
    composer_service = ComposerService(session)
    if composer_service.get_item_status(composer_service_name) is not None:
        return
    runner_input = RunnerInput()
    composer_service.collect_v2(
        name=composer_service_name,
        items=[(ItemType.SERVING_SERVICE_QUERY_PARTICIPANT_STATUS, runner_input)],
        # cron job at every 10 seconds
        cron_config='* * * * * */10')


def start_update_model(session: Session):
    composer_service_name = 'serving_model_update_model_v2'
    composer_service = ComposerService(session)
    if composer_service.get_item_status(composer_service_name) is not None:
        return
    runner_input = RunnerInput()
    composer_service.collect_v2(
        name=composer_service_name,
        items=[(ItemType.SERVING_SERVICE_UPDATE_MODEL, runner_input)],
        # cron job at every 30 seconds
        cron_config='* * * * * */30')
