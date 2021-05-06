# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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
from typing import Optional, List


# Please keep the value consistent with operator's definition
@unique
class PodType(Enum):
    UNKNOWN = 'UNKNOWN'
    # Parameter server
    PS = 'PS'
    # Master worker
    MASTER = 'MASTER'
    WORKER = 'WORKER'

    @staticmethod
    def from_value(value: str) -> 'PodType':
        try:
            if isinstance(value, str):
                value = value.upper()
            return PodType(value)
        except ValueError:
            logging.error(f'Unexpected value of PodType: {value}')
            return PodType.UNKNOWN


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


class MessageProvider(metaclass=ABCMeta):
    @abstractmethod
    def get_message(self, private: bool = False) -> Optional[str]:
        pass


class ContainerState(MessageProvider):
    def __init__(self, state: str,
                 message: Optional[str] = None,
                 reason: Optional[str] = None):
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
    def __init__(self, cond_type: str,
                 message: Optional[str] = None,
                 reason: Optional[str] = None):
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
                 pod_type: PodType,
                 container_states: List[ContainerState] = None,
                 pod_conditions: List[PodCondition] = None):
        self.name = name
        self.state = state or PodState.UNKNOWN
        self.pod_type = pod_type
        self.container_states = container_states or []
        self.pod_conditions = pod_conditions or []

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
               self.pod_type == other.pod_type

    def to_dict(self, include_private_info: bool = False):
        # TODO: to reuse to_dict from db.py
        messages = []
        for container_state in self.container_states:
            message = container_state.get_message(include_private_info)
            if message is not None:
                messages.append(message)
        for pod_condition in self.pod_conditions:
            message = pod_condition.get_message(include_private_info)
            if message is not None:
                messages.append(message)

        return {
            'name': self.name,
            'pod_type': self.pod_type.name,
            'state': self.state.name,
            'message': ', '.join(messages)
        }

    @classmethod
    def from_json(cls, p: dict) -> 'Pod':
        """Extracts information from original K8S pod info.

        Schema ref: https://github.com/garethr/kubernetes-json-schema/blob/
        master/v1.6.5-standalone/pod.json"""
        container_states: List[ContainerState] = []
        pod_conditions: List[PodCondition] = []
        if 'containerStatuses' in p['status']:
            for state, detail in \
                    p['status']['containerStatuses'][0]['state'].items():
                container_states.append(ContainerState(
                    state=state,
                    message=detail.get('message'),
                    reason=detail.get('reason')
                ))
        if 'conditions' in p['status']:
            for cond in p['status']['conditions']:
                pod_conditions.append(PodCondition(
                    cond_type=cond['type'],
                    message=cond.get('message'),
                    reason=cond.get('reason')
                ))
        return cls(
            name=p['metadata']['name'],
            pod_type=PodType.from_value(
                p['metadata']['labels']['fl-replica-type']),
            state=PodState.from_value(p['status']['phase']),
            container_states=container_states,
            pod_conditions=pod_conditions)


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


class FlApp(object):
    def __init__(self,
                 state: FlAppState = FlAppState.UNKNOWN,
                 pods: Optional[List[Pod]] = None,
                 completed_at: Optional[int] = None):
        self.state = state
        self.pods = pods or []
        self.completed_at = completed_at

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
    def from_json(cls, flapp: dict) -> 'FlApp':
        if flapp is None or 'status' not in flapp:
            return cls()

        pods: List[Pod] = []
        completed_at: Optional[int] = None
        # Parses pod related info
        replicas = flapp['status'].get('flReplicaStatus', {})
        for pod_type in replicas:
            for state in ['failed', 'succeeded']:
                for pod_name in replicas[pod_type].get(state, {}):
                    if state == 'failed':
                        pod_state = PodState.FAILED_AND_FREED
                    else:
                        pod_state = PodState.SUCCEEDED_AND_FREED
                    pods.append(Pod(
                        name=pod_name,
                        pod_type=PodType.from_value(pod_type),
                        state=pod_state))
        state = flapp['status'].get('appState')
        if flapp['status'].get('completionTime', None):
            # Completion time is a iso formatted datetime in UTC timezone
            completed_at = int(datetime.strptime(
                flapp['status']['completionTime'],
                '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                               .timestamp())

        return cls(state=FlAppState.from_value(state),
                   pods=pods,
                   completed_at=completed_at)
