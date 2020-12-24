import glob
import importlib
import logging
import os
import shutil
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


class _DefaultFileManager(FileManagerBase):
    """Default file manager for native file system or NFS."""

    def can_handle(self, path):
        return path.startswith('/')

    def ls(self, path: str, recursive=False) -> List[str]:
        return glob.glob(path, recursive=recursive)

    def move(self, source: str, destination: str) -> bool:
        try:
            shutil.move(source, destination)
            return True
        except Exception as e:
            logging.error('Error during move %s', e)
            return False

    def remove(self, path: str) -> bool:
        try:
            if os.path.isfile(path):
                os.remove(path)
                return True
            elif os.path.isdir(path):
                shutil.rmtree(path)
                return True
        except Exception as e:
            logging.error('Error during remove %s', e)
        return False


class HdfsFileManager(FileManagerBase):
    """A wrapper of snakebite client."""

    def can_handle(self, path):
        return path.startswith('hdfs://')

    def __init__(self):
        self._client = AutoConfigClient()

    def ls(self, path: str, recursive=False) -> List[str]:
        return list(self._client.ls([path], recurse=recursive))

    def move(self, source: str, destination: str) -> bool:
        return len(list(self._client.rename(source, destination))) > 0

    def remove(self, path: str) -> bool:
        return len(list(self._client.delete([path], recursive=True))) > 0


class FileManager(FileManagerBase):
    """A centralized manager to handle files.

    Please extend `FileManagerBase` and put the class path into `CUSTOMIZED_FILE_MANAGER`.
    For example, 'fedlearner_webconsole.utils.file_manager:HdfsFileManager'"""
    def __init__(self):
        self._file_managers = []
        cfm_path = os.environ.get('CUSTOMIZED_FILE_MANAGER')
        if cfm_path:
            module_path, class_name = cfm_path.split(':')
            module = importlib.import_module(module_path)
            # Dynamically construct a file manager
            customized_file_manager = getattr(module, class_name)
            self._file_managers.append(customized_file_manager())
        self._file_managers.append(_DefaultFileManager())

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
