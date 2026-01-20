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
import grpc
import logging

from google.protobuf import json_format
from google.protobuf.json_format import MessageToDict
from tensorflow import make_tensor_proto
from tensorflow.core.protobuf import saved_model_pb2  # pylint: disable=no-name-in-module
from tensorflow.core.framework import graph_pb2, node_def_pb2, types_pb2  # pylint: disable=no-name-in-module
from tensorflow.core.example.example_pb2 import Example  # pylint: disable=no-name-in-module
from tensorflow.core.example.feature_pb2 import Int64List, Feature, FloatList, BytesList, Features  # pylint: disable=no-name-in-module
from tensorflow_serving.apis import (get_model_status_pb2, model_service_pb2_grpc, get_model_metadata_pb2,
                                     prediction_service_pb2_grpc, predict_pb2)
from tensorflow_serving.apis.get_model_metadata_pb2 import SignatureDefMap
from tensorflow_serving.apis.get_model_status_pb2 import ModelVersionStatus
from typing import Dict, List, Tuple, Optional
from kubernetes.client.models.v1_pod_list import V1PodList
from envs import Envs
from fedlearner_webconsole.exceptions import InternalException, ResourceConflictException, NotFoundException, \
    InvalidArgumentException
from fedlearner_webconsole.mmgr.models import Model
from fedlearner_webconsole.mmgr.service import ModelJobGroupService
from fedlearner_webconsole.participant.services import ParticipantService
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.proto import common_pb2, service_pb2, serving_pb2
from fedlearner_webconsole.proto.serving_pb2 import ServingServiceType, RemoteDeployState
from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.serving import remote
from fedlearner_webconsole.serving.database_fetcher import DatabaseFetcher
from fedlearner_webconsole.serving.metrics import serving_metrics_emit_counter
from fedlearner_webconsole.serving.utils import get_model, get_serving_negotiator_by_serving_model_id
from fedlearner_webconsole.utils import pp_datetime, flask_utils
from fedlearner_webconsole.k8s.models import Pod, PodState
from fedlearner_webconsole.db import Session
from fedlearner_webconsole.k8s.k8s_client import k8s_client
from fedlearner_webconsole.serving.models import ServingModel, ServingNegotiator, ServingModelStatus, ServingDeployment
from fedlearner_webconsole.serving.serving_yaml_template import (generate_serving_yaml, DEPLOYMENT_TEMPLATE,
                                                                 CONFIG_MAP_TEMPLATE, SERVICE_TEMPLATE)
from fedlearner_webconsole.utils.const import API_VERSION
from fedlearner_webconsole.proto.serving_pb2 import (ServingServiceInstance, ServingServiceSignature,
                                                     ServingServiceSignatureInput)
from fedlearner_webconsole.utils.sorting import SortExpression


class ServingDeploymentService:

    def __init__(self, session: Session = None):
        self._session = session

    @staticmethod
    def get_base_path(serving_model_id: int):
        # TODO(wangsen.0914): should having a serving storage filesystem. /cc @lixiaoguang.01
        return f'test/{serving_model_id}'

    def _get_serving_object_definition(self, serving_model: ServingModel) -> Tuple[Dict, Dict, Dict]:
        """get all kubernetes definition

        Returns:
            configMap, Deployment, Service
        """
        resource = json.loads(serving_model.serving_deployment.resource)
        if serving_model.model_path is not None:
            model_path = serving_model.model_path
        else:
            model_path = self.get_base_path(serving_model.id)
        serving_config = {
            'project': serving_model.project,
            'model': {
                'base_path': model_path
            },
            'serving': {
                'name': serving_model.serving_deployment.deployment_name,
                'resource': {
                    'resource': {
                        'cpu': resource['cpu'],
                        'memory': resource['memory']
                    },
                    'replicas': resource['replicas'],
                },
            }
        }
        config_map_object = generate_serving_yaml(serving_config, CONFIG_MAP_TEMPLATE, self._session)
        deployment_object = generate_serving_yaml(serving_config, DEPLOYMENT_TEMPLATE, self._session)
        service_object = generate_serving_yaml(serving_config, SERVICE_TEMPLATE, self._session)

        return config_map_object, deployment_object, service_object

    def create_or_update_deployment(self, serving_model: ServingModel):
        """post a bunch of k8s resources.

        Raises:
            Raises RuntimeError if k8s post ops failed. Then you should call `session.rollback()`.
        """
        config_map_object, deployment_object, service_object = self._get_serving_object_definition(serving_model)

        # For core api, failed to use *_app method.
        k8s_client.create_or_update_config_map(metadata=config_map_object['metadata'],
                                               data=config_map_object['data'],
                                               name=config_map_object['metadata']['name'],
                                               namespace=Envs.K8S_NAMESPACE)

        k8s_client.create_or_update_app(app_yaml=deployment_object,
                                        group='apps',
                                        version='v1',
                                        plural='deployments',
                                        namespace=Envs.K8S_NAMESPACE)

        k8s_client.create_or_update_service(metadata=service_object['metadata'],
                                            spec=service_object['spec'],
                                            name=service_object['metadata']['name'],
                                            namespace=Envs.K8S_NAMESPACE)

    def delete_deployment(self, serving_model: ServingModel):
        """delete a bunch of k8s resources.
        """
        try:
            config_map_object, deployment_object, service_object = self._get_serving_object_definition(serving_model)

            # For core api, failed to use *_app method.
            k8s_client.delete_config_map(name=config_map_object['metadata']['name'], namespace=Envs.K8S_NAMESPACE)

            k8s_client.delete_app(app_name=deployment_object['metadata']['name'],
                                  group='apps',
                                  version='v1',
                                  plural='deployments',
                                  namespace=Envs.K8S_NAMESPACE)

            k8s_client.delete_service(name=service_object['metadata']['name'], namespace=Envs.K8S_NAMESPACE)
        except RuntimeError as err:
            logging.warning(f'Failed to delete serving k8s resources, {err}')

    @staticmethod
    def get_pods_info(deployment_name: str) -> List[Pod]:
        pods: V1PodList = k8s_client.get_pods(Envs.K8S_NAMESPACE, label_selector=f'app={deployment_name}')

        pods_info = []
        for p in pods.items:
            pods_info.append(Pod.from_json(p.to_dict()))
        return pods_info

    @staticmethod
    def get_replica_status(deployment_name: str) -> str:
        config = k8s_client.get_deployment(deployment_name)
        if config is not None and config.status is not None:
            if config.status.ready_replicas is None:
                config.status.ready_replicas = 0
            return f'{config.status.ready_replicas}/{config.spec.replicas}'
        return 'UNKNOWN'

    @classmethod
    def get_pods_status(cls, deployment_name: str) -> List[ServingServiceInstance]:
        pods = cls.get_pods_info(deployment_name)
        result = []
        for pod in pods:
            instance = ServingServiceInstance(name=pod.name,
                                              cpu='UNKNOWN',
                                              memory='UNKNOWN',
                                              created_at=pod.creation_timestamp)
            if pod.state in (PodState.RUNNING, PodState.SUCCEEDED):
                instance.status = 'AVAILABLE'
            else:
                instance.status = 'UNAVAILABLE'
            result.append(instance)
        return result

    @staticmethod
    def get_pod_log(pod_name: str, tail_lines: int) -> List[str]:
        """get pod log

        Args:
            pod_name (str): pod name that you want to query
            tail_lines (int): lines you want to query

        Returns:
            List[str]: list of logs
        """
        return k8s_client.get_pod_log(pod_name, namespace=Envs.K8S_NAMESPACE, tail_lines=tail_lines)

    @staticmethod
    def generate_deployment_name(serving_model_id: int) -> str:
        hash_value = hashlib.sha256(str(pp_datetime.now()).encode('utf8'))
        return f'serving-{serving_model_id}-{hash_value.hexdigest()[0:6]}'


class TensorflowServingService:

    def __init__(self, deployment_name):
        self._deployment_name = deployment_name
        model_server_address = f'{deployment_name}.{Envs.K8S_NAMESPACE}.svc:8500'
        channel = grpc.insecure_channel(model_server_address)
        self.model_service_stub = model_service_pb2_grpc.ModelServiceStub(channel)
        self.prediction_service_stub = prediction_service_pb2_grpc.PredictionServiceStub(channel)

    def get_model_status(self) -> ModelVersionStatus.State:
        """ ref: https://github.com/tensorflow/serving/blob/master/tensorflow_serving/apis/get_model_status.proto#L26
        """
        request = get_model_status_pb2.GetModelStatusRequest()
        request.model_spec.name = self._deployment_name
        try:
            state = self.model_service_stub.GetModelStatus(request).model_version_status[0].state
        except grpc.RpcError:
            return ModelVersionStatus.State.UNKNOWN
        if state == ModelVersionStatus.State.START:
            state = ModelVersionStatus.State.LOADING
        elif state == ModelVersionStatus.State.END:
            state = ModelVersionStatus.State.UNKNOWN
        return state

    def get_model_signature(self) -> dict:
        request = get_model_metadata_pb2.GetModelMetadataRequest()
        request.model_spec.name = self._deployment_name
        request.metadata_field.append('signature_def')
        try:
            metadata = self.prediction_service_stub.GetModelMetadata(request)
        except grpc.RpcError:
            return {}
        signature = SignatureDefMap()
        metadata.metadata['signature_def'].Unpack(signature)
        return MessageToDict(signature.signature_def['serving_default'])

    def get_model_inference_output(self, user_input: Example, extend_input: Optional[dict] = None) -> dict:
        inputs = make_tensor_proto([user_input.SerializeToString()])
        request = predict_pb2.PredictRequest()
        request.model_spec.name = self._deployment_name
        request.inputs['examples'].CopyFrom(inputs)
        if extend_input is not None:
            for k in extend_input:
                ext_inputs = make_tensor_proto([extend_input[k]])
                request.inputs[k].CopyFrom(ext_inputs)
        try:
            output = self.prediction_service_stub.Predict(request)
        except grpc.RpcError as err:
            logging.error(f'Failed to inference, {err}')
            return {'Error': str(err)}
        return MessageToDict(output)

    @staticmethod
    def get_model_inference_endpoint(project_id: int, serving_model_id: int) -> str:
        return f'{API_VERSION}/projects/{project_id}/serving_services/{serving_model_id}/inference'


class NegotiatorServingService:

    def __init__(self, session: Session = None):
        self._session = session

    def _handle_participant_request_create(self, request: service_pb2.ServingServiceRequest,
                                           project: Project) -> service_pb2.ServingServiceResponse:
        response = service_pb2.ServingServiceResponse(status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS),
                                                      code=serving_pb2.SERVING_SERVICE_SUCCESS)
        # check model existence
        model = self._session.query(Model).filter_by(uuid=request.model_uuid, project_id=project.id).first()
        if model is None:
            response.status.code = common_pb2.STATUS_NOT_FOUND
            response.code = serving_pb2.SERVING_SERVICE_MODEL_NOT_FOUND
            response.msg = 'model not found'
            serving_metrics_emit_counter('serving.from_participant.create.model_not_found')
            return response
        # check serving model name
        serving_model = self._session.query(ServingModel).filter_by(name=request.serving_model_name).first()
        if serving_model is not None:
            response.status.code = common_pb2.STATUS_INVALID_ARGUMENT
            response.code = serving_pb2.SERVING_SERVICE_NAME_DUPLICATED
            response.msg = 'serving model name is duplicated'
            serving_metrics_emit_counter('serving.from_participant.create.duplicated', serving_model)
            return response
        # create db records in 3 tables
        serving_model = ServingModel()
        if model is not None:
            serving_model.model_id = model.id
            serving_model.model_path = model.get_exported_model_path()
        serving_model.name = request.serving_model_name
        serving_model.project_id = project.id
        serving_model.status = ServingModelStatus.WAITING_CONFIG
        serving_deployment = ServingDeployment()
        serving_deployment.project_id = project.id
        serving_deployment.resource = json.dumps({'cpu': '1000m', 'memory': '1Gi', 'replicas': 0})
        serving_negotiator = ServingNegotiator()
        serving_negotiator.project_id = project.id
        serving_negotiator.is_local = False
        try:
            self._session.add(serving_model)
            self._session.flush([serving_model])
        except Exception as err:
            serving_metrics_emit_counter('serving.from_participant.create.db_error', serving_model)
            raise ResourceConflictException(
                f'create serving service fail! serving model name = {serving_model.name}, err = {err}') from err
        serving_deployment.deployment_name = ServingDeploymentService.generate_deployment_name(serving_model.id)
        self._session.add(serving_deployment)
        self._session.flush([serving_deployment])
        serving_negotiator.serving_model_id = serving_model.id
        serving_negotiator.serving_model_uuid = request.serving_model_uuid
        serving_negotiator.with_label = False
        self._session.add(serving_negotiator)
        serving_model.endpoint = TensorflowServingService.get_model_inference_endpoint(project.id, serving_model.id)
        serving_model.serving_deployment_id = serving_deployment.id
        self._session.commit()
        serving_metrics_emit_counter('serving.from_participant.create.success', serving_model)
        return response

    def _handle_participant_request_query(
            self, request: service_pb2.ServingServiceRequest) -> service_pb2.ServingServiceResponse:
        response = service_pb2.ServingServiceResponse(status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS),
                                                      code=serving_pb2.SERVING_SERVICE_SUCCESS)
        # check serving model status
        serving_model = self._session.query(ServingModel).filter_by(name=request.serving_model_name).first()
        if serving_model is None:
            response.status.code = common_pb2.STATUS_NOT_FOUND
            response.code = serving_pb2.SERVING_SERVICE_MODEL_NOT_FOUND
            response.msg = f'serving model not found, name = {request.serving_model_name}'
            serving_metrics_emit_counter('serving.from_participant.query.serving_not_found')
            return response
        if serving_model.status == ServingModelStatus.WAITING_CONFIG:
            response.code = serving_pb2.SERVING_SERVICE_PENDING_ACCEPT
            response.msg = 'serving model is waiting for config'
            serving_metrics_emit_counter('serving.from_participant.query.waiting', serving_model)
            return response
        serving_metrics_emit_counter('serving.from_participant.query.success', serving_model)
        return response

    def _handle_participant_request_destroy(
            self, request: service_pb2.ServingServiceRequest) -> service_pb2.ServingServiceResponse:
        response = service_pb2.ServingServiceResponse(status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS),
                                                      code=serving_pb2.SERVING_SERVICE_SUCCESS)
        serving_negotiator = self._session.query(ServingNegotiator).filter_by(
            serving_model_uuid=request.serving_model_uuid).one_or_none()
        if serving_negotiator is None:
            response.msg = 'serving negotiator is already deleted'
            serving_metrics_emit_counter('serving.from_participant.delete.already_done')
            return response
        if serving_negotiator.serving_model.status == ServingModelStatus.WAITING_CONFIG:
            self._session.delete(serving_negotiator.serving_model.serving_deployment)
            self._session.delete(serving_negotiator.serving_model)
            self._session.delete(serving_negotiator)
            self._session.commit()
            serving_metrics_emit_counter('serving.from_participant.delete.directly', serving_negotiator.serving_model)
            return response
        serving_negotiator.serving_model.status = ServingModelStatus.DELETED
        serving_metrics_emit_counter('serving.from_participant.delete.success', serving_negotiator.serving_model)
        self._session.commit()
        return response

    @staticmethod
    def generate_uuid(serving_model_id: int) -> str:
        hash_value = hashlib.sha256(str(pp_datetime.now()).encode('utf8'))
        return f'{serving_model_id}{hash_value.hexdigest()[0:6]}'

    def operate_participant_serving_service(self, serving_negotiator: ServingNegotiator, operation: ServingServiceType):
        serving_model = self._session.query(ServingModel).filter_by(
            id=serving_negotiator.serving_model_id).one_or_none()
        # no need to notify participants when serving on third party platform
        if serving_model.serving_deployment.is_remote_serving():
            return serving_pb2.SERVING_SERVICE_SUCCESS
        service = ParticipantService(self._session)
        participants = service.get_platform_participants_by_project(serving_negotiator.project.id)
        for participant in participants:
            client = RpcClient.from_project_and_participant(serving_negotiator.project.name,
                                                            serving_negotiator.project.token, participant.domain_name)
            model_uuid = ''
            if serving_model.model is not None:
                model_uuid = '' or serving_model.model.uuid
            resp = client.operate_serving_service(operation, serving_negotiator.serving_model_uuid, model_uuid,
                                                  serving_model.name)
            if resp.status.code != common_pb2.STATUS_SUCCESS:
                msg = f'operate participant fail! status code = {resp.status.code}, msg = {resp.msg}'
                logging.error(msg)
                raise InternalException(msg)
            if operation == serving_pb2.SERVING_SERVICE_CREATE:
                if resp.code != serving_pb2.SERVING_SERVICE_SUCCESS:
                    return resp.code
            elif operation == serving_pb2.SERVING_SERVICE_QUERY:
                if resp.code != serving_pb2.SERVING_SERVICE_SUCCESS:
                    return resp.code
            else:  # SERVING_SERVICE_DESTROY
                pass
        return serving_pb2.SERVING_SERVICE_SUCCESS

    def participant_serving_service_inference(self, serving_negotiator: ServingNegotiator,
                                              example_id: str) -> service_pb2.ServingServiceInferenceResponse:
        service = ParticipantService(self._session)
        participants = service.get_platform_participants_by_project(serving_negotiator.project.id)
        assert len(participants) == 1, f'support one participant only! num = {len(participants)}'
        client = RpcClient.from_project_and_participant(serving_negotiator.project.name,
                                                        serving_negotiator.project.token, participants[0].domain_name)
        resp = client.inference_serving_service(serving_negotiator.serving_model_uuid, example_id)
        if resp.status.code != common_pb2.STATUS_SUCCESS:
            logging.error(resp.status.msg)
            raise InternalException(resp.status.msg)
        return resp

    def handle_participant_request(self, request: service_pb2.ServingServiceRequest,
                                   project: Project) -> service_pb2.ServingServiceResponse:
        if request.operation_type == ServingServiceType.SERVING_SERVICE_CREATE:
            return self._handle_participant_request_create(request, project)
        if request.operation_type == ServingServiceType.SERVING_SERVICE_QUERY:
            return self._handle_participant_request_query(request)
        if request.operation_type == ServingServiceType.SERVING_SERVICE_DESTROY:
            return self._handle_participant_request_destroy(request)
        response = service_pb2.ServingServiceResponse(status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS),
                                                      code=serving_pb2.SERVING_SERVICE_SUCCESS)
        return response

    def handle_participant_inference_request(self, request: service_pb2.ServingServiceInferenceRequest,
                                             project: Project) -> service_pb2.ServingServiceInferenceResponse:
        response = service_pb2.ServingServiceInferenceResponse(status=common_pb2.Status(code=common_pb2.STATUS_SUCCESS),
                                                               code=serving_pb2.SERVING_SERVICE_SUCCESS)
        serving_negotiator = self._session.query(ServingNegotiator).filter_by(
            serving_model_uuid=request.serving_model_uuid, project_id=project.id).one_or_none()
        if serving_negotiator is None:
            response.rpc_status.code = common_pb2.STATUS_NOT_FOUND
            response.code = serving_pb2.SERVING_SERVICE_NEGOTIATOR_NOT_FOUND
            response.msg = 'serving negotiator not found'
            return response
        deployment_name = serving_negotiator.serving_model.serving_deployment.deployment_name
        tf_serving_service = TensorflowServingService(deployment_name)
        query_key = int(request.example_id)
        data_record = DatabaseFetcher.fetch_by_int_key(query_key, serving_negotiator.serving_model.signature)
        feature_input = {}
        for k, item in data_record.items():
            if isinstance(item[0], int):
                int_list = Int64List(value=item)
                feature_input[k] = Feature(int64_list=int_list)
            if isinstance(item[0], float):
                float_list = FloatList(value=item)
                feature_input[k] = Feature(float_list=float_list)
            if isinstance(item[0], str):
                data_record_bytes = [x.encode(encoding='utf-8') for x in item]
                bytes_list = BytesList(value=data_record_bytes)
                feature_input[k] = Feature(bytes_list=bytes_list)
        input_data = Example(features=Features(feature=feature_input))
        output = tf_serving_service.get_model_inference_output(input_data)
        response.data.update({'result': output['outputs']})
        return response


class SavedModelService:
    PARSE_EXAMPLE_NAME = 'ParseExample/ParseExample'
    INPUT_NODE_NAMES = [PARSE_EXAMPLE_NAME]

    @staticmethod
    def get_nodes_from_graph(graph: graph_pb2.GraphDef, node_list: List[str]) -> Dict[str, node_def_pb2.NodeDef]:
        """get nodes from graph by node names

        Args:
            graph (graph_pb2.GraphDef): GraphDef
            node_list (List[str]): node name list

        Returns:
            Dict[str, node_def_pb2.NodeDef]: a mapping from node_name to NodeDef

        Raises:
            AssertionError: when failed to get all nodes required by node_list
        """
        result = {}
        for n in graph.node:
            if n.name in node_list:
                result[n.name] = n
        assert list(result.keys()) == node_list, f'Failed to get nodes: {node_list - result.keys()}'
        return result

    @classmethod
    def get_parse_example_details(cls, saved_model_binary: bytes) -> ServingServiceSignature:
        saved_model_message = saved_model_pb2.SavedModel()
        saved_model_message.ParseFromString(saved_model_binary)
        graph = saved_model_message.meta_graphs[0].graph_def

        parse_example_op = cls.get_nodes_from_graph(graph, cls.INPUT_NODE_NAMES)[cls.PARSE_EXAMPLE_NAME]
        assert parse_example_op.op == 'ParseExample', f'{parse_example_op} node is not a ParseExample op'

        dense_keys_inputs = [i for i in parse_example_op.input if 'dense_keys' in i]
        assert len(dense_keys_inputs) == parse_example_op.attr['Ndense'].i, 'Consistency check failed'

        dense_keys_nodes = cls.get_nodes_from_graph(graph, dense_keys_inputs)
        # Keep nodes in order
        dense_keys_list = [dense_keys_nodes[i] for i in dense_keys_inputs]
        signature = ServingServiceSignature()
        # For more details on serving/examples/parse_graph.py
        for n, t, s in zip(dense_keys_list, parse_example_op.attr['Tdense'].list.type,
                           parse_example_op.attr['dense_shapes'].list.shape):
            signature_input = ServingServiceSignatureInput(name=n.attr['value'].tensor.string_val[0],
                                                           type=types_pb2.DataType.Name(t),
                                                           dim=[d.size for d in s.dim])
            signature.inputs.append(signature_input)
        return signature


class ServingModelService(object):

    def __init__(self, session: Session = None):
        self._session = session

    def create_from_param(self,
                          project_id: int,
                          name: str,
                          is_local: bool,
                          comment: Optional[str],
                          model_id: Optional[int],
                          model_group_id: Optional[int],
                          resource: serving_pb2.ServingServiceResource = None,
                          remote_platform: serving_pb2.ServingServiceRemotePlatform = None) -> ServingModel:
        session = self._session
        serving_model = ServingModel()
        if model_id is not None:
            serving_model.model_id = model_id
            model = get_model(serving_model.model_id, self._session)
        elif model_group_id is not None:
            serving_model.model_group_id = model_group_id
            model = ModelJobGroupService(self._session).get_latest_model_from_model_group(serving_model.model_group_id)
            serving_model.model_id = model.id
        else:
            raise InvalidArgumentException('model_id and model_group_id need to fill one')
        serving_model.name = name
        serving_model.project_id = project_id
        serving_model.comment = comment
        serving_model.status = ServingModelStatus.LOADING
        serving_model.model_path = model.get_exported_model_path()

        try:
            session.add(serving_model)
            session.flush([serving_model])
        except Exception as err:
            serving_metrics_emit_counter('serving.create.db_fail', serving_model)
            raise ResourceConflictException(
                f'create serving service fail! serving model name = {serving_model.name}, err = {err}') from err

        serving_deployment = ServingDeployment()
        serving_deployment.project_id = project_id
        session.add(serving_deployment)
        session.flush([serving_deployment])
        serving_model.serving_deployment_id = serving_deployment.id

        serving_negotiator = ServingNegotiator()
        serving_negotiator.project_id = project_id
        serving_negotiator.is_local = is_local

        if remote_platform is None:  # serving inside this platform
            serving_deployment.resource = json.dumps(MessageToDict(resource))
            serving_deployment.deployment_name = ServingDeploymentService.generate_deployment_name(serving_model.id)
            serving_model.endpoint = TensorflowServingService.get_model_inference_endpoint(project_id, serving_model.id)
            self._create_or_update_deployment(serving_model)
        else:  # remote serving
            deploy_config: serving_pb2.RemoteDeployConfig = self._create_remote_serving(remote_platform, serving_model)
            serving_deployment.deploy_platform = json.dumps(MessageToDict(deploy_config))
            serving_model.endpoint = self._get_remote_serving_url(remote_platform)

        # Notifying participants needs to be placed behind the k8s operation,
        # because when the k8s operation fails, it avoids the participants from generating dirty data
        serving_negotiator.serving_model_id = serving_model.id
        serving_negotiator.serving_model_uuid = NegotiatorServingService.generate_uuid(serving_model.id)
        serving_negotiator.with_label = True
        session.add(serving_negotiator)
        session.flush([serving_negotiator])
        if not serving_negotiator.is_local:
            serving_model.status = ServingModelStatus.PENDING_ACCEPT
            result = NegotiatorServingService(session).operate_participant_serving_service(
                serving_negotiator, serving_pb2.SERVING_SERVICE_CREATE)
            if result != serving_pb2.SERVING_SERVICE_SUCCESS:
                raise InternalException(details=f'create participant serving service fail! result code = {result}')
        return serving_model

    def get_serving_service_detail(self,
                                   serving_model_id: int,
                                   project_id: Optional[int] = None,
                                   sorter: Optional[SortExpression] = None) -> serving_pb2.ServingServiceDetail:
        serving_model = self._session.query(ServingModel).filter_by(id=serving_model_id).one_or_none()
        if not serving_model:
            raise NotFoundException(f'Failed to find serving model {serving_model_id}')
        if project_id is not None:
            if serving_model.project_id != project_id:
                raise NotFoundException(f'Failed to find serving model {serving_model_id} in project {project_id}')
        deployment_name = serving_model.serving_deployment.deployment_name
        result = serving_model.to_serving_service_detail()
        if serving_model.serving_deployment.is_remote_serving():
            result.status = self._get_remote_serving_status(serving_model).name
            result.support_inference = (result.status == ServingModelStatus.AVAILABLE.name)
        else:
            status = TensorflowServingService(deployment_name).get_model_status()
            if serving_model.status == ServingModelStatus.LOADING and status != ModelVersionStatus.State.UNKNOWN:
                result.status = ModelVersionStatus.State.Name(status)
                result.support_inference = (result.status == ServingModelStatus.AVAILABLE.name)
            resource = json.loads(serving_model.serving_deployment.resource)
            resource = serving_pb2.ServingServiceResource(
                cpu=resource['cpu'],
                memory=resource['memory'],
                replicas=resource['replicas'],
            )
            result.resource.CopyFrom(resource)
        if result.resource.replicas > 0:
            k8s_serving_service = ServingDeploymentService()
            result.instance_num_status = k8s_serving_service.get_replica_status(deployment_name)
            instances = k8s_serving_service.get_pods_status(deployment_name)
            if sorter is not None:
                if sorter.field == 'created_at':
                    reverse = not sorter.is_asc
                    instances = sorted(instances, key=lambda x: x.created_at, reverse=reverse)
            result.instances.extend(instances)
        else:
            result.instance_num_status = 'UNKNOWN'
        serving_negotiator = get_serving_negotiator_by_serving_model_id(serving_model_id, self._session)
        if serving_negotiator is not None:
            result.is_local = serving_negotiator.is_local
            if not serving_negotiator.with_label:
                result.support_inference = False
        return result

    def set_resource_and_status_on_ref(self, single_res: serving_pb2.ServingService, serving_model: ServingModel):
        if serving_model.serving_deployment.is_remote_serving():
            single_res.status = self._get_remote_serving_status(serving_model).name
            single_res.support_inference = (single_res.status == ServingModelStatus.AVAILABLE.name)
            return
        deployment_name = serving_model.serving_deployment.deployment_name
        resource = json.loads(serving_model.serving_deployment.resource)
        tf_serving_service = TensorflowServingService(deployment_name)
        status = tf_serving_service.get_model_status()
        if serving_model.status == ServingModelStatus.LOADING and status != ModelVersionStatus.State.UNKNOWN:
            single_res.status = ModelVersionStatus.State.Name(status)
            single_res.support_inference = (single_res.status == ServingModelStatus.AVAILABLE.name)
        if resource['replicas'] > 0:
            single_res.instance_num_status = ServingDeploymentService.get_replica_status(deployment_name)
        else:
            single_res.instance_num_status = 'UNKNOWN'
        single_res.resource.cpu = resource['cpu']
        single_res.resource.memory = resource['memory']
        single_res.resource.replicas = resource['replicas']

    def set_is_local_on_ref(self, single_res: serving_pb2.ServingService, serving_model: ServingModel):
        serving_negotiator = self._session.query(ServingNegotiator).filter_by(
            serving_model_id=serving_model.id).one_or_none()
        if serving_negotiator is not None:
            single_res.is_local = serving_negotiator.is_local
            if not serving_negotiator.with_label:
                single_res.support_inference = False

    def update_model(self, model_id: Optional[int], model_group_id: Optional[int], serving_model: ServingModel) -> bool:
        need_update = False
        if model_id is not None:
            if model_id != serving_model.model_id:
                model = get_model(model_id, self._session)
                serving_model.model_id = model.id
                serving_model.model_path = model.get_exported_model_path()
                need_update = True
            serving_model.model_group_id = None  # clear model group config
        elif model_group_id is not None and model_group_id != serving_model.model_group_id:
            model = ModelJobGroupService(self._session).get_latest_model_from_model_group(model_group_id)
            if serving_model.model_id != model.id:
                serving_model.model_id = model.id
                serving_model.model_path = model.get_exported_model_path()
                need_update = True
            serving_model.model_group_id = model_group_id

        if not need_update:
            return False

        if serving_model.serving_deployment.is_remote_serving():
            self.update_remote_serving_model(serving_model)
            return True

        serving_negotiator = self._session.query(ServingNegotiator).filter_by(
            serving_model_id=serving_model.id).one_or_none()
        if serving_negotiator is not None and not serving_negotiator.is_local:
            # TODO(lixiaoguang.01) support update model for federal serving
            raise InvalidArgumentException('update model is not supported for federal serving')

        self._create_or_update_deployment(serving_model)
        return True

    def update_resource(self, resource: dict, serving_model: ServingModel):
        serving_model.serving_deployment.resource = json.dumps(resource)
        serving_model.status = ServingModelStatus.LOADING
        self._create_or_update_deployment(serving_model)
        self._session.add(serving_model.serving_deployment)

    def delete_serving_service(self, serving_model: ServingModel):
        serving_negotiator = self._session.query(ServingNegotiator).filter_by(
            serving_model_id=serving_model.id).one_or_none()
        if serving_negotiator is not None:
            if not serving_negotiator.is_local:
                NegotiatorServingService(self._session).operate_participant_serving_service(
                    serving_negotiator, serving_pb2.ServingServiceType.SERVING_SERVICE_DESTROY)
            self._session.delete(serving_negotiator)
        if serving_model.serving_deployment.is_remote_serving():
            self._undeploy_remote_serving(serving_model)
        else:
            try:
                ServingDeploymentService(self._session).delete_deployment(serving_model)
            except RuntimeError as err:
                serving_metrics_emit_counter('serving.delete.deployment_error', serving_model)
                raise ResourceConflictException(
                    f'delete deployment fail! serving model id = {serving_model.id}, err = {err}') from err
        self._session.delete(serving_model.serving_deployment)
        self._session.delete(serving_model)

    def _create_or_update_deployment(self, serving_model: ServingModel):
        try:
            ServingDeploymentService(self._session).create_or_update_deployment(serving_model)
        except RuntimeError as err:
            serving_metrics_emit_counter('serving.deployment_error', serving_model)
            raise InternalException(
                f'create or update deployment fail! serving model id = {serving_model.id}, err = {err}') from err

    @staticmethod
    def _create_remote_serving(remote_platform: serving_pb2.ServingServiceRemotePlatform,
                               serving_model: ServingModel) -> serving_pb2.RemoteDeployConfig:
        current_user = flask_utils.get_current_user()
        if remote_platform.platform not in remote.supported_remote_serving:
            raise InvalidArgumentException(f'platform {remote_platform.platform} not supported')
        deploy_config = serving_pb2.RemoteDeployConfig(platform=remote_platform.platform,
                                                       payload=remote_platform.payload,
                                                       deploy_name=f'privacy-platform-{serving_model.name}',
                                                       model_src_path=serving_model.model_path)
        remote_helper = remote.supported_remote_serving[remote_platform.platform]
        try:
            deploy_config.deploy_id = remote_helper.deploy_model(current_user.username, deploy_config)
        except (FileNotFoundError, AttributeError) as err:
            serving_metrics_emit_counter('serving.remote_deployment_error', serving_model)
            raise InvalidArgumentException(
                f'create remote deployment fail! serving model id = {serving_model.id}, err = {err}') from err
        # not stored in db, fetch from serving_model when deploy
        deploy_config.model_src_path = ''
        return deploy_config

    def update_remote_serving_model(self, serving_model: ServingModel):
        current_user = flask_utils.get_current_user()
        if current_user is None:
            username = 'robot'
        else:
            username = current_user.username
        deploy_config = serving_pb2.RemoteDeployConfig()
        json_format.Parse(serving_model.serving_deployment.deploy_platform, deploy_config)
        if deploy_config.platform not in remote.supported_remote_serving:
            raise InvalidArgumentException(f'platform {deploy_config.platform} not supported')
        deploy_config.model_src_path = serving_model.model_path
        remote_helper = remote.supported_remote_serving[deploy_config.platform]
        remote_helper.deploy_model(username, deploy_config)

    @staticmethod
    def _get_remote_serving_url(remote_platform: serving_pb2.ServingServiceRemotePlatform) -> str:
        if remote_platform.platform not in remote.supported_remote_serving:
            raise InvalidArgumentException(f'platform {remote_platform.platform} not supported')
        deploy_config = serving_pb2.RemoteDeployConfig(payload=remote_platform.payload)
        remote_helper = remote.supported_remote_serving[remote_platform.platform]
        return remote_helper.get_deploy_url(deploy_config)

    @staticmethod
    def _get_remote_serving_status(serving_model: ServingModel) -> ServingModelStatus:
        deploy_config = serving_pb2.RemoteDeployConfig()
        json_format.Parse(serving_model.serving_deployment.deploy_platform, deploy_config)
        if deploy_config.platform not in remote.supported_remote_serving:
            raise InvalidArgumentException(f'platform {deploy_config.platform} not supported')
        remote_helper = remote.supported_remote_serving[deploy_config.platform]
        deploy_status = remote_helper.get_deploy_status(deploy_config)
        if deploy_status == RemoteDeployState.REMOTE_DEPLOY_READY:
            return ServingModelStatus.AVAILABLE
        return ServingModelStatus.LOADING

    @staticmethod
    def _undeploy_remote_serving(serving_model: ServingModel):
        deploy_config = serving_pb2.RemoteDeployConfig()
        json_format.Parse(serving_model.serving_deployment.deploy_platform, deploy_config)
        if deploy_config.platform not in remote.supported_remote_serving:
            raise InvalidArgumentException(f'platform {deploy_config.platform} not supported')
        remote_helper = remote.supported_remote_serving[deploy_config.platform]
        remote_helper.undeploy_model(deploy_config)
