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
import logging
import os
import tempfile

import fsspec
from fedlearner_webconsole.utils.file_manager import FileManager
from fedlearner_webconsole.utils.stream_untars import StreamingUntar
from fedlearner_webconsole.utils.stream_tars import StreamingTar
from tensorflow.io import gfile  # pylint: disable=import-error
from typing import Union

HDFS_PREFIX = 'hdfs://'
TAR_SUFFIX = ('.tar',)
GZIP_SUFFIX = ('.gz', '.tgz')


class FileOperator(object):

    def __init__(self):
        self._fm = FileManager()
        self._streaming_untar = StreamingUntar(self._fm)
        self._streaming_tar = StreamingTar(self._fm)

    def clear_and_make_an_empty_dir(self, dir_name: str):
        try:
            self._fm.remove(dir_name)
        except Exception as err:  # pylint: disable=broad-except
            logging.debug('failed to remove %s with exception %s', dir_name, err)
        finally:
            self._fm.mkdir(dir_name)

    def getsize(self, path: str) -> float:
        """Return all files size under path and dont skip the sybolic link
        Args:
            path (str): file/directory

        Returns:
            total_size (float): total size(B)
        """
        fs: fsspec.AbstractFileSystem = fsspec.get_mapper(path).fs

        def get_dsize(dpath: str) -> int:
            """Gets size for directory."""
            total = 0
            for sub_path in fs.ls(dpath, detail=True):
                if sub_path.get('type') == 'directory':
                    total += get_dsize(sub_path.get('name'))
                else:
                    total += sub_path.get('size', 0)
            return total

        if not fs.exists(path):
            return 0
        if fs.isdir(path):
            return get_dsize(path)
        # File
        return fs.size(path)

    def archive_to(self, source: Union[str, list], destination: str, gzip_compress: bool = False, move: bool = False):
        """compress the file/directory to the destination tarfile/gzip file.
        src and dst should be path-like objects or strings.
        eg:

        Args:
             source (str): source file/directory
             destination (str): tarfile/gzip file
             gzip_compress (bool): if gzip_compress is true, will compress to gzip file
             move (bool): if move is true, will delete source after archive
        Raises:
            ValueError: if destination tarfile not ends with .tar/.tar.gz
            Exception: if io operation failed
        """
        logging.info(f'File Operator: will archive {source} to {destination}')
        # check destination suffix
        if not gzip_compress and not destination.endswith(TAR_SUFFIX):
            logging.error(f'Error in archive_to: destination:{destination} is not endswith TAR_SUFFIX')
            raise ValueError(f'destination:{destination} is not endswith TAR_SUFFIX')
        if gzip_compress and not destination.endswith(GZIP_SUFFIX):
            logging.error(f'Error in archive_to: destination:{destination} is not endswith GZIP_SUFFIX')
            raise ValueError(f'destination:{destination} is not endswith GZIP_SUFFIX')
        src_paths = source
        if isinstance(source, str):
            src_paths = [source]
        # check the source list is on the same platform or not.
        is_from_hdfs = src_paths[0].startswith(HDFS_PREFIX)
        for src_path in src_paths:
            if src_path.startswith(HDFS_PREFIX) != is_from_hdfs:
                logging.error(f'Error in archive_to: source list:{source} is not on the same platform.')
                raise ValueError(f'source list:{source} is not the same platform.')
        is_to_hdfs = destination.startswith(HDFS_PREFIX)
        is_hdfs = is_from_hdfs or is_to_hdfs
        if is_hdfs:
            # src_parent_dir/src_basename/xx -> tmp_dir/src_basename/xx -> tmp_dir/dest_basename -> dest
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_archive_path = os.path.join(tmp_dir, os.path.basename(destination))
                tmp_src_paths = []
                for src_path in src_paths:
                    tmp_src_path = os.path.join(tmp_dir, os.path.basename(src_path))
                    # if src_path is dir, copytree only copy the sub-items in src_path
                    if self._fm.isdir(src_path):
                        self._fm.mkdir(tmp_src_path)
                    self._copytree(src_path, tmp_src_path)
                    tmp_src_paths.append(tmp_src_path)
                self._streaming_tar.archive(tmp_src_paths, tmp_archive_path, gzip_compress=gzip_compress)
                self._fm.copy(tmp_archive_path, destination)
        else:
            self._streaming_tar.archive(source, destination, gzip_compress=gzip_compress)
        if move:
            self._fm.remove(source)

    def extract_to(self, source: str, destination: str, create_dir: bool = False):
        """extract the file to the directory dst. src and dst should be path-like objects or strings.

        Args:
             source (str): source file/directory/tarfile
             destination (str): directory
             create_dir (bool): if create_dir is true, will create the destination dir
        Raises:
            ValueError: if tarfile not ends with .tar/.tar.gz
            Exception: if io operation failed
        """
        self.copy_to(source, destination, extract=True, move=False, create_dir=create_dir)

    def copy_to(self,
                source: str,
                destination: str,
                extract: bool = False,
                move: bool = False,
                create_dir: bool = False):
        """Copies the file src to the directory dst. src and dst should be path-like objects or strings,
        the file will be copied into dst using the base filename from src.

        Args:
             source (str): source file/directory/tarfile
             destination (str): directory
             extract (bool): extract source file if it is tarfile
             move (bool): if move is true, will delete source after copy
             create_dir (bool): if create_dir is true, will create the destination dir

        Raises:
            ValueError: if tarfile not ends with .tar/.tar.gz
            Exception: if io operation failed
        """
        # create the destination dir
        if create_dir and not self._fm.exists(destination):
            self._fm.mkdir(destination)
        if not self._fm.isdir(destination):
            logging.error(f'Error in copy_to: destination:{destination} is not a existed directory')
            raise ValueError(f'destination:{destination} is not a existed directory')
        if not extract:
            self._copytree(source, destination)
            if move:
                self._fm.remove(source)
            return
        is_hdfs = source.startswith(HDFS_PREFIX) or destination.startswith(HDFS_PREFIX)
        if is_hdfs:
            self._unpack_hdfs_tarfile(source, destination, is_move=move)
        else:
            self._unpack_tarfile(source, destination, is_move=move)

    def _unpack_tarfile(self, filename: str, extract_dir: str, is_move: bool = False):
        """Unpack tar/tar.gz/ `filename` to `extract_dir`
        """
        self._streaming_untar.untar(filename, extract_dir)
        if is_move:
            self._fm.remove(filename)

    def _unpack_hdfs_tarfile(self, filename: str, extract_dir: str, is_move: bool = False):
        """Unpack tar/tar.gz/ `filename` to `extract_dir`
        will copy the tarfile locally to unzip it and then upload
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                self._fm.copy(filename, tmp_dir)
                tmp_tarfile = os.path.join(tmp_dir, os.path.basename(filename))
                tmp_sub_dir = os.path.join(tmp_dir, 'tmp_sub_dir')
                self._fm.mkdir(tmp_sub_dir)
                self._streaming_untar.untar(tmp_tarfile, tmp_sub_dir)
            except Exception as e:  # pylint: disable=broad-except
                logging.error(f'failed to untar file {filename}, exception: {e}')
                return
            self._copytree(tmp_sub_dir, extract_dir)
        if is_move:
            self._fm.remove(filename)

    def _copytree(self, source: str, dest: str):
        """Recursively copy an entire directory tree rooted at src to a directory named dest

        Args:
             source (str): source file/directory/tarfile
             dest (str): directory

        Raises:
            Exception: if io operation failed
        """
        # file
        if self._fm.exists(source) and not self._fm.isdir(source):
            self._fm.copy(source, dest)
        # directory
        # TODO(wangzeju): use file manager instead of gfile
        for root, dirs, files in gfile.walk(source):
            relative_path = os.path.relpath(root, source)
            for f in files:
                file_path = os.path.join(root, f)
                dest_file = os.path.join(dest, relative_path, f)
                try:
                    self._fm.copy(file_path, dest_file)
                except Exception as e:  # pylint: disable=broad-except
                    logging.error(f'failed to copy file, from {file_path} to {dest_file}, ex: {e}')
            for d in dirs:
                dest_dir = os.path.join(dest, relative_path, d)
                try:
                    self._fm.mkdir(dest_dir)
                except Exception as e:  # pylint: disable=broad-except
                    logging.error(f'failed to mkdir {dest_dir}, ex: {e}')
