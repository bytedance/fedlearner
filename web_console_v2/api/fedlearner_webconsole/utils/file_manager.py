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
import importlib
import logging
import os
import re
from collections import namedtuple

from typing import List

from tensorflow.io import gfile

# path: absolute path of the file
# size: file size in bytes
# mtime: time of last modification, unix timestamp in seconds.
File = namedtuple('File', ['path', 'size', 'mtime'])
# Currently the supported format '/' or 'hdfs://'
# TODO(chenyikan): Add oss format when verified.
SUPPORTED_FILE_PREFIXES = r'\.+\/|^\/|^hdfs:\/\/'


class FileManagerBase(object):
    """A base interface for file manager, please implement this interface
    if you have specific logic to handle files, for example, HDFS with ACL."""
    def can_handle(self, path: str) -> bool:
        """If the manager can handle such file."""
        raise NotImplementedError()

    def ls(self, path: str, recursive=False) -> List[str]:
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
        """Removes files under a path."""
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
        raise NotImplementedError()


class GFileFileManager(FileManagerBase):
    """Gfile file manager for all FS supported by TF,
     currently it covers all file types we have."""
    def can_handle(self, path):
        if path.startswith('fake://'):
            return False
        return re.match(SUPPORTED_FILE_PREFIXES, path)

    def ls(self, path: str, recursive=False) -> List[File]:
        def _get_file_stats(path: str):
            stat = gfile.stat(path)
            return File(path=path,
                        size=stat.length,
                        mtime=int(stat.mtime_nsec / 1e9))

        if not gfile.exists(path):
            raise ValueError(
                f'cannot access {path}: No such file or directory')
        # If it is a file
        if not gfile.isdir(path):
            return [_get_file_stats(path)]

        files = []
        if recursive:
            for root, _, res in gfile.walk(path):
                for file in res:
                    if not gfile.isdir(os.path.join(root, file)):
                        files.append(_get_file_stats(os.path.join(root, file)))
        else:
            for file in gfile.listdir(path):
                if not gfile.isdir(os.path.join(path, file)):
                    files.append(_get_file_stats(os.path.join(path, file)))
        # Files only
        return files

    def move(self, source: str, destination: str) -> bool:
        self.copy(source, destination)
        self.remove(source)
        return destination

    def remove(self, path: str) -> bool:
        if not gfile.isdir(path):
            return os.remove(path)
        return gfile.rmtree(path)

    def copy(self, source: str, destination: str) -> bool:
        if gfile.isdir(destination):
            # gfile requires a file name for copy destination.
            return gfile.copy(source,
                              os.path.join(destination,
                                           os.path.basename(source)),
                              overwrite=True)
        return gfile.copy(source, destination, overwrite=True)

    def mkdir(self, path: str) -> bool:
        return gfile.makedirs(path)

    def read(self, path: str) -> str:
        return gfile.GFile(path).read()


class FileManager(FileManagerBase):
    """A centralized manager to handle files.

    Please extend `FileManagerBase` and put the class path into
    `CUSTOMIZED_FILE_MANAGER`. For example,
    'fedlearner_webconsole.utils.file_manager:HdfsFileManager'
    """
    def __init__(self):
        self._file_managers = []
        cfm_path = os.environ.get('CUSTOMIZED_FILE_MANAGER')
        if cfm_path:
            module_path, class_name = cfm_path.split(':')
            module = importlib.import_module(module_path)
            # Dynamically construct a file manager
            customized_file_manager = getattr(module, class_name)
            self._file_managers.append(customized_file_manager())
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
        raise RuntimeError(f'ls is not supported for {path}')

    def move(self, source: str, destination: str) -> bool:
        logging.info('Moving files from [%s] to [%s]', source, destination)
        for fm in self._file_managers:
            if fm.can_handle(source) and fm.can_handle(destination):
                return fm.move(source, destination)
        # TODO(chenyikan): Support cross FileManager move by using buffers.
        raise RuntimeError(
            f'move is not supported for {source} and {destination}')

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
        raise RuntimeError(
            f'copy is not supported for {source} and {destination}')

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
