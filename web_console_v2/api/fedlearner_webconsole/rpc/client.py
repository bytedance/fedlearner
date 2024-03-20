# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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
# pylint: disable=broad-except

import logging
from functools import wraps

import grpc

from envs import Envs
from fedlearner_webconsole.exceptions import (
    UnauthorizedException, InvalidArgumentException
)
from fedlearner_webconsole.proto import (
    service_pb2, service_pb2_grpc, common_pb2
)
from fedlearner_webconsole.utils.decorators import retry_fn


def _build_channel(url, authority):
    """A helper function to build gRPC channel for easy testing."""
    return grpc.insecure_channel(
        target=url,
        # options defined at
        # https://github.com/grpc/grpc/blob/master/include/grpc/impl/codegen/grpc_types.h
        options=[('grpc.default_authority', authority)])


def catch_and_fallback(resp_class):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except grpc.RpcError as e:
                return resp_class(status=common_pb2.Status(
                    code=common_pb2.STATUS_UNKNOWN_ERROR, msg=repr(e)))

        return wrapper

    return decorator


class RpcClient(object):
    def __init__(self, project_config, receiver_config):
        self._project = project_config
        self._receiver = receiver_config
        self._auth_info = service_pb2.ProjAuthInfo(
            project_name=self._project.name,
            target_domain=self._receiver.domain_name,
            auth_token=self._project.token)

        egress_url = 'fedlearner-stack-ingress-nginx-controller.default.svc:80'
        for variable in self._project.variables:
            if variable.name == 'EGRESS_URL':
                egress_url = variable.value
                break
        self._client = service_pb2_grpc.WebConsoleV2ServiceStub(
            _build_channel(egress_url, self._receiver.grpc_spec.authority))

    def _get_metadata(self):
        metadata = []
        x_host_prefix = 'fedlearner-webconsole-v2'
        for variable in self._project.variables:
            if variable.name == 'X_HOST':
                x_host_prefix = variable.value
                break
        metadata.append(('x-host', '{}.{}'.format(x_host_prefix,
                                                  self._receiver.domain_name)))
        for key, value in self._receiver.grpc_spec.extra_headers.items():
            metadata.append((key, value))
        # metadata is a tuple of tuples
        return tuple(metadata)

    @catch_and_fallback(resp_class=service_pb2.CheckConnectionResponse)
    @retry_fn(retry_times=3, needed_exceptions=[grpc.RpcError])
    def check_connection(self):
        msg = service_pb2.CheckConnectionRequest(auth_info=self._auth_info)
        response = self._client.CheckConnection(
            request=msg,
            metadata=self._get_metadata(),
            timeout=Envs.GRPC_CLIENT_TIMEOUT)
        if response.status.code != common_pb2.STATUS_SUCCESS:
            logging.debug('check_connection request error: %s',
                          response.status.msg)
        return response

    @catch_and_fallback(resp_class=service_pb2.UpdateWorkflowStateResponse)
    @retry_fn(retry_times=3, needed_exceptions=[grpc.RpcError])
    def update_workflow_state(self, name, state, target_state,
                              transaction_state, uuid, forked_from_uuid,
                              extra=''):
        msg = service_pb2.UpdateWorkflowStateRequest(
            auth_info=self._auth_info,
            workflow_name=name,
            state=state.value,
            target_state=target_state.value,
            transaction_state=transaction_state.value,
            uuid=uuid,
            forked_from_uuid=forked_from_uuid,
            extra=extra
        )
        response = self._client.UpdateWorkflowState(
            request=msg, metadata=self._get_metadata(),
            timeout=Envs.GRPC_CLIENT_TIMEOUT)
        if response.status.code != common_pb2.STATUS_SUCCESS:
            logging.debug('update_workflow_state request error: %s',
                          response.status.msg)
        return response

    @catch_and_fallback(resp_class=service_pb2.GetWorkflowResponse)
    @retry_fn(retry_times=3, needed_exceptions=[grpc.RpcError])
    def get_workflow(self, name):
        msg = service_pb2.GetWorkflowRequest(auth_info=self._auth_info,
                                             workflow_name=name)
        response = self._client.GetWorkflow(request=msg,
                                            metadata=self._get_metadata(),
                                            timeout=Envs.GRPC_CLIENT_TIMEOUT)

        if response.status.code != common_pb2.STATUS_SUCCESS:
            logging.debug('get_workflow request error: %s',
                          response.status.msg)
        return response

    @catch_and_fallback(resp_class=service_pb2.UpdateWorkflowResponse)
    @retry_fn(retry_times=3, needed_exceptions=[grpc.RpcError])
    def update_workflow(self, name, config):
        msg = service_pb2.UpdateWorkflowRequest(auth_info=self._auth_info,
                                                workflow_name=name,
                                                config=config)
        response = self._client.UpdateWorkflow(request=msg,
                                               metadata=self._get_metadata(),
                                               timeout=Envs.GRPC_CLIENT_TIMEOUT)

        if response.status.code != common_pb2.STATUS_SUCCESS:
            logging.debug('update_workflow request error: %s',
                          response.status.msg)
        return response

    @catch_and_fallback(resp_class=service_pb2.GetJobMetricsResponse)
    @retry_fn(retry_times=3, needed_exceptions=[grpc.RpcError])
    def get_job_metrics(self, job_name):
        msg = service_pb2.GetJobMetricsRequest(auth_info=self._auth_info,
                                               job_name=job_name)
        response = self._client.GetJobMetrics(request=msg,
                                              metadata=self._get_metadata(),
                                              timeout=Envs.GRPC_CLIENT_TIMEOUT)

        if response.status.code != common_pb2.STATUS_SUCCESS:
            logging.debug('get_job_metrics request error: %s',
                          response.status.msg)
        return response

    @catch_and_fallback(resp_class=service_pb2.GetJobMetricsResponse)
    @retry_fn(retry_times=3, needed_exceptions=[grpc.RpcError])
    def get_job_kibana(self, job_name, json_args):
        msg = service_pb2.GetJobKibanaRequest(auth_info=self._auth_info,
                                              job_name=job_name,
                                              json_args=json_args)
        response = self._client.GetJobKibana(request=msg,
                                             metadata=self._get_metadata(),
                                             timeout=Envs.GRPC_CLIENT_TIMEOUT)
        status = response.status
        if status.code != common_pb2.STATUS_SUCCESS:
            if status.code == common_pb2.STATUS_UNAUTHORIZED:
                raise UnauthorizedException(status.msg)
            if status.code == common_pb2.STATUS_INVALID_ARGUMENT:
                raise InvalidArgumentException(status.msg)
            logging.debug('get_job_kibana request error: %s',
                          response.status.msg)
        return response

    @catch_and_fallback(resp_class=service_pb2.GetJobEventsResponse)
    @retry_fn(retry_times=3, needed_exceptions=[grpc.RpcError])
    def get_job_events(self, job_name, start_time, max_lines):
        msg = service_pb2.GetJobEventsRequest(auth_info=self._auth_info,
                                              job_name=job_name,
                                              start_time=start_time,
                                              max_lines=max_lines)
        response = self._client.GetJobEvents(request=msg,
                                             metadata=self._get_metadata(),
                                             timeout=Envs.GRPC_CLIENT_TIMEOUT)

        if response.status.code != common_pb2.STATUS_SUCCESS:
            logging.debug('get_job_events request error: %s',
                          response.status.msg)
        return response

    @catch_and_fallback(resp_class=service_pb2.CheckJobReadyResponse)
    @retry_fn(retry_times=3, needed_exceptions=[grpc.RpcError])
    def check_job_ready(self, job_name: str) \
            -> service_pb2.CheckJobReadyResponse:
        msg = service_pb2.CheckJobReadyRequest(auth_info=self._auth_info,
                                               job_name=job_name)
        response = self._client.CheckJobReady(request=msg,
                                              timeout=Envs.GRPC_CLIENT_TIMEOUT,
                                              metadata=self._get_metadata())

        if response.status.code != common_pb2.STATUS_SUCCESS:
            logging.debug('check_job_ready request error: %s',
                          response.status.msg)
        return response
