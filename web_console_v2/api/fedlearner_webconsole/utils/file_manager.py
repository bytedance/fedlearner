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
from collections import namedtuple

from pathlib import Path
from typing import List

from pyarrow import fs
from pyarrow.fs import FileSystem
from tensorflow.io import gfile
import tensorflow_io  # pylint: disable=unused-import

from fedlearner_webconsole.envs import Envs

# path: absolute path of the file
# size: file size in bytes
# mtime: time of last modification, unix timestamp in seconds.
File = namedtuple('File', ['path', 'size', 'mtime'])


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


class DefaultFileManager(FileManagerBase):
    """Default file manager for native file system or NFS."""
    def can_handle(self, path):
        return path.startswith('/')

    def ls(self, path: str, recursive=False) -> List[File]:
        def _get_file_stats(path: str):
            stat = os.stat(path)
            return File(path=path, size=stat.st_size, mtime=int(stat.st_mtime))

        if not Path(path).exists():
            return []
        # If it is a file
        if Path(path).is_file():
            return [_get_file_stats(path)]

        files = []
        if recursive:
            for root, _, res in os.walk(path):
                for file in res:
                    if Path(os.path.join(root, file)).is_file():
                        files.append(_get_file_stats(os.path.join(root, file)))
        else:
            for file in os.listdir(path):
                if Path(os.path.join(path, file)).is_file():
                    files.append(_get_file_stats(os.path.join(path, file)))
        # Files only
        return files

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
            logging.error('Error during remove %s', str(e))
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
            os.makedirs(path, exist_ok=True)
            return True
        except Exception as e:  # pylint: disable=broad-except
            logging.error('Error during create %s', e)
        return False


class HdfsFileManager(FileManagerBase):
    """A wrapper of snakebite client."""
    def can_handle(self, path):
        return path.startswith('hdfs://')

    def __init__(self):
        self._client, _ = FileSystem.from_uri(Envs.HDFS_SERVER)

    def _unwrap_path(self, path):
        if path.startswith('hdfs://'):
            return path[7:]
        return path

    def _wrap_path(self, path):
        if not path.startswith('hdfs://'):
            return f'hdfs://{path}'
        return path

    def ls(self, path: str, recursive=False) -> List[File]:
        path = self._unwrap_path(path)
        files = []
        try:
            for file in self._client.get_file_info(
                    fs.FileSelector(path, recursive=recursive)):
                if file.type == fs.FileType.File:
                    files.append(
                        File(
                            path=self._wrap_path(file.path),
                            size=file.size,
                            # ns to second
                            mtime=int(file.mtime_ns / 1e9)))
        except RuntimeError as error:
            # This is a hack that snakebite can not handle generator
            if str(error) == 'generator raised StopIteration':
                pass
            else:
                raise
        return files

    def move(self, source: str, destination: str) -> bool:
        source = self._unwrap_path(source)
        destination = self._unwrap_path(destination)
        return len(list(self._client.move(source, destination))) > 0

    def remove(self, path: str) -> bool:
        path = self._unwrap_path(path)
        try:
            if self._client.get_file_info(path).is_file:
                self._client.delete_file(path)
            else:
                self._client.delete_dir(path)
            return True
        except Exception as e:  # pylint: disable=broad-except
            logging.error('Error during remove %s', str(e))
        return False

    def copy(self, source: str, destination: str) -> bool:
        try:
            gfile.copy(source, destination)
            return True
        except Exception as e:  # pylint: disable=broad-except
            logging.error('Error during copy %s', e)
        return False

    def mkdir(self, path: str) -> bool:
        path = self._unwrap_path(path)
        self._client.create_dir(path)
        return True


class GFileFileManager(FileManagerBase):
    """Gfile file manager for all FS supported by TF."""

    def can_handle(self, path):
        # TODO: List tf support
        if path.startswith('fake://'):
            return False
        if not Envs.SUPPORT_HDFS and path.startswith('hdfs://'):
            return False
        return True

    def ls(self, path: str, recursive=False) -> List[File]:
        def _get_file_stats(path: str):
            stat = gfile.stat(path)
            return File(path=path,
                        size=stat.length,
                        mtime=int(stat.mtime_nsec/1e9))

        if not gfile.exists(path):
            return []
        # If it is a file
        if not gfile.isdir(path):
            return [_get_file_stats(path)]

        files = []
        if recursive:
            for root, _, res in gfile.walk(path):
                for file in res:
                    if not gfile.isdir(os.path.join(root, file)):
                        files.append(
                            _get_file_stats(os.path.join(root, file)))
        else:
            for file in gfile.listdir(path):
                if not gfile.isdir(os.path.join(path, file)):
                    files.append(
                        _get_file_stats(os.path.join(path, file)))
        # Files only
        return files

    def move(self, source: str, destination: str) -> bool:
        try:
            self.copy(source, destination)
            self.remove(source)
            return True
        except Exception as e:  # pylint: disable=broad-except
            logging.error('Error during move %s', e)
            return False

    def remove(self, path: str) -> bool:
        try:
            if not gfile.isdir(path):
                os.remove(path)
                return True
            if gfile.isdir(path):
                gfile.rmtree(path)
                return True
        except Exception as e:  # pylint: disable=broad-except
            logging.error('Error during remove %s', str(e))
        return False

    def copy(self, source: str, destination: str) -> bool:
        try:
            gfile.copy(source, destination)
            return True
        except Exception as e:  # pylint: disable=broad-except
            logging.error('Error during copy %s', e)
        return False

    def mkdir(self, path: str) -> bool:
        try:
            gfile.makedirs(path)
            return True
        except Exception as e:  # pylint: disable=broad-except
            logging.error('Error during create %s', e)
        return False


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
        if Envs.HDFS_SERVER:
            self._file_managers.append(HdfsFileManager())
        self._file_managers.append(DefaultFileManager())
        self._file_managers.append(GFileFileManager())

    def can_handle(self, path):
        for fm in self._file_managers:
            if fm.can_handle(path):
                return True
        return False

    def ls(self, path: str, recursive=False) -> List[File]:
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
