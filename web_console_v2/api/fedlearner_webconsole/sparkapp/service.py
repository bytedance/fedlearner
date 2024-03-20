# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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
from fedlearner_webconsole.utils.file_manager import FileManager
from fedlearner_webconsole.sparkapp.schema import SparkAppConfig, SparkAppInfo
from fedlearner_webconsole.utils.k8s_client import k8s_client
from fedlearner_webconsole.utils.tars import TarCli

UPLOAD_PATH = Envs.STORAGE_ROOT


class SparkAppService(object):
    def __init__(self) -> None:
        self._base_dir = os.path.join(UPLOAD_PATH, 'sparkapp')
        self._file_client = FileManager()

        self._file_client.mkdir(self._base_dir)

    def _clear_and_make_an_empty_dir(self, dir_name: str):
        try:
            self._file_client.remove(dir_name)
        except Exception as err:  # pylint: disable=broad-except
            logging.error('failed to remove %s with exception %s', dir_name,
                          err)
        finally:
            self._file_client.mkdir(dir_name)

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
        existable = False
        try:
            self._file_client.ls(sparkapp_path)
            existable = True
        except ValueError:
            existable = False

        return existable, sparkapp_path

    def _copy_files_to_target_filesystem(self, source_filesystem_path: str,
                                         target_filesystem_path: str) -> bool:
        """ copy files to remote filesystem
            - untar if file is tared
            - copy files to remote filesystem

        Args:
            source_filesystem_path (str): local filesystem
            target_filesystem_path (str): remote filesystem

        Returns:
            bool: whether success
        """
        temp_path = source_filesystem_path
        if source_filesystem_path.find('.tar') != -1:
            temp_path = os.path.abspath(
                os.path.join(source_filesystem_path, '../tmp'))
            os.makedirs(temp_path)
            TarCli.untar_file(source_filesystem_path, temp_path)

        for root, dirs, files in os.walk(temp_path):
            relative_path = os.path.relpath(root, temp_path)
            for f in files:
                file_path = os.path.join(root, f)
                remote_file_path = os.path.join(target_filesystem_path,
                                                relative_path, f)
                self._file_client.copy(file_path, remote_file_path)
            for d in dirs:
                remote_dir_path = os.path.join(target_filesystem_path,
                                               relative_path, d)
                self._file_client.mkdir(remote_dir_path)

        return True

    def submit_sparkapp(self, config: SparkAppConfig) -> SparkAppInfo:
        """submit sparkapp

        Args:
            config (SparkAppConfig): sparkapp config

        Raises:
            InternalException: if fail to get sparkapp

        Returns:
            SparkAppInfo: resp of sparkapp
        """
        sparkapp_path = config.files_path
        if config.files_path is None:
            _, sparkapp_path = self._get_sparkapp_upload_path(config.name)
            self._clear_and_make_an_empty_dir(sparkapp_path)

            with tempfile.TemporaryDirectory() as temp_dir:
                tar_path = os.path.join(temp_dir, 'files.tar')
                with open(tar_path, 'wb') as fwrite:
                    fwrite.write(config.files)
                self._copy_files_to_target_filesystem(
                    source_filesystem_path=tar_path,
                    target_filesystem_path=sparkapp_path)

        config_dict = config.build_config(sparkapp_path)
        logging.info(f'submit sparkapp, config: {config_dict}')
        resp = k8s_client.create_sparkapplication(config_dict)
        return SparkAppInfo.from_k8s_resp(resp)

    def get_sparkapp_info(self, name: str) -> SparkAppInfo:
        """ get sparkapp info

        Args:
            name (str): sparkapp name

        Raises:
            WebConsoleApiException

        Returns:
            SparkAppInfo: resp of sparkapp
        """
        resp = k8s_client.get_sparkapplication(name)
        return SparkAppInfo.from_k8s_resp(resp)

    def delete_sparkapp(self, name: str) -> SparkAppInfo:
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
            self._file_client.remove(sparkapp_path)

        resp = k8s_client.delete_sparkapplication(name)
        sparkapp_info = SparkAppInfo.from_k8s_resp(resp)

        return sparkapp_info
