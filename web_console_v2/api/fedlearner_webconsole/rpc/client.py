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
# pylint: disable=broad-except

import logging
from functools import wraps
from typing import Optional

import grpc
from google.protobuf import empty_pb2

from envs import Envs
from fedlearner_webconsole.utils.decorators.lru_cache import lru_cache
from fedlearner_webconsole.utils.decorators.retry import retry_fn
from fedlearner_webconsole.exceptions import (UnauthorizedException, InvalidArgumentException)
from fedlearner_webconsole.proto import (dataset_pb2, service_pb2, service_pb2_grpc, common_pb2)
from fedlearner_webconsole.proto.service_pb2_grpc import WebConsoleV2ServiceStub
from fedlearner_webconsole.proto.serving_pb2 import ServingServiceType
from fedlearner_webconsole.proto.two_pc_pb2 import TwoPcType, TwoPcAction, TransactionData
from fedlearner_webconsole.proto.workflow_definition_pb2 import WorkflowDefinition
from fedlearner_webconsole.rpc.client_interceptor import ClientInterceptor
from fedlearner_webconsole.rpc.v2.client_base import get_nginx_controller_url


@lru_cache(timeout=60, maxsize=100)
def _build_grpc_stub(egress_url: str, authority: str) -> WebConsoleV2ServiceStub:
    """A helper function to build gRPC stub with cache.

    Notice that as we cache the stub, if nginx controller gets restarted, the channel may break.
    This practice is following official best practice: https://grpc.io/docs/guides/performance/

    Args:
        egress_url: nginx controller url in current cluster.
        authority: ingress domain in current cluster.

    Returns:
        A grpc service stub to call API.
    """
    channel = grpc.insecure_channel(
        target=egress_url,
        # options defined at
        # https://github.com/grpc/grpc/blob/master/include/grpc/impl/codegen/grpc_types.h
        options=[('grpc.default_authority', authority)])
    channel = grpc.intercept_channel(channel, ClientInterceptor())
    return service_pb2_grpc.WebConsoleV2ServiceStub(channel)


# TODO(linfan.fine): refactor catch_and_fallback
def catch_and_fallback(resp_class):

    def decorator(f):

        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except grpc.RpcError as e:
                return resp_class(status=common_pb2.Status(code=common_pb2.STATUS_UNKNOWN_ERROR, msg=repr(e)))

        return wrapper

    return decorator


def _need_retry_for_get(err: Exception) -> bool:
    if not isinstance(err, grpc.RpcError):
        return False
    # No need to retry for NOT_FOUND
    return err.code() != grpc.StatusCode.NOT_FOUND


def _default_need_retry(err: Exception) -> bool:
    return isinstance(err, grpc.RpcError)


class RpcClient(object):

    def __init__(self,
                 egress_url: str,
                 authority: str,
                 x_host: str,
                 project_auth_info: Optional[service_pb2.ProjAuthInfo] = None):
        """Inits rpc client.

        Args:
            egress_url: nginx controller url in current cluster.
            authority: ingress domain in current cluster.
            x_host: ingress domain in target cluster, nginx will handle the
                rewriting.
            project_auth_info: info for project level authentication.
        """
        self._x_host = x_host
        self._project_auth_info = project_auth_info

        self._client = _build_grpc_stub(egress_url, authority)

    @classmethod
    def from_project_and_participant(cls, project_name: str, project_token: str, domain_name: str):
        # Builds auth info from project and receiver
        auth_info = service_pb2.ProjAuthInfo(project_name=project_name,
                                             target_domain=domain_name,
                                             auth_token=project_token)
        return cls(egress_url=get_nginx_controller_url(),
                   authority=gen_egress_authority(domain_name),
                   x_host=gen_x_host(domain_name),
                   project_auth_info=auth_info)

    @classmethod
    def from_participant(cls, domain_name: str):
        return cls(egress_url=get_nginx_controller_url(),
                   authority=gen_egress_authority(domain_name),
                   x_host=gen_x_host(domain_name))

    def _get_metadata(self):
        # metadata is a tuple of tuples
        return tuple([('x-host', self._x_host)])

    @catch_and_fallback(resp_class=service_pb2.CheckConnectionResponse)
    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def check_connection(self):
        msg = service_pb2.CheckConnectionRequest(auth_info=self._project_auth_info)
        response = self._client.CheckConnection(request=msg,
                                                metadata=self._get_metadata(),
                                                timeout=Envs.GRPC_CLIENT_TIMEOUT)
        if response.status.code != common_pb2.STATUS_SUCCESS:
            logging.debug('check_connection request error: %s', response.status.msg)
        return response

    @catch_and_fallback(resp_class=service_pb2.CheckPeerConnectionResponse)
    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def check_peer_connection(self):
        # TODO(taoyanting): double check
        msg = service_pb2.CheckPeerConnectionRequest()
        response = self._client.CheckPeerConnection(request=msg,
                                                    metadata=self._get_metadata(),
                                                    timeout=Envs.GRPC_CLIENT_TIMEOUT)
        if response.status.code != common_pb2.STATUS_SUCCESS:
            logging.debug('check_connection request error: %s', response.status.msg)
        return response

    @catch_and_fallback(resp_class=service_pb2.UpdateWorkflowStateResponse)
    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def update_workflow_state(self, name, state, target_state, transaction_state, uuid, forked_from_uuid, extra=''):
        msg = service_pb2.UpdateWorkflowStateRequest(auth_info=self._project_auth_info,
                                                     workflow_name=name,
                                                     state=state.value,
                                                     target_state=target_state.value,
                                                     transaction_state=transaction_state.value,
                                                     uuid=uuid,
                                                     forked_from_uuid=forked_from_uuid,
                                                     extra=extra)
        response = self._client.UpdateWorkflowState(request=msg,
                                                    metadata=self._get_metadata(),
                                                    timeout=Envs.GRPC_CLIENT_TIMEOUT)
        if response.status.code != common_pb2.STATUS_SUCCESS:
            logging.debug('update_workflow_state request error: %s', response.status.msg)
        return response

    @catch_and_fallback(resp_class=service_pb2.GetWorkflowResponse)
    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def get_workflow(self, uuid, name):
        msg = service_pb2.GetWorkflowRequest(auth_info=self._project_auth_info, workflow_name=name, workflow_uuid=uuid)
        response = self._client.GetWorkflow(request=msg,
                                            metadata=self._get_metadata(),
                                            timeout=Envs.GRPC_CLIENT_TIMEOUT)

        if response.status.code != common_pb2.STATUS_SUCCESS:
            logging.debug('get_workflow request error: %s', response.status.msg)
        return response

    @catch_and_fallback(resp_class=service_pb2.UpdateWorkflowResponse)
    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def update_workflow(self, uuid, name, config):
        msg = service_pb2.UpdateWorkflowRequest(auth_info=self._project_auth_info,
                                                workflow_name=name,
                                                workflow_uuid=uuid,
                                                config=config)
        response = self._client.UpdateWorkflow(request=msg,
                                               metadata=self._get_metadata(),
                                               timeout=Envs.GRPC_CLIENT_TIMEOUT)

        if response.status.code != common_pb2.STATUS_SUCCESS:
            logging.debug('update_workflow request error: %s', response.status.msg)
        return response

    @catch_and_fallback(resp_class=service_pb2.InvalidateWorkflowResponse)
    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def invalidate_workflow(self, uuid: str):
        msg = service_pb2.InvalidateWorkflowRequest(auth_info=self._project_auth_info, workflow_uuid=uuid)
        response = self._client.InvalidateWorkflow(request=msg,
                                                   metadata=self._get_metadata(),
                                                   timeout=Envs.GRPC_CLIENT_TIMEOUT)
        if response.status.code != common_pb2.STATUS_SUCCESS:
            logging.debug('invalidate_workflow request error: %s', response.status.msg)
        return response

    @catch_and_fallback(resp_class=service_pb2.GetJobMetricsResponse)
    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def get_job_metrics(self, job_name):
        msg = service_pb2.GetJobMetricsRequest(auth_info=self._project_auth_info, job_name=job_name)
        response = self._client.GetJobMetrics(request=msg,
                                              metadata=self._get_metadata(),
                                              timeout=Envs.GRPC_CLIENT_TIMEOUT)

        if response.status.code != common_pb2.STATUS_SUCCESS:
            logging.debug('get_job_metrics request error: %s', response.status.msg)
        return response

    @catch_and_fallback(resp_class=service_pb2.GetJobMetricsResponse)
    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def get_job_kibana(self, job_name, json_args):
        msg = service_pb2.GetJobKibanaRequest(auth_info=self._project_auth_info, job_name=job_name, json_args=json_args)
        response = self._client.GetJobKibana(request=msg,
                                             metadata=self._get_metadata(),
                                             timeout=Envs.GRPC_CLIENT_TIMEOUT)
        status = response.status
        if status.code != common_pb2.STATUS_SUCCESS:
            if status.code == common_pb2.STATUS_UNAUTHORIZED:
                raise UnauthorizedException(status.msg)
            if status.code == common_pb2.STATUS_INVALID_ARGUMENT:
                raise InvalidArgumentException(status.msg)
            logging.debug('get_job_kibana request error: %s', response.status.msg)
        return response

    @catch_and_fallback(resp_class=service_pb2.GetJobEventsResponse)
    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def get_job_events(self, job_name, start_time, max_lines):
        msg = service_pb2.GetJobEventsRequest(auth_info=self._project_auth_info,
                                              job_name=job_name,
                                              start_time=start_time,
                                              max_lines=max_lines)
        response = self._client.GetJobEvents(request=msg,
                                             metadata=self._get_metadata(),
                                             timeout=Envs.GRPC_CLIENT_TIMEOUT)

        if response.status.code != common_pb2.STATUS_SUCCESS:
            logging.debug('get_job_events request error: %s', response.status.msg)
        return response

    @catch_and_fallback(resp_class=service_pb2.CheckJobReadyResponse)
    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def check_job_ready(self, job_name: str) \
            -> service_pb2.CheckJobReadyResponse:
        msg = service_pb2.CheckJobReadyRequest(auth_info=self._project_auth_info, job_name=job_name)
        response = self._client.CheckJobReady(request=msg,
                                              timeout=Envs.GRPC_CLIENT_TIMEOUT,
                                              metadata=self._get_metadata())

        if response.status.code != common_pb2.STATUS_SUCCESS:
            logging.debug('check_job_ready request error: %s', response.status.msg)
        return response

    @catch_and_fallback(resp_class=service_pb2.TwoPcResponse)
    @retry_fn(retry_times=3, need_retry=_default_need_retry, delay=200, backoff=2)
    def run_two_pc(self, transaction_uuid: str, two_pc_type: TwoPcType, action: TwoPcAction,
                   data: TransactionData) -> service_pb2.TwoPcResponse:
        msg = service_pb2.TwoPcRequest(auth_info=self._project_auth_info,
                                       transaction_uuid=transaction_uuid,
                                       type=two_pc_type,
                                       action=action,
                                       data=data)
        response = self._client.Run2Pc(request=msg, metadata=self._get_metadata(), timeout=Envs.GRPC_CLIENT_TIMEOUT)
        return response

    @catch_and_fallback(resp_class=service_pb2.ServingServiceResponse)
    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def operate_serving_service(self, operation_type: ServingServiceType, serving_model_uuid: str, model_uuid: str,
                                name: str):
        msg = service_pb2.ServingServiceRequest(auth_info=self._project_auth_info,
                                                operation_type=operation_type,
                                                serving_model_uuid=serving_model_uuid,
                                                model_uuid=model_uuid,
                                                serving_model_name=name)
        response = self._client.ServingServiceManagement(request=msg,
                                                         metadata=self._get_metadata(),
                                                         timeout=Envs.GRPC_CLIENT_TIMEOUT)

        if response.status.code != common_pb2.STATUS_SUCCESS:
            logging.debug('serving_service request error: %s', response.status.msg)
        return response

    @catch_and_fallback(resp_class=service_pb2.ServingServiceInferenceResponse)
    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def inference_serving_service(self, serving_model_uuid: str, example_id: str):
        msg = service_pb2.ServingServiceInferenceRequest(auth_info=self._project_auth_info,
                                                         serving_model_uuid=serving_model_uuid,
                                                         example_id=example_id)
        response = self._client.ServingServiceInference(request=msg,
                                                        metadata=self._get_metadata(),
                                                        timeout=Envs.GRPC_CLIENT_TIMEOUT)

        if response.status.code != common_pb2.STATUS_SUCCESS:
            logging.debug('serving_service request error: %s', response.status.msg)
        return response

    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def get_model_job(self, model_job_uuid: str, need_metrics: bool = False) -> service_pb2.GetModelJobResponse:
        request = service_pb2.GetModelJobRequest(auth_info=self._project_auth_info,
                                                 uuid=model_job_uuid,
                                                 need_metrics=need_metrics)
        return self._client.GetModelJob(request, metadata=self._get_metadata(), timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def get_model_job_group(self, model_job_group_uuid: str) -> service_pb2.GetModelJobGroupResponse:
        request = service_pb2.GetModelJobGroupRequest(auth_info=self._project_auth_info, uuid=model_job_group_uuid)
        return self._client.GetModelJobGroup(request, metadata=self._get_metadata(), timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def update_model_job_group(self, model_job_group_uuid: str,
                               config: WorkflowDefinition) -> service_pb2.UpdateModelJobGroupResponse:
        request = service_pb2.UpdateModelJobGroupRequest(auth_info=self._project_auth_info,
                                                         uuid=model_job_group_uuid,
                                                         config=config)
        return self._client.UpdateModelJobGroup(request,
                                                metadata=self._get_metadata(),
                                                timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def list_participant_datasets(self,
                                  kind: Optional[str] = None,
                                  uuid: Optional[str] = None) -> service_pb2.ListParticipantDatasetsResponse:
        request = service_pb2.ListParticipantDatasetsRequest(auth_info=self._project_auth_info)
        if kind is not None:
            request.kind = kind
        if uuid is not None:
            request.uuid = uuid
        return self._client.ListParticipantDatasets(request,
                                                    metadata=self._get_metadata(),
                                                    timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_need_retry_for_get)
    def get_dataset_job(self, uuid: str) -> service_pb2.GetDatasetJobResponse:
        request = service_pb2.GetDatasetJobRequest(auth_info=self._project_auth_info, uuid=uuid)
        return self._client.GetDatasetJob(request, metadata=self._get_metadata(), timeout=Envs.GRPC_CLIENT_TIMEOUT)

    @retry_fn(retry_times=3, need_retry=_default_need_retry)
    def create_dataset_job(self, dataset_job: dataset_pb2.DatasetJob, ticket_uuid: str,
                           dataset: dataset_pb2.Dataset) -> empty_pb2.Empty:
        request = service_pb2.CreateDatasetJobRequest(auth_info=self._project_auth_info,
                                                      dataset_job=dataset_job,
                                                      ticket_uuid=ticket_uuid,
                                                      dataset=dataset)
        return self._client.CreateDatasetJob(request, metadata=self._get_metadata(), timeout=Envs.GRPC_CLIENT_TIMEOUT)


def gen_egress_authority(domain_name: str) -> str:
    """generate egress host
    Args:
        domain_name:
            ex: 'test-1.com'
    Returns:
        authority:
            ex:'test-1-client-auth.com'
    """
    domain_name_prefix = domain_name.rpartition('.')[0]
    return f'{domain_name_prefix}-client-auth.com'


def gen_x_host(domain_name: str) -> str:
    """generate x host
        Args:
            domain_name:
                ex: 'test-1.com'
        Returns:
            x-host:
                ex:'fedlearner-webconsole-v2.test-1.com'
    """
    return f'fedlearner-webconsole-v2.{domain_name}'
