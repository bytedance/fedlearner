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

from envs import Envs


def _is_valid_env(env: dict) -> bool:
    return env.get('valueFrom', None) is not None or \
           env.get('value', None) is not None


def _normalize_env(env: dict) -> dict:
    if 'value' in env:
        env['value'] = str(env['value'])
    return env


def get_system_envs():
    """Gets a JSON string to represent system envs."""
    # Most envs should be from pod's env
    envs = [{
        'name': 'POD_IP',
        'valueFrom': {
            'fieldRef': {
                'fieldPath': 'status.podIP'
            }
        }
    }, {
        'name': 'POD_NAME',
        'valueFrom': {
            'fieldRef': {
                'fieldPath': 'metadata.name'
            }
        }
    }, {
        'name': 'CPU_REQUEST',
        'valueFrom': {
            'resourceFieldRef': {
                'resource': 'requests.cpu'
            }
        }
    }, {
        'name': 'MEM_REQUEST',
        'valueFrom': {
            'resourceFieldRef': {
                'resource': 'requests.memory'
            }
        }
    }, {
        'name': 'CPU_LIMIT',
        'valueFrom': {
            'resourceFieldRef': {
                'resource': 'limits.cpu'
            }
        }
    }, {
        'name': 'MEM_LIMIT',
        'valueFrom': {
            'resourceFieldRef': {
                'resource': 'limits.memory'
            }
        }
    }, {
        'name': 'ES_HOST',
        'value': Envs.ES_HOST
    }, {
        'name': 'ES_PORT',
        'value': Envs.ES_PORT
    }, {
        'name': 'DB_HOST',
        'value': Envs.DB_HOST
    }, {
        'name': 'DB_PORT',
        'value': Envs.DB_PORT
    }, {
        'name': 'DB_DATABASE',
        'value': Envs.DB_DATABASE
    }, {
        'name': 'DB_USERNAME',
        'value': Envs.DB_USERNAME
    }, {
        'name': 'DB_PASSWORD',
        'value': Envs.DB_PASSWORD
    }, {
        'name': 'KVSTORE_TYPE',
        'value': Envs.KVSTORE_TYPE
    }, {
        'name': 'ETCD_NAME',
        'value': Envs.ETCD_NAME
    }, {
        'name': 'ETCD_ADDR',
        'value': Envs.ETCD_ADDR
    }, {
        'name': 'ETCD_BASE_DIR',
        'value': Envs.ETCD_BASE_DIR
    }, {
        'name': 'ROBOT_USERNAME',
        'value': Envs.ROBOT_USERNAME
    }, {
        'name': 'ROBOT_PWD',
        'value': Envs.ROBOT_PWD
    }, {
        'name': 'WEB_CONSOLE_V2_ENDPOINT',
        'value': Envs.WEB_CONSOLE_V2_ENDPOINT
    }, {
        'name': 'HADOOP_HOME',
        'value': Envs.HADOOP_HOME
    }, {
        'name': 'JAVA_HOME',
        'value': Envs.JAVA_HOME
    }, {
        'name': 'PRE_START_HOOK',
        'value': Envs.PRE_START_HOOK
    }, {
        'name': 'METRIC_COLLECTOR_EXPORT_ENDPOINT',
        'value': Envs.APM_SERVER_ENDPOINT
    }, {
        'name': 'CLUSTER',
        'value': Envs.CLUSTER
    }]
    valid_envs = [env for env in envs if _is_valid_env(env)]
    envs = [_normalize_env(env) for env in valid_envs]
    return envs


if __name__ == '__main__':
    print(get_system_envs())
