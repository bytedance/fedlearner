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
import os
import logging
import tempfile

from typing import Tuple

from envs import Envs
from fedlearner_webconsole.proto import sparkapp_pb2
from fedlearner_webconsole.utils.file_manager import FileManager
from fedlearner_webconsole.sparkapp.schema import SparkAppConfig, from_k8s_resp
from fedlearner_webconsole.k8s.k8s_client import (SPARKOPERATOR_CUSTOM_GROUP, SPARKOPERATOR_CUSTOM_VERSION, CrdKind,
                                                  k8s_client, SPARKOPERATOR_NAMESPACE)
from fedlearner_webconsole.utils.file_operator import FileOperator

UPLOAD_PATH = Envs.STORAGE_ROOT


class SparkAppService(object):

    def __init__(self) -> None:
        self._base_dir = os.path.join(UPLOAD_PATH, 'sparkapp')
        self._file_manager = FileManager()
        self._file_operator = FileOperator()
        self._file_manager.mkdir(self._base_dir)

    def _get_sparkapp_upload_path(self, name: str) -> Tuple[bool, str]:
        """get upload path for specific sparkapp

        Args:
            name (str): sparkapp name

        Returns:
            Tuple[bool, str]:
                bool: True if this directory already exists
                str:  upload path for this sparkapp

        """
        sparkapp_path = os.path.join(self._base_dir, name)
        existable = self._file_manager.isdir(sparkapp_path)
        return existable, sparkapp_path

    def submit_sparkapp(self, config: SparkAppConfig) -> sparkapp_pb2.SparkAppInfo:
        """submit sparkapp

        Args:
            config (SparkAppConfig): sparkapp config

        Raises:
            InternalException: if fail to get sparkapp

        Returns:
            SparkAppInfo: resp of sparkapp
        """
        logging.info(f'submit sparkapp with config:{config}')
        sparkapp_path = config.files_path
        if not config.files_path:
            _, sparkapp_path = self._get_sparkapp_upload_path(config.name)
            self._file_operator.clear_and_make_an_empty_dir(sparkapp_path)

            # In case there is no files
            if config.files is not None:
                with tempfile.TemporaryDirectory() as temp_dir:
                    tar_path = os.path.join(temp_dir, 'files.tar')
                    with open(tar_path, 'wb') as fwrite:
                        fwrite.write(config.files)
                    self._file_operator.copy_to(tar_path, sparkapp_path, extract=True)

        config_dict = config.build_config(sparkapp_path)
        logging.info(f'submit sparkapp, config: {config_dict}')
        resp = k8s_client.create_app(config_dict, SPARKOPERATOR_CUSTOM_GROUP, SPARKOPERATOR_CUSTOM_VERSION,
                                     CrdKind.SPARK_APPLICATION.value)
        return from_k8s_resp(resp)

    def get_sparkapp_info(self, name: str) -> sparkapp_pb2.SparkAppInfo:
        """ get sparkapp info

        Args:
            name (str): sparkapp name

        Raises:
            WebConsoleApiException

        Returns:
            SparkAppInfo: resp of sparkapp
        """
        resp = k8s_client.get_sparkapplication(name)
        return from_k8s_resp(resp)

    def get_sparkapp_log(self, name: str, lines: int) -> str:
        """ get sparkapp log

        Args:
            name (str): sparkapp name
            lines (int): max lines of log

        Returns:
            str: sparkapp log
        """
        return k8s_client.get_pod_log(f'{name}-driver', SPARKOPERATOR_NAMESPACE, tail_lines=lines)

    def delete_sparkapp(self, name: str) -> sparkapp_pb2.SparkAppInfo:
        """delete sparkapp
            - delete sparkapp. If failed, raise exception
            - delete the tmp filesystem


        Args:
            name (str): sparkapp name

        Raises:
            WebConsoleApiException

        Returns:
            SparkAppInfo: resp of sparkapp
        """
        existable, sparkapp_path = self._get_sparkapp_upload_path(name)
        if existable:
            self._file_manager.remove(sparkapp_path)

        resp = k8s_client.delete_sparkapplication(name)
        sparkapp_info = from_k8s_resp(resp)

        return sparkapp_info
