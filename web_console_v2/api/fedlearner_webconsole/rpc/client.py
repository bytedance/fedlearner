# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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
import grpc
from fedlearner_webconsole.proto import (service_pb2, service_pb2_grpc,
                                         common_pb2)
from fedlearner_webconsole.exceptions import NeedToRetryException
from fedlearner_webconsole.utils.decorators import retry_fn


def _build_channel(url, authority):
    """A helper function to build gRPC channel for easy testing."""
    return grpc.insecure_channel(
        target=url,
        # options defined at
        # https://github.com/grpc/grpc/blob/master/include/grpc/impl/codegen/grpc_types.h
        options=[('grpc.default_authority', authority)])


class RpcClient(object):
    def __init__(self, project_config, receiver_config):
        self._project = project_config
        self._receiver = receiver_config
        self._auth_info = service_pb2.ProjAuthInfo(
            project_name=self._project.name,
            target_domain=self._receiver.domain_name,
            auth_token=self._project.token)

        egress_url = 'fedlearner-stack-ingress-nginx-controller.default'\
                     '.svc.cluster.local:80'
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

    @staticmethod
    def _grpc_error_need_recover(e):
        if e.code() in (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.INTERNAL):
            return True
        if e.code() == grpc.StatusCode.UNKNOWN:
            httpstatus = RpcClient._grpc_error_get_http_status(e.details())
            # catch all header with non-200 OK
            if httpstatus:
                return True
        return False

    @staticmethod
    def _grpc_error_get_http_status(details):
        try:
            if details.count("http2 header with status") > 0:
                fields = details.split(":")
                if len(fields) == 2:
                    return int(details.split(":")[1])
        except Exception as e:  #pylint: disable=broad-except
            logging.warning(
                "[Channel] grpc_error_get_http_status except: %s, details: %s",
                repr(e), details)
        return None

    @retry_fn(retry_times=3)
    def _try_handle_request(self, func, request, resp_class):
        try:
            func_name = func._method_full_rpc_name  # pylint: disable=protected-access
            response = func(request=request, metadata=self._get_metadata())
            if response.status.code != common_pb2.STATUS_SUCCESS:
                logging.debug('%s request error: %s',
                              func_name, response.status.msg)
            return response
        except grpc.RpcError as e:
            logging.error('%s request error: %s', func_name,
                          repr(e))
            fallback_resp = resp_class(status=common_pb2.Status(
                code=common_pb2.STATUS_UNKNOWN_ERROR, msg=repr(e)))
            if self._grpc_error_need_recover(e):
                raise NeedToRetryException(ret_value=fallback_resp) from e
            return fallback_resp

    def check_connection(self):
        msg = service_pb2.CheckConnectionRequest(auth_info=self._auth_info)
        return self._try_handle_request(
            func=self._client.CheckConnection,
            request=msg,
            resp_class=service_pb2.CheckConnectionResponse).status

    def update_workflow_state(self, name, state, target_state,
                              transaction_state, uuid, forked_from_uuid):
        msg = service_pb2.UpdateWorkflowStateRequest(
            auth_info=self._auth_info,
            workflow_name=name,
            state=state.value,
            target_state=target_state.value,
            transaction_state=transaction_state.value,
            uuid=uuid,
            forked_from_uuid=forked_from_uuid)
        return self._try_handle_request(
            func=self._client.UpdateWorkflowState,
            request=msg,
            resp_class=service_pb2.UpdateWorkflowStateResponse)

    def get_workflow(self, name):
        msg = service_pb2.GetWorkflowRequest(auth_info=self._auth_info,
                                             workflow_name=name)
        return self._try_handle_request(
            func=self._client.GetWorkflow,
            request=msg,
            resp_class=service_pb2.GetWorkflowResponse)

    def update_workflow(self, name, config):
        msg = service_pb2.UpdateWorkflowRequest(auth_info=self._auth_info,
                                                workflow_name=name,
                                                config=config)
        return self._try_handle_request(
            func=self._client.UpdateWorkflow,
            request=msg,
            resp_class=service_pb2.UpdateWorkflowResponse)

    def get_job_metrics(self, job_name):
        msg = service_pb2.GetJobMetricsRequest(auth_info=self._auth_info,
                                               job_name=job_name)
        return self._try_handle_request(
            func=self._client.GetJobMetrics,
            request=msg,
            resp_class=service_pb2.GetJobMetricsResponse)

    def get_job_events(self, job_name, start_time, max_lines):
        msg = service_pb2.GetJobEventsRequest(auth_info=self._auth_info,
                                              job_name=job_name,
                                              start_time=start_time,
                                              max_lines=max_lines)
        return self._try_handle_request(
            func=self._client.GetJobEvents,
            request=msg,
            resp_class=service_pb2.GetJobEventsResponse)
