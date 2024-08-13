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
import importlib
import logging
import os
import re
import fsspec
from collections import namedtuple

from typing import List, Dict, Union, Optional

from tensorflow.io import gfile  # pylint: disable=import-error

from envs import Envs

# path: absolute path of the file
# size: file size in bytes
# mtime: time of last modification, unix timestamp in seconds.
File = namedtuple('File', ['path', 'size', 'mtime', 'is_directory'])
# Currently the supported format '/', 'hdfs://' or 'file://'
# TODO(chenyikan): Add oss format when verified.
SUPPORTED_FILE_PREFIXES = r'\.+\/|^\/|^hdfs:\/\/|^file:\/\/'
FILE_PREFIX = 'file://'


class FileManagerBase(object):
    """A base interface for file manager, please implement this interface
    if you have specific logic to handle files, for example, HDFS with ACL."""

    def can_handle(self, path: str) -> bool:
        """If the manager can handle such file."""
        raise NotImplementedError()

    def info(self) -> Dict:
        """Give details of entry at path."""
        raise NotImplementedError()

    def ls(self, path: str, include_directory=False) -> List[File]:
        """Lists files under a path.
        Raises:
            ValueError: When the path does not exist.
        """
        raise NotImplementedError()

    def move(self, source: str, destination: str) -> bool:
        """Moves a file from source to destination, if destination
        is a folder then move into that folder. Files that already exist
         will be overwritten."""
        raise NotImplementedError()

    def remove(self, path: str) -> bool:
        """Removes files under a path. Raises exception when path is not exists"""
        raise NotImplementedError()

    def copy(self, source: str, destination: str) -> bool:
        """Copies a file from source to destination, if destination
        is a folder then move into that folder. Files that already exist
         will be overwritten."""
        raise NotImplementedError()

    def mkdir(self, path: str) -> bool:
        """Creates a directory. If already exists, return False"""
        raise NotImplementedError()

    def read(self, path: str) -> str:
        """Read from a file path."""
        raise NotImplementedError()

    def read_bytes(self, path: str) -> bytes:
        """Read from a file path by Bytes"""
        raise NotImplementedError()

    def write(self, path: str, payload: str, mode: str = 'w') -> bool:
        """Write payload to a file path. Will override original content."""
        raise NotImplementedError()

    def exists(self, path: str) -> bool:
        """Determine whether a path exists or not"""
        raise NotImplementedError()

    def isdir(self, path: str) -> bool:
        """Return whether the path is a directory or not"""
        raise NotImplementedError()

    def listdir(self, path: str) -> List[str]:
        """Return all file/directory names in this path, not recursive"""
        raise NotImplementedError()

    def rename(self, source: str, dest: str):
        """Rename or move a file / directory"""
        raise NotImplementedError()


class GFileFileManager(FileManagerBase):
    """Gfile file manager for all FS supported by TF,
     currently it covers all file types we have."""

    # TODO(gezhengqiang): change the class name
    def __init__(self):
        self._fs_dict = {}

    def get_customized_fs(self, path: str) -> fsspec.spec.AbstractFileSystem:
        """
        Ref: https://filesystem-spec.readthedocs.io/en/latest/_modules/fsspec/core.html?highlight=split_protocol#
        # >>> from fsspec.core import split_protocol
        # >>> split_protocol('hdfs:///user/test')
        # >>> ('hdfs', '/user/test')
        """
        protocol = self._get_protocol_from_path(path) or 'file'
        if protocol not in self._fs_dict:
            self._fs_dict[protocol] = fsspec.get_mapper(path).fs
        return self._fs_dict[protocol]

    def can_handle(self, path):
        if path.startswith('fake://'):
            return False
        return re.match(SUPPORTED_FILE_PREFIXES, path)

    @staticmethod
    def _get_protocol_from_path(path: str) -> Optional[str]:
        """If path is '/data', then return None. If path is 'file:///data', then return 'file'."""
        return fsspec.core.split_protocol(path)[0]

    @staticmethod
    def _get_file_stats_from_dict(file: Dict) -> File:
        return File(path=file['path'],
                    size=file['size'],
                    mtime=int(file['mtime'] if 'mtime' in file else file['last_modified_time']),
                    is_directory=(file['type'] == 'directory'))

    def info(self, path: str) -> str:
        fs = self.get_customized_fs(path)
        info = fs.info(path)
        if 'last_modified' in info:
            info['last_modified_time'] = info['last_modified']
        return info

    def ls(self, path: str, include_directory=False) -> List[File]:
        fs = self.get_customized_fs(path)
        if not fs.exists(path):
            raise ValueError(f'cannot access {path}: No such file or directory')
        # If it is a file
        info = self.info(path)
        if info['type'] != 'directory':
            info['path'] = path
            return [self._get_file_stats_from_dict(info)]

        files = []
        for file in fs.ls(path, detail=True):
            # file['name'] from 'fs.ls' delete the protocol of the path,
            # here use 'join' to obtain the file['path'] with protocol
            base_path = self.info(path)['name']  # base_path does not have protocol
            rel_path = os.path.relpath(file['name'], base_path)  # file['name'] does not have protocol
            file['path'] = os.path.join(path, rel_path)  # file['path'] has protocol as well as path
            if file['type'] == 'directory':
                if include_directory:
                    files.append(self._get_file_stats_from_dict(file))
            else:
                files.append(self._get_file_stats_from_dict(file))

        return files

    def move(self, source: str, destination: str) -> bool:
        self.copy(source, destination)
        self.remove(source)
        return destination

    def remove(self, path: str) -> bool:
        if not gfile.isdir(path):
            return gfile.remove(path)
        return gfile.rmtree(path)

    def copy(self, source: str, destination: str) -> bool:
        if gfile.isdir(destination):
            # gfile requires a file name for copy destination.
            return gfile.copy(source, os.path.join(destination, os.path.basename(source)), overwrite=True)
        return gfile.copy(source, destination, overwrite=True)

    def mkdir(self, path: str) -> bool:
        return gfile.makedirs(path)

    def read(self, path: str) -> str:
        return gfile.GFile(path).read()

    def read_bytes(self, path: str) -> bytes:
        return gfile.GFile(path, 'rb').read()

    def write(self, path: str, payload: str, mode: str = 'w') -> bool:
        if gfile.isdir(path):
            raise ValueError(f'{path} is a directory: Must provide a filename')
        if gfile.exists(path):
            self.remove(path)
        if not gfile.exists(os.path.dirname(path)):
            self.mkdir(os.path.dirname(path))
        return gfile.GFile(path, mode).write(payload)

    def exists(self, path: str) -> bool:
        return gfile.exists(path)

    def isdir(self, path: str) -> bool:
        return gfile.isdir(path)

    def listdir(self, path: str) -> List[str]:
        """Return all file/directory names in this path, not recursive"""
        if not gfile.isdir(path):
            raise ValueError(f'{path} must be a directory!')
        return gfile.listdir(path)

    def rename(self, source: str, dest: str):
        gfile.rename(source, dest)


class FileManager(FileManagerBase):
    """A centralized manager to handle files.

    Please extend `FileManagerBase` and put the class path into
    `CUSTOMIZED_FILE_MANAGER`. For example,
    'fedlearner_webconsole.utils.file_manager:HdfsFileManager'
    """

    def __init__(self):
        self._file_managers = []
        cfm_path = Envs.CUSTOMIZED_FILE_MANAGER
        if cfm_path:
            module_path, class_name = cfm_path.split(':')
            module = importlib.import_module(module_path)
            # Dynamically construct a file manager
            customized_file_manager = getattr(module, class_name)
            self._file_managers.append(customized_file_manager())
        self._file_managers.append(GFileFileManager())

    def can_handle(self, path) -> bool:
        for fm in self._file_managers:
            if fm.can_handle(path):
                return True
        return False

    def info(self, path: str) -> Dict:
        for fm in self._file_managers:
            if fm.can_handle(path):
                return fm.info(path)
        raise RuntimeError(f'info is not supported for {path}')

    def ls(self, path: str, include_directory=False) -> List[File]:
        for fm in self._file_managers:
            if fm.can_handle(path):
                return fm.ls(path, include_directory=include_directory)
        raise RuntimeError(f'ls is not supported for {path}')

    def move(self, source: str, destination: str) -> bool:
        logging.info('Moving files from [%s] to [%s]', source, destination)
        for fm in self._file_managers:
            if fm.can_handle(source) and fm.can_handle(destination):
                return fm.move(source, destination)
        # TODO(chenyikan): Support cross FileManager move by using buffers.
        raise RuntimeError(f'move is not supported for {source} and {destination}')

    def remove(self, path: str) -> bool:
        logging.info('Removing file [%s]', path)
        for fm in self._file_managers:
            if fm.can_handle(path):
                return fm.remove(path)
        raise RuntimeError(f'remove is not supported for {path}')

    def copy(self, source: str, destination: str) -> bool:
        logging.info('Copying file from [%s] to [%s]', source, destination)
        for fm in self._file_managers:
            if fm.can_handle(source) and fm.can_handle(destination):
                return fm.copy(source, destination)
        # TODO(chenyikan): Support cross FileManager move by using buffers.
        raise RuntimeError(f'copy is not supported for {source} and {destination}')

    def mkdir(self, path: str) -> bool:
        logging.info('Create directory [%s]', path)
        for fm in self._file_managers:
            if fm.can_handle(path):
                return fm.mkdir(path)
        raise RuntimeError(f'mkdir is not supported for {path}')

    def read(self, path: str) -> str:
        logging.info(f'Read file from [{path}]')
        for fm in self._file_managers:
            if fm.can_handle(path):
                return fm.read(path)
        raise RuntimeError(f'read is not supported for {path}')

    def read_bytes(self, path: str) -> bytes:
        logging.info(f'Read file from [{path}]')
        for fm in self._file_managers:
            if fm.can_handle(path):
                return fm.read_bytes(path)
        raise RuntimeError(f'read_bytes is not supported for {path}')

    def write(self, path: str, payload: Union[str, bytes], mode: str = 'w') -> bool:
        logging.info(f'Write file to [{path}]')
        for fm in self._file_managers:
            if fm.can_handle(path):
                return fm.write(path, payload, mode)
        raise RuntimeError(f'write is not supported for {path}')

    def exists(self, path: str) -> bool:
        logging.info(f'Check [{path}] existence')
        for fm in self._file_managers:
            if fm.can_handle(path):
                return fm.exists(path)
        raise RuntimeError(f'check existence is not supported for {path}')

    def isdir(self, path: str) -> bool:
        logging.info(f'Determine whether [{path}] is a directory')
        for fm in self._file_managers:
            if fm.can_handle(path):
                return fm.isdir(path)
        raise RuntimeError(f'check isdir is not supported for {path}')

    def listdir(self, path: str) -> List[str]:
        logging.info(f'get file/directory names from [{path}]')
        for fm in self._file_managers:
            if fm.can_handle(path):
                return fm.listdir(path)
        raise RuntimeError(f'listdir is not supported for {path}')

    def rename(self, source: str, dest: str):
        logging.info(f'Rename[{source}] to [{dest}]')
        for fm in self._file_managers:
            if fm.can_handle(source):
                fm.rename(source, dest)
                return
        raise RuntimeError(f'rename is not supported for {source}')


file_manager = FileManager()
