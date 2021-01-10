# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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
import importlib
import logging
import os
import shutil

from pathlib import Path
from typing import List

from snakebite.client import AutoConfigClient


class FileManagerBase(object):
    """A base interface for file manager, please implement this interface
    if you have specific logic to handle files, for example, HDFS with ACL."""
    def can_handle(self, path: str) -> bool:
        """If the manager can handle such file."""
        raise NotImplementedError()

    def ls(self, path: str, recursive=False) -> List[str]:
        """Lists files under a path."""
        raise NotImplementedError()

    def move(self, source: str, destination: str) -> bool:
        """Moves a file from source to destination, if destination
        is a folder then move into that folder."""
        raise NotImplementedError()

    def remove(self, path: str) -> bool:
        """Removes files under a path."""
        raise NotImplementedError()

    def copy(self, source: str, destination: str) -> bool:
        """Copies a file from source to destination, if destination
        is a folder then move into that folder."""
        raise NotImplementedError()

    def mkdir(self, path: str) -> bool:
        """Creates a directory. If already exists, return False"""
        raise NotImplementedError()

    def get_size(self, path: str) -> int:
        """Get size of a file or directory."""
        raise NotImplementedError()

    def is_dir(self, path: str) -> bool:
        """Is path a directory"""
        raise NotImplementedError()


class DefaultFileManager(FileManagerBase):
    """Default file manager for native file system or NFS."""

    def can_handle(self, path):
        return path.startswith('/')

    def ls(self, path: str, recursive=False) -> List[str]:
        if not Path(path).exists():
            return []
        # If it is a file
        if Path(path).is_file():
            return [path]

        files = []
        if recursive:
            for root, dirs, fs in os.walk(path):
                for file in fs:
                    files.append(os.path.join(root, file))
        else:
            files = [
                os.path.join(path, file)
                for file in os.listdir(path)
            ]
        # Files only
        return list(filter(lambda f: Path(f).is_file(), files))

    def move(self, source: str, destination: str) -> bool:
        try:
            shutil.move(source, destination)
            return True
        except Exception as e:  # pylint: disable=broad-except
            logging.error('Error during move %s', e)
            return False

    def remove(self, path: str) -> bool:
        try:
            if os.path.isfile(path):
                os.remove(path)
                return True
            if os.path.isdir(path):
                shutil.rmtree(path)
                return True
        except Exception as e:  # pylint: disable=broad-except
            logging.error('Error during remove %s', e)
        return False

    def copy(self, source: str, destination: str) -> bool:
        try:
            shutil.copy(source, destination)
            return True
        except Exception as e:  # pylint: disable=broad-except
            logging.error('Error during copy %s', e)
        return False

    def mkdir(self, path: str) -> bool:
        try:
            os.makedirs(path)
            return True
        except Exception as e:  # pylint: disable=broad-except
            logging.error('Error during create %s', e)
        return False

    def get_size(self, path: str) -> int:
        return os.path.getsize(path)

    def is_dir(self, path: str) -> bool:
        return os.path.isdir(path)


class HdfsFileManager(FileManagerBase):
    """A wrapper of snakebite client."""

    def can_handle(self, path):
        return path.startswith('hdfs://')

    def __init__(self):
        self._client = AutoConfigClient()

    def ls(self, path: str, recursive=False) -> List[str]:
        files = []
        for file in self._client.ls([path], recurse=recursive):
            if file['file_type'] == 'f':
                files.append(file['path'])
        return files

    def move(self, source: str, destination: str) -> bool:
        return len(list(self._client.rename([source], destination))) > 0

    def remove(self, path: str) -> bool:
        return len(list(self._client.delete([path]))) > 0

    def copy(self, source: str, destination: str) -> bool:
        # TODO
        raise NotImplementedError()

    def mkdir(self, path: str) -> bool:
        return next(self._client.mkdir([path], create_parent=True))\
            .get('result')

    def get_size(self, path: str) -> int:
        # return like [{'path': '/', 'length': 123L}]
        return int(self._client.du([path])[0].get('length')[:-1])

    def is_dir(self, path: str) -> bool:
        return self._client.test(path, directory=True)


class FileManager(FileManagerBase):
    """A centralized manager to handle files.

    Please extend `FileManagerBase` and put the class path into
    `CUSTOMIZED_FILE_MANAGER`. For example,
    'fedlearner_webconsole.utils.file_manager:HdfsFileManager'"""
    def __init__(self):
        self._file_managers = []
        cfm_path = os.environ.get('CUSTOMIZED_FILE_MANAGER')
        if cfm_path:
            module_path, class_name = cfm_path.split(':')
            module = importlib.import_module(module_path)
            # Dynamically construct a file manager
            customized_file_manager = getattr(module, class_name)
            self._file_managers.append(customized_file_manager())
        self._file_managers.append(DefaultFileManager())

    def can_handle(self, path):
        for fm in self._file_managers:
            if fm.can_handle(path):
                return True
        return False

    def ls(self, path: str, recursive=False) -> List[str]:
        for fm in self._file_managers:
            if fm.can_handle(path):
                return fm.ls(path, recursive=recursive)
        raise RuntimeError('ls is not supported')

    def move(self, source: str, destination: str) -> bool:
        logging.info('Moving files from [%s] to [%s]', source, destination)
        for fm in self._file_managers:
            if fm.can_handle(source) and fm.can_handle(destination):
                return fm.move(source, destination)
        raise RuntimeError('move is not supported')

    def remove(self, path: str) -> bool:
        logging.info('Removing file [%s]', path)
        for fm in self._file_managers:
            if fm.can_handle(path):
                return fm.remove(path)
        raise RuntimeError('remove is not supported')

    def copy(self, source: str, destination: str) -> bool:
        logging.info('Copying file from [%s] to [%s]', source, destination)
        for fm in self._file_managers:
            if fm.can_handle(source) and fm.can_handle(destination):
                return fm.copy(source, destination)
        raise RuntimeError('copy is not supported')

    def mkdir(self, path: str) -> bool:
        logging.info('Create directory [%s]', path)
        for fm in self._file_managers:
            if fm.can_handle(path):
                return fm.mkdir(path)
        raise RuntimeError('mkdir is not supported')

    def get_size(self, path: str) -> int:
        logging.info('Get size of [%s]', path)
        for fm in self._file_managers:
            if fm.can_handle(path):
                return fm.get_size(path)
        raise RuntimeError('get_size is not supported')

    def is_dir(self, path: str) -> bool:
        logging.info('Test is dir [%s]', path)
        for fm in self._file_managers:
            if fm.can_handle(path):
                return fm.is_dir(path)
        raise RuntimeError('is_dir is not supported')
