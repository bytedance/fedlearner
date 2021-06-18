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
import base64
import enum
import json
import logging
import requests
import os
import subprocess
from http import HTTPStatus
from kubernetes.client.exceptions import ApiException


def login_webconsole(base_url, username, password):
    login_url = base_url + '/auth/signin'
    password = base64.b64encode(password.encode()).decode()
    response = requests.post(
        login_url,
        data={
            'username': username,
            'password': password
        }
    )
    if response.status_code != HTTPStatus.OK:
        logging.fatal("Failed to login webconsole. response %s", response)
        return None
    response = json.loads(response.content)
    if 'data' not in response:
        logging.fatal("Login webconsole error. response %s", response)
        return None
    token = response['data'].get('access_token')
    return token


class SparkAPPStatus(enum.Enum):
    SUBMITTED = "SUBMITTED"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    SUCCEEDING = "SUCCEEDING"
    FAILED = "FAILED"
    FAILING = "FAILING"


class WebConsoleClient(object):
    def __init__(self, base_url, username, password):
        token = login_webconsole(base_url, username, password)
        self._headers = {
            'Authorization': f'Bearer {token}'
        }
        self._spark_api_url = os.path.join(base_url, "sparkapps")

    def _raise_runtime_error(self, status, message):
        raise RuntimeError('Status: {}, Message: {}'.format(
            status, message))

    def _check_response(self, response):
        if 'code' in response and 'message' in response:
            self._raise_runtime_error(response['code'], response['message'])

    def get_sparkapplication(self,
                             name: str) \
            -> (SparkAPPStatus, str):
        spark_job_url = os.path.join(self._spark_api_url, name)
        response = requests.get(url=spark_job_url, headers=self._headers)
        response = json.loads(response.text)
        self._check_response(response)
        k8s_status = set(item.value for item in SparkAPPStatus)
        if 'data' in response and 'state' in response['data'] and \
            response['data']['state'] in k8s_status:
            return SparkAPPStatus[response['data']['state']], response
        return SparkAPPStatus.PENDING, ''

    @staticmethod
    def _spark_task_config(task_name, file_config,
                           driver_config, executor_config):
        return {
            "name": task_name,
            "image_url": file_config.image,
            "main_application": file_config.entry_file,
            "command": ["--config", file_config.config_file],
            "py_files": [file_config.dep_file],
            "driver_config": {
                "cores": driver_config.cores,
                "memory": driver_config.memory
            },
            "executor_config": {
                "cores": executor_config.cores,
                "memory": executor_config.memory,
                "instances": executor_config.instances
            },
        }

    def create_sparkapplication(
            self,
            task_name,
            file_config,
            driver_config,
            executor_config) -> dict:
        task_config = self._spark_task_config(task_name, file_config,
                                              driver_config, executor_config)
        response = requests.post(url=self._spark_api_url,
                                 json=task_config,
                                 headers=self._headers)
        response = json.loads(response.text)
        self._check_response(response)
        return response

    def delete_sparkapplication(self,
                                name: str) -> dict:
        spark_job_url = os.path.join(self._spark_api_url, name)
        response = requests.get(url=spark_job_url, headers=self._headers)
        return json.loads(response.text)


class FakeWebConsoleClient(object):
    def __init__(self):
        self._process = None

    def _raise_runtime_error(self, exception: ApiException):
        raise RuntimeError('[{}] {}'.format(exception.status,
                                            exception.reason))

    def get_sparkapplication(self,
                             name: str) -> (SparkAPPStatus, str):
        stdout_data, stderr_data = self._process.communicate()
        logging.info(stdout_data.decode('utf-8'))
        if not self._process:
            self._raise_runtime_error(
                ApiException("Task {} not exist".format(name)))
        elif self._process.returncode is None:
            return SparkAPPStatus.RUNNING, ''
        elif self._process.returncode == 0:
            return SparkAPPStatus.COMPLETED, ''
        return SparkAPPStatus.FAILED, 'Failed'

    def create_sparkapplication(
        self,
        task_name,
        file_config,
        driver_config,
        executor_config) -> dict:
        entry_script = file_config.entry_file
        args = file_config.config_file
        cmd = ['python', entry_script] + args
        logging.info(cmd)
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        return {
            'apiVersion': 'sparkoperator.k8s.io/v1beta2',
            'kind': 'SparkApplication',
            'metadata': {
                'creationTimestamp': '2021-05-13T08:41:48Z',
                'generation': 1,
                'name': task_name,
                'resourceVersion': '2894990020',
                'selfLink': '/apis/sparkoperator.k8s.io/v1beta2/namespaces',
                'uid': "123-ds3"
            }
        }

    def delete_sparkapplication(self,
                                name: str,
                                ) -> dict:
        logging.info("Delete spark application %s", name)
        return {}
