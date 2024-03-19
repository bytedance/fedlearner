# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
import logging
from abc import ABCMeta, abstractmethod
from datetime import datetime, timezone
from enum import Enum, unique
from typing import Optional, List, Dict, NamedTuple
from google.protobuf.json_format import ParseDict
from kubernetes.client import V1ObjectMeta
from fedlearner_webconsole.proto.job_pb2 import PodPb
from fedlearner_webconsole.proto.k8s_pb2 import Condition
from fedlearner_webconsole.utils.pp_datetime import to_timestamp


class PodMessage(NamedTuple):
    summary: Optional[str]
    details: str


@unique
class PodState(Enum):
    UNKNOWN = 'UNKNOWN'
    RUNNING = 'RUNNING'
    SUCCEEDED = 'SUCCEEDED'
    # Succeeded and resource released
    SUCCEEDED_AND_FREED = 'SUCCEEDED_AND_FREED'
    FAILED = 'FAILED'
    # Failed and resource released
    FAILED_AND_FREED = 'FAILED_AND_FREED'
    PENDING = 'PENDING'

    @staticmethod
    def from_value(value: str) -> 'PodState':
        try:
            if isinstance(value, str):
                value = value.upper()
            return PodState(value)
        except ValueError:
            logging.error(f'Unexpected value of PodState: {value}')
            return PodState.UNKNOWN


class CrdKind(Enum):
    FLAPP = 'FLApp'
    SPARKAPPLICATION = 'SparkApplication'
    FEDAPP = 'FedApp'
    UNKNOWN = 'Unknown'

    @staticmethod
    def from_value(value: str) -> 'CrdKind':
        try:
            return CrdKind(value)
        except ValueError:
            return CrdKind.UNKNOWN


class MessageProvider(metaclass=ABCMeta):

    @abstractmethod
    def get_message(self, private: bool = False) -> Optional[str]:
        pass


class ContainerState(MessageProvider):

    def __init__(self, state: str, message: Optional[str] = None, reason: Optional[str] = None):
        self.state = state
        self.message = message
        self.reason = reason

    def get_message(self, private: bool = False) -> Optional[str]:
        if private:
            if self.message is not None:
                return f'{self.state}:{self.message}'
        if self.reason is not None:
            return f'{self.state}:{self.reason}'
        return None

    def __eq__(self, other):
        if not isinstance(other, ContainerState):
            return False
        return self.state == other.state and \
               self.message == other.message and \
               self.reason == other.reason


class PodCondition(MessageProvider):

    def __init__(self, cond_type: str, message: Optional[str] = None, reason: Optional[str] = None):
        self.cond_type = cond_type
        self.message = message
        self.reason = reason

    def get_message(self, private: bool = False) -> Optional[str]:
        if private:
            if self.message is not None:
                return f'{self.cond_type}:{self.message}'
        if self.reason is not None:
            return f'{self.cond_type}:{self.reason}'
        return None

    def __eq__(self, other):
        if not isinstance(other, PodCondition):
            return False
        return self.cond_type == other.cond_type and \
               self.message == other.message and \
               self.reason == other.reason


class Pod(object):

    def __init__(self,
                 name: str,
                 state: PodState,
                 pod_type: str = 'UNKNOWN',
                 pod_ip: str = None,
                 container_states: List[ContainerState] = None,
                 pod_conditions: List[PodCondition] = None,
                 creation_timestamp: int = None,
                 status_message: str = None):
        self.name = name
        self.state = state or PodState.UNKNOWN
        self.pod_type = pod_type
        self.pod_ip = pod_ip
        self.container_states = container_states or []
        self.pod_conditions = pod_conditions or []
        self.creation_timestamp = creation_timestamp or 0
        self.status_message = status_message or ''

    def __eq__(self, other):
        if not isinstance(other, Pod):
            return False
        if len(self.container_states) != len(other.container_states):
            return False
        for index, state in enumerate(self.container_states):
            if state != other.container_states[index]:
                return False
        if len(self.pod_conditions or []) != len(self.pod_conditions or []):
            return False
        for index, cond in enumerate(self.pod_conditions):
            if cond != other.pod_conditions[index]:
                return False
        return self.name == other.name and \
               self.state == other.state and \
               self.pod_type == other.pod_type and \
               self.pod_ip == other.pod_ip and \
               self.creation_timestamp == self.creation_timestamp

    def to_proto(self, include_private_info: bool = False) -> PodPb:

        return PodPb(name=self.name,
                     pod_type=self.pod_type,
                     state=self.state.name,
                     pod_ip=self.pod_ip,
                     creation_timestamp=self.creation_timestamp,
                     message=self.get_message(include_private_info).details)

    def get_message(self, include_private_info: bool = False) -> PodMessage:
        summary = None
        messages = [self.status_message] if self.status_message else []
        for container_state in self.container_states:
            message = container_state.get_message(include_private_info)
            if message is not None:
                messages.append(message)
            if container_state.state == 'terminated':
                summary = message
        for pod_condition in self.pod_conditions:
            message = pod_condition.get_message(include_private_info)
            if message is not None:
                messages.append(message)
        return PodMessage(summary=summary, details=', '.join(messages))

    @classmethod
    def from_json(cls, p: dict) -> 'Pod':
        """Extracts information from original K8S pod info.

        Schema ref: https://github.com/garethr/kubernetes-json-schema/blob/
        master/v1.6.5-standalone/pod.json"""
        container_states: List[ContainerState] = []
        pod_conditions: List[PodCondition] = []
        if 'container_statuses' in p['status'] and \
                isinstance(p['status']['container_statuses'], list) and \
                len(p['status']['container_statuses']) > 0:
            for state, detail in \
                    p['status']['container_statuses'][0]['state'].items():
                # detail may be None, so add a conditional judgement('and')
                # short-circuit operation
                container_states.append(
                    ContainerState(state=state,
                                   message=detail and detail.get('message'),
                                   reason=detail and detail.get('reason')))
        if 'conditions' in p['status'] and \
                isinstance(p['status']['conditions'], list):
            for cond in p['status']['conditions']:
                pod_conditions.append(
                    PodCondition(cond_type=cond['type'], message=cond.get('message'), reason=cond.get('reason')))

        return cls(name=p['metadata']['name'],
                   pod_type=get_pod_type(p),
                   state=PodState.from_value(p['status']['phase']),
                   pod_ip=p['status'].get('pod_ip'),
                   container_states=container_states,
                   pod_conditions=pod_conditions,
                   creation_timestamp=to_timestamp(p['metadata']['creation_timestamp']),
                   status_message=p['status'].get('message'))


def get_pod_type(pod: dict) -> str:
    labels = pod['metadata']['labels']
    # SparkApplication -> pod.metadata.labels.spark-role
    # FlApp -> pod.metadata.labels.fl-replica-type
    pod_type = labels.get('fl-replica-type', None) or labels.get('spark-role', 'UNKNOWN')
    return pod_type.upper()


def get_creation_timestamp_from_k8s_app(app: dict) -> int:
    if 'metadata' in app and 'creationTimestamp' in app['metadata']:
        return to_timestamp(app['metadata']['creationTimestamp'])
    return 0


class K8sApp(metaclass=ABCMeta):

    @classmethod
    @abstractmethod
    def from_json(cls, app_detail: dict):
        pass

    @property
    @abstractmethod
    def is_completed(self) -> bool:
        pass

    @property
    @abstractmethod
    def is_failed(self) -> bool:
        pass

    @property
    @abstractmethod
    def completed_at(self) -> int:
        pass

    @property
    @abstractmethod
    def pods(self) -> List[Pod]:
        pass

    @property
    @abstractmethod
    def error_message(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def creation_timestamp(self) -> int:
        pass


# Please keep the value consistent with operator's definition
@unique
class FlAppState(Enum):
    UNKNOWN = 'Unknown'
    NEW = 'FLStateNew'
    BOOTSTRAPPED = 'FLStateBootstrapped'
    SYNC_SENT = 'FLStateSyncSent'
    RUNNING = 'FLStateRunning'
    COMPLETED = 'FLStateComplete'
    FAILING = 'FLStateFailing'
    SHUTDOWN = 'FLStateShutDown'
    FAILED = 'FLStateFailed'

    @staticmethod
    def from_value(value: str) -> 'FlAppState':
        try:
            return FlAppState(value)
        except ValueError:
            logging.error(f'Unexpected value of FlAppState: {value}')
            return FlAppState.UNKNOWN


class FlApp(K8sApp):

    def __init__(self,
                 state: FlAppState = FlAppState.UNKNOWN,
                 pods: Optional[List[Pod]] = None,
                 completed_at: Optional[int] = None,
                 creation_timestamp: Optional[int] = None):
        self.state = state
        self._pods = pods or []
        self._completed_at = completed_at
        self._is_failed = self.state == FlAppState.FAILED
        self._is_completed = self.state == FlAppState.COMPLETED
        self._creation_timestamp = creation_timestamp

    def __eq__(self, other):
        if not isinstance(other, FlApp):
            return False
        if len(self.pods) != len(other.pods):
            return False
        for index, pod in enumerate(self.pods):
            if pod != other.pods[index]:
                return False
        return self.state == other.state and \
               self.completed_at == other.completed_at

    @classmethod
    def from_json(cls, app_detail: dict) -> 'FlApp':
        flapp = app_detail.get('app', None)
        if flapp is None \
                or 'status' not in flapp \
                or not isinstance(flapp['status'], dict):
            return cls()

        pods: List[Pod] = []
        completed_at: Optional[int] = None
        # Parses pod related info
        replicas = flapp['status'].get('flReplicaStatus', {})
        for pod_type in replicas:
            for state in ['active', 'failed', 'succeeded']:
                for pod_name in replicas[pod_type].get(state, {}):
                    if state == 'active':
                        pod_state = PodState.RUNNING
                    if state == 'failed':
                        pod_state = PodState.FAILED_AND_FREED
                    if state == 'succeeded':
                        pod_state = PodState.SUCCEEDED_AND_FREED
                    pods.append(Pod(name=pod_name, pod_type=pod_type.upper(), state=pod_state))
        state = flapp['status'].get('appState')
        if flapp['status'].get('completionTime', None):
            # Completion time is a iso formatted datetime in UTC timezone
            completed_at = int(
                datetime.strptime(flapp['status']['completionTime'],
                                  '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp())

        name_to_pod = get_pod_dict_from_detail(app_detail.get('pods', {}))
        for pod in pods:
            # Only master pod and ps pod use state in flapp,
            # because they would not immediately exit when flapp is deleted.
            if pod.name not in name_to_pod:
                name_to_pod[pod.name] = pod
            elif pod.pod_type in ['MASTER', 'PS']:
                name_to_pod[pod.name].state = pod.state

        pods = list(name_to_pod.values())
        return cls(state=FlAppState.from_value(state),
                   pods=pods,
                   completed_at=completed_at,
                   creation_timestamp=get_creation_timestamp_from_k8s_app(flapp))

    @property
    def is_completed(self) -> bool:
        return self._is_completed

    @property
    def is_failed(self) -> bool:
        return self._is_failed

    @property
    def completed_at(self) -> int:
        return self._completed_at or 0

    @property
    def pods(self) -> List[Pod]:
        return self._pods

    @property
    def error_message(self) -> Optional[str]:
        return None

    @property
    def creation_timestamp(self) -> int:
        return self._creation_timestamp or 0


@unique
class SparkAppState(Enum):
    # state: https://github.com/GoogleCloudPlatform/spark-on-k8s-operator/ \
    # blob/075e5383e4678ddd70d7f3fdd71904aa3c9113c2 \
    # /pkg/apis/sparkoperator.k8s.io/v1beta2/types.go#L332

    # core state transition: SUBMITTED -> RUNNING -> COMPLETED/FAILED
    NEW = ''
    SUBMITTED = 'SUBMITTED'
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    SUBMISSION_FAILED = 'SUBMISSION_FAILED'
    PEDNING_RERUN = 'PENDING_RERUN'
    INVALIDATING = 'INVALIDATING'
    SUCCEEDING = 'SUCCEEDING'
    FAILING = 'FAILING'
    UNKNOWN = 'UNKNOWN'

    @staticmethod
    def from_value(value: str) -> 'SparkAppState':
        try:
            return SparkAppState(value)
        except ValueError:
            logging.error(f'Unexpected value of FlAppState: {value}')
            return SparkAppState.UNKNOWN


class SparkApp(K8sApp):

    def __init__(self,
                 pods: List[Pod],
                 state: SparkAppState = SparkAppState.UNKNOWN,
                 completed_at: Optional[int] = None,
                 err_message: Optional[str] = None,
                 creation_timestamp: Optional[int] = None):
        self.state = state
        self._completed_at = completed_at
        self._is_failed = self.state in [SparkAppState.FAILED]
        self._is_completed = self.state in [SparkAppState.COMPLETED]
        self._pods = pods
        self._error_message = err_message
        self._creation_timestamp = creation_timestamp

    def __eq__(self, other):
        if not isinstance(other, SparkApp):
            return False
        return self.state == other.state and \
            self.completed_at == other.completed_at

    @classmethod
    def from_json(cls, app_detail: dict) -> 'SparkApp':
        sparkapp = app_detail.get('app', None)
        if sparkapp is None \
                or 'status' not in sparkapp \
                or not isinstance(sparkapp['status'], dict):
            return cls(pods=[])

        status = sparkapp['status']
        application_state = status.get('applicationState', {})
        state = application_state.get('state', SparkAppState.UNKNOWN)
        completed_at: Optional[int] = None
        termination_time = status.get('terminationTime', None)
        if termination_time:
            # Completion time is a iso formatted datetime in UTC timezone
            completed_at = int(
                datetime.strptime(termination_time, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp())
        pods = list(get_pod_dict_from_detail(app_detail.get('pods', {})).values())
        err_message = application_state.get('errorMessage', None)
        return cls(state=SparkAppState.from_value(state),
                   completed_at=completed_at,
                   pods=pods,
                   err_message=err_message,
                   creation_timestamp=get_creation_timestamp_from_k8s_app(sparkapp))

    @property
    def is_completed(self) -> bool:
        return self._is_completed

    @property
    def is_failed(self) -> bool:
        return self._is_failed

    @property
    def completed_at(self) -> int:
        return self._completed_at or 0

    @property
    def pods(self) -> List[Pod]:
        return self._pods

    @property
    def error_message(self) -> Optional[str]:
        return self._error_message

    @property
    def creation_timestamp(self) -> int:
        return self._creation_timestamp or 0


class FedApp(K8sApp):

    def __init__(self, pods: List[Pod], success_condition: Condition, creation_timestamp: Optional[int] = None):
        self.success_condition = success_condition
        self._pods = pods
        self._completed_at = self.success_condition.last_transition_time and to_timestamp(
            self.success_condition.last_transition_time)
        self._is_failed = self.success_condition.status == Condition.FALSE
        self._is_completed = self.success_condition.status == Condition.TRUE
        self._creation_timestamp = creation_timestamp

    @classmethod
    def from_json(cls, app_detail: dict) -> 'FedApp':
        app = app_detail.get('app', None)
        if app is None \
                or 'status' not in app \
                or not isinstance(app['status'], dict):
            return cls([], Condition())

        status = app['status']
        success_condition = Condition()
        for c in status.get('conditions', []):
            c_proto: Condition = ParseDict(c, Condition())
            if c_proto.type == Condition.SUCCEEDED:
                success_condition = c_proto
        pods = list(get_pod_dict_from_detail(app_detail.get('pods', {})).values())
        return cls(success_condition=success_condition,
                   pods=pods,
                   creation_timestamp=get_creation_timestamp_from_k8s_app(app))

    @property
    def is_completed(self) -> bool:
        return self._is_completed

    @property
    def is_failed(self) -> bool:
        return self._is_failed

    @property
    def completed_at(self) -> int:
        return self._completed_at or 0

    @property
    def pods(self) -> List[Pod]:
        return self._pods

    @property
    def error_message(self) -> str:
        return f'{self.success_condition.reason}: {self.success_condition.message}'

    @property
    def creation_timestamp(self) -> int:
        return self._creation_timestamp or 0


class UnknownCrd(K8sApp):

    @classmethod
    def from_json(cls, app_detail: dict) -> 'UnknownCrd':
        return UnknownCrd()

    @property
    def is_completed(self) -> bool:
        return False

    @property
    def is_failed(self) -> bool:
        return False

    @property
    def completed_at(self) -> int:
        return 0

    @property
    def pods(self) -> List[Pod]:
        return []

    @property
    def error_message(self) -> Optional[str]:
        return None

    @property
    def creation_timestamp(self) -> Optional[str]:
        return None


def get_pod_dict_from_detail(pod_detail: dict) -> Dict[str, Pod]:
    """
    Generate name to Pod dict from pod json detail which got from pod cache.
    """
    name_to_pod = {}
    pods_json = pod_detail.get('items', [])
    for p in pods_json:
        pod = Pod.from_json(p)
        name_to_pod[pod.name] = pod
    return name_to_pod


def get_app_name_from_metadata(metadata: V1ObjectMeta) -> Optional[str]:
    """Extracts the CR app name from the metadata.

    Basically the metadata is from k8s watch event, we only care about the events
    related with CRs, so we will check owner references."""
    owner_refs = metadata.owner_references or []
    if not owner_refs:
        return None

    # Spark app uses labels to get app name instead of owner references,
    # because executors' owner reference will be driver, not the spark app.
    labels = metadata.labels or {}
    sparkapp_name = labels.get('sparkoperator.k8s.io/app-name', None)
    if sparkapp_name:
        return sparkapp_name

    owner = owner_refs[0]
    if CrdKind.from_value(owner.kind) == CrdKind.UNKNOWN:
        return None
    return owner.name
