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
import os
from http import HTTPStatus
import subprocess
import time
import requests
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
    NOT_FOUND = "NOT_FOUND"
    UNKNOWN = "UNKNOWN"


class WebConsoleClient(object):
    def __init__(self, base_url, username, password, num_retries=3):
        token = login_webconsole(base_url, username, password)
        self._headers = {
            'Authorization': f'Bearer {token}'
        }
        self._spark_api_url = os.path.join(base_url, "sparkapps")
        self._num_retries = num_retries

    @staticmethod
    def _check_response(response):
        status = None
        msg = ''
        if 'code' in response:
            if int(response['code']) == 404:
                status = SparkAPPStatus.NOT_FOUND
            else:
                status = SparkAPPStatus.FAILED
        if 'message' in response:
            msg = 'Status: {}, Message: {}'.format(response['code'],
                                                   response['message'])

        return status, msg

    def get_sparkapplication(self,
                             name: str) \
            -> (SparkAPPStatus, str):
        spark_job_url = os.path.join(self._spark_api_url, name)
        for _ in range(self._num_retries):
            response = requests.get(url=spark_job_url, headers=self._headers)
            if response is None:
                time.sleep(10)
                continue
            response = json.loads(response.text)
            status, msg = self._check_response(response)
            if status == SparkAPPStatus.NOT_FOUND:
                return status, msg
            if status is not None:
                logging.error("Get spark application error %s", msg)
                time.sleep(10)
                continue
            k8s_status = set(item.value for item in SparkAPPStatus)
            if 'data' in response and 'state' in response['data'] and \
                response['data']['state'] in k8s_status:
                return SparkAPPStatus[response['data']['state']], response
        return SparkAPPStatus.PENDING, ''

    def get_sparkapplication_log(self,
                                 name: str) -> str:
        spark_job_url = os.path.join(self._spark_api_url, name, "log")
        params = {"lines": "10000"}
        for i in range(self._num_retries):
            response = requests.get(url=spark_job_url, headers=self._headers,
                                    params=params)
            if response is None:
                time.sleep(10)
                continue
            response = json.loads(response.text)
            if 'data' in response:
                return '\n'.join(sorted(response['data']))
            time.sleep(10)
        return ''

    @staticmethod
    def _spark_task_config(task_name, file_config,
                           driver_config, executor_config):
        return {
            "name": task_name,
            "image_url": file_config.image,
            "main_application": file_config.entry_file,
            "command": [
                "--config", file_config.config_file,
                "--oss_access_key_id", file_config.oss_access_key_id,
                "--oss_access_key_secret", file_config.oss_access_key_secret,
                "--oss_endpoint", file_config.oss_endpoint],
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
            executor_config) -> bool:
        task_config = self._spark_task_config(task_name, file_config,
                                              driver_config, executor_config)
        for i in range(self._num_retries):
            response = requests.post(url=self._spark_api_url,
                                     json=task_config,
                                     headers=self._headers)
            if response is None:
                logging.error("Create spark application failed")
                time.sleep(10)
                continue
            response = json.loads(response.text)
            status, msg = self._check_response(response)
            if status is None:
                return True
            logging.error("Create spark application error %s", msg)
            time.sleep(10)
        return False

    def delete_sparkapplication(self,
                                name: str) -> bool:
        spark_job_url = os.path.join(self._spark_api_url, name)
        for i in range(self._num_retries):
            requests.delete(url=spark_job_url, headers=self._headers)
            status, msg = self.get_sparkapplication(name)
            if status == SparkAPPStatus.NOT_FOUND:
                return True
            logging.info("Sleep 60s to wait spark app killed. msg: %s", msg)
            time.sleep(60)
        return False


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
            return SparkAPPStatus.NOT_FOUND, ''
        if self._process.returncode is None:
            return SparkAPPStatus.RUNNING, ''
        if self._process.returncode == 0:
            return SparkAPPStatus.COMPLETED, ''
        return SparkAPPStatus.FAILED, 'Failed'

    def create_sparkapplication(
        self,
        task_name,
        file_config,
        driver_config,
        executor_config) -> bool:
        entry_script = file_config.entry_file
        args = file_config.config_file
        cmd = ['python', entry_script] + args
        logging.info(cmd)
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        return True

    def get_sparkapplication_log(self,
                                 name: str) -> str:
        logging.info("Get log of spark application %s", name)
        return ""

    def delete_sparkapplication(self,
                                name: str,) -> bool:
        logging.info("Delete spark application %s", name)
        return True
