#  Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#  coding: utf-8
import grpc
import json
import logging
from functools import wraps
from typing import Optional, Dict, Tuple, Callable
from envs import Envs
from flask import request
from google.protobuf.message import Message
from google.protobuf.empty_pb2 import Empty
from fedlearner_webconsole.audit.services import EventService
from fedlearner_webconsole.db import db
from fedlearner_webconsole.utils.const import API_VERSION
from fedlearner_webconsole.utils.flask_utils import get_current_user
from fedlearner_webconsole.utils.metrics import emit_store
from fedlearner_webconsole.proto.audit_pb2 import Event
from fedlearner_webconsole.proto.common_pb2 import StatusCode
from fedlearner_webconsole.proto.service_pb2 import TwoPcRequest
from fedlearner_webconsole.exceptions import UnauthorizedException, InvalidArgumentException
from fedlearner_webconsole.utils.domain_name import get_pure_domain_name
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.utils.proto import to_dict
from fedlearner_webconsole.rpc.auth import get_common_name, PROJECT_NAME_HEADER, SSL_CLIENT_SUBJECT_DN_HEADER
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.proto.two_pc_pb2 import TwoPcType
# TODO(wangsen.0914): IAM and SYSTEM WIP

RESOURCE_TYPE_MAPPING = {
    'projects': Event.ResourceType.WORKSPACE,
    'workflow_templates': Event.ResourceType.TEMPLATE,
    'workflows': Event.ResourceType.WORKFLOW,
    'datasets': Event.ResourceType.DATASET,
    'models': Event.ResourceType.MODEL,
    'auth': Event.ResourceType.USER,
    'participants': Event.ResourceType.PARTICIPANT,
    'serving_services': Event.ResourceType.SERVING_SERVICE,
    'algorithm_projects': Event.ResourceType.ALGORITHM_PROJECT,
    'preset_algorithms': Event.ResourceType.PRESET_ALGORITHM
}

OP_TYPE_MAPPING = {
    'post': Event.OperationType.CREATE,
    'patch': Event.OperationType.UPDATE,
    'put': Event.OperationType.UPDATE,
    'delete': Event.OperationType.DELETE
}

STATUS_TYPE_MAPPING = {
    StatusCode.STATUS_SUCCESS: grpc.StatusCode.OK.name,
    StatusCode.STATUS_UNKNOWN_ERROR: grpc.StatusCode.UNKNOWN.name,
    StatusCode.STATUS_UNAUTHORIZED: grpc.StatusCode.UNAUTHENTICATED.name,
    StatusCode.STATUS_NOT_FOUND: grpc.StatusCode.NOT_FOUND.name,
    StatusCode.STATUS_INVALID_ARGUMENT: grpc.StatusCode.INVALID_ARGUMENT.name
}

RESULT_TYPE_MAPPING = {
    Event.Result.UNKNOWN_RESULT: grpc.StatusCode.UNKNOWN.name,
    Event.Result.SUCCESS: grpc.StatusCode.OK.name,
    Event.Result.FAILURE: grpc.StatusCode.ABORTED.name
}


def emits_event(resource_type: Event.ResourceType = Event.ResourceType.UNKNOWN_RESOURCE_TYPE,
                op_type: Event.OperationType = Event.OperationType.UNKNOWN_OPERATION_TYPE,
                audit_fields: Optional[list] = None):

    def wrapper_func(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if user is None:
                return func(*args, **kwargs)
            fields, result = _infer_event_fields(resource_type, op_type, audit_fields), Event.Result.SUCCESS
            try:
                data, *_ = func(*args, **kwargs)
                if fields['op_type'] == Event.OperationType.CREATE:
                    fields['resource_name'] += f'/{data.get("data").get("id")}'
                return (data, *_)
            except Exception as e:
                result = Event.Result.FAILURE
                raise e
            finally:
                # TODO(yeqiuhan): deprecate result in two release cut
                _emit_event(user_id=user.id, result=result, result_code=RESULT_TYPE_MAPPING[result], fields=fields)

        return wrapper

    return wrapper_func


# TODO(yeqiuhan): Call local server for operation


def emits_rpc_event(
    resource_name_fn: Callable[[Message], str],
    resource_type: Event.ResourceType = Event.ResourceType.UNKNOWN_RESOURCE_TYPE,
    op_type: Event.OperationType = Event.OperationType.UNKNOWN_OPERATION_TYPE,
):

    def wrapper_func(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            func_params = _get_func_params(func, *args, **kwargs)
            fields = _infer_rpc_event_fields(func_params, resource_type, resource_name_fn, op_type)
            try:
                response = func(*args, **kwargs)
                return response
            except Exception as e:
                raise e
            finally:
                # use public interface to get status code until upgrade of grpc from 1.32 to 1.38+
                if func_params['context']._state.code is not None:  # pylint: disable=protected-access
                    result_code = func_params['context']._state.code.name  # pylint: disable=protected-access
                else:
                    if isinstance(response, Empty) or response.DESCRIPTOR.fields_by_name.get('status') is None:
                        result_code = 'OK'
                    elif isinstance(response.status.code, int):
                        result_code = STATUS_TYPE_MAPPING[response.status.code]
                    else:
                        result_code = 'UNKNOWN'
                _emit_event(user_id=None,
                            result=Event.Result.SUCCESS if result_code == 'OK' else Event.Result.FAILURE,
                            result_code=result_code,
                            fields=fields)

        return wrapper

    return wrapper_func


def _infer_event_fields(resource_type: Event.ResourceType = Event.ResourceType.UNKNOWN_RESOURCE_TYPE,
                        op_type: Event.OperationType = Event.OperationType.UNKNOWN_OPERATION_TYPE,
                        audit_fields: Optional[list] = None) -> Dict[str, any]:
    # path: API_PATH_PREFIX/resource_type/...
    if resource_type == Event.ResourceType.UNKNOWN_RESOURCE_TYPE:
        resource_type = RESOURCE_TYPE_MAPPING.get(request.path.partition(API_VERSION)[-1].split('/')[1].lower())
    if op_type == Event.OperationType.UNKNOWN_OPERATION_TYPE:
        op_type = OP_TYPE_MAPPING.get(request.method.lower())
    body = request.get_json(force=True, silent=True)
    resource_name = request.path.rpartition(API_VERSION)[-1]
    extra = {k: body.get(k) for k in audit_fields} if audit_fields else {}
    coordinator_pure_domain_name = SettingService.get_system_info().pure_domain_name
    return {
        'name': Event.OperationType.Name(op_type).lower() + Event.ResourceType.Name(resource_type).capitalize(),
        'resource_type': resource_type,
        'resource_name': resource_name,
        'op_type': op_type,
        # TODO(wangsen.0914): source depends on credentials
        'source': Event.Source.UI,
        'extra': json.dumps(extra),
        'coordinator_pure_domain_name': coordinator_pure_domain_name
    }


def _get_func_params(func, *args, **kwargs):
    dict_param = {}
    for arg in list(kwargs.values()) + list(args):
        if isinstance(arg, grpc.ServicerContext):
            dict_param['context'] = arg
        if isinstance(arg, Message):
            dict_param['request'] = arg
    return dict_param


def _infer_auth_info(rpc_request, context) -> Tuple[Optional[str], Optional[int]]:
    if Envs.FLASK_ENV == 'production':
        metadata = dict(context.invocation_metadata())
        if not metadata:
            raise UnauthorizedException('No client subject dn found')
        cn = get_common_name(metadata.get(SSL_CLIENT_SUBJECT_DN_HEADER))
        if not cn:
            raise UnauthorizedException('Failed to get domain name from certs')
        pure_domain_name = get_pure_domain_name(cn)
        with db.session_scope() as session:
            if 'auth_info' in rpc_request.keys():  # v1
                project_name = rpc_request['auth_info']['project_name']
            else:  # v2
                project_name = metadata.get(PROJECT_NAME_HEADER)
            project = session.query(Project).filter_by(name=project_name).first()
            project_id = project.id if project is not None else None
        return pure_domain_name, project_id
    return (None, None)


def _infer_rpc_event_fields(func_params: Dict[str, any], resource_type: Event.ResourceType,
                            resource_name_fn: Callable[[Message], str], op_type: Event.OperationType) -> Dict[str, any]:
    request_type = type(func_params['request'])
    if resource_name_fn is None:
        raise InvalidArgumentException('Callable resource_name_fn required')
    resource_uuid = resource_name_fn(func_params['request'])
    rpc_request = to_dict(func_params['request'])
    context = func_params['context']
    if request_type is TwoPcRequest:
        type_list = rpc_request['type'].split('_')
        if type_list[-1] == 'STATE':
            op_type = Event.OperationType.Value(type_list[0] + '_' + type_list[-1])
            resource_type = Event.ResourceType.Value('_'.join(type_list[1:-1]))
        else:
            op_type = Event.OperationType.Value(type_list[0])
            resource_type = Event.ResourceType.Value('_'.join(type_list[1:]))
    # get domain_name and project_name
    pure_domain_name, project_id = _infer_auth_info(rpc_request, context)
    return {
        'name': str(request_type)[str(request_type).rfind('.') + 1:str(request_type).rfind('Request')],
        'op_type': op_type,
        'resource_type': resource_type,
        'resource_name': resource_uuid,
        'coordinator_pure_domain_name': pure_domain_name,
        'project_id': project_id,
        'source': Event.Source.RPC
    }


def _emit_event(user_id: Optional[int], result: Event.Result, result_code: str, fields: dict) -> None:
    event = Event(user_id=user_id, result=result, result_code=result_code, **fields)
    try:
        with db.session_scope() as session:
            EventService(session).emit_event(event)
            session.commit()
    except ValueError as e:
        logging.error(f'[audit.decorator] invalid argument passed: {e}')
        emit_store('audit_invalid_arguments', 1)


def get_two_pc_request_uuid(rpc_request: TwoPcRequest) -> Optional[str]:
    if rpc_request.type == TwoPcType.CREATE_MODEL_JOB:
        return rpc_request.data.create_model_job_data.model_job_uuid
    if rpc_request.type == TwoPcType.CONTROL_WORKFLOW_STATE:
        return rpc_request.data.transit_workflow_state_data.workflow_uuid
    if rpc_request.type == TwoPcType.CREATE_MODEL_JOB_GROUP:
        return rpc_request.data.create_model_job_group_data.model_job_group_uuid
    if rpc_request.type == TwoPcType.LAUNCH_DATASET_JOB:
        return rpc_request.data.launch_dataset_job_data.dataset_job_uuid
    if rpc_request.type == TwoPcType.STOP_DATASET_JOB:
        return rpc_request.data.stop_dataset_job_data.dataset_job_uuid
    if rpc_request.type == TwoPcType.CREATE_TRUSTED_JOB_GROUP:
        return rpc_request.data.create_trusted_job_group_data.algorithm_uuid
    if rpc_request.type == TwoPcType.LAUNCH_TRUSTED_JOB:
        return rpc_request.data.launch_trusted_job_data.uuid
    if rpc_request.type == TwoPcType.STOP_TRUSTED_JOB:
        return rpc_request.data.stop_trusted_job_data.uuid
    if rpc_request.type == TwoPcType.LAUNCH_DATASET_JOB_STAGE:
        return rpc_request.data.launch_dataset_job_stage_data.dataset_job_stage_uuid
    if rpc_request.type == TwoPcType.STOP_DATASET_JOB_STAGE:
        return rpc_request.data.stop_dataset_job_stage_data.dataset_job_stage_uuid
    logging.warning('[TwoPc] Unsupported TwoPcType!')
    return None
