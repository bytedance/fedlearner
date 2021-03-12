# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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
import json
import os


def get_system_envs():
    """Gets a JSON string to represent system envs."""
    # Most envs should be from pod's env
    envs = [
        {
            'name': 'POD_IP',
            'valueFrom': {
                'fieldRef': {
                    'fieldPath': 'status.podIP'
                }
            }
        },
        {
            'name': 'POD_NAME',
            'valueFrom': {
                'fieldRef': {
                    'fieldPath': 'metadata.name'
                }
            }
        },
        {
            'name': 'CPU_REQUEST',
            'valueFrom': {
                'resourceFieldRef': {
                    'resource': 'requests.cpu'
                }
            }
        },
        {
            'name': 'MEM_REQUEST',
            'valueFrom': {
                'resourceFieldRef': {
                    'resource': 'requests.memory'
                }
            }
        },
        {
            'name': 'CPU_LIMIT',
            'valueFrom': {
                'resourceFieldRef': {
                    'resource': 'limits.cpu'
                }
            }
        },
        {
            'name': 'MEM_LIMIT',
            'valueFrom': {
                'resourceFieldRef': {
                    'resource': 'limits.memory'
                }
            }
        },
        {
            'name': 'ES_HOST',
            'value': os.getenv('ES_HOST')
        },
        {
            'name': 'ES_PORT',
            'value': os.getenv('ES_PORT')
        },
        {
            'name': 'DB_HOST',
            'value': os.getenv('DB_HOST')
        },
        {
            'name': 'DB_PORT',
            'value': os.getenv('DB_PORT')
        },
        {
            'name': 'DB_DATABASE',
            'value': os.getenv('DB_DATABASE')
        },
        {
            'name': 'DB_USERNAME',
            'value': os.getenv('DB_USERNAME')
        },
        {
            'name': 'DB_PASSWORD',
            'value': os.getenv('DB_PASSWORD')
        },
        {
            'name': 'KVSTORE_TYPE',
            'value': os.getenv('KVSTORE_TYPE')
        },
        {
            'name': 'ETCD_NAME',
            'value': os.getenv('ETCD_NAME')
        },
        {
            'name': 'ETCD_ADDR',
            'value': os.getenv('ETCD_ADDR')
        },
        {
            'name': 'ETCD_BASE_DIR',
            'value': os.getenv('ETCD_BASE_DIR')
        },
    ]
    return ','.join([json.dumps(env) for env in envs])


if __name__ == '__main__':
    print(get_system_envs())
