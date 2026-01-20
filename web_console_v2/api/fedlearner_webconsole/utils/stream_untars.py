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
# pylint: disable=redefined-builtin, no-else-continue, broad-except, consider-using-f-string, consider-using-with
import tarfile
import gzip
from tarfile import (BLOCKSIZE, TarFile, ReadError, EOFHeaderError, InvalidHeaderError, EmptyHeaderError,
                     TruncatedHeaderError, SubsequentHeaderError)
import tempfile
import logging
from typing import BinaryIO

from fedlearner_webconsole.utils.file_manager import FileManager, FILE_PREFIX

CHUNK_SIZE = 1 << 22

TAR_SUFFIX = ('.tar',)
GZIP_SUFFIX = ('.gz', '.tgz')


class _TarFileWithoutCache(TarFile):

    def next(self):
        self._check('ra')
        if self.firstmember is not None:
            m = self.firstmember
            self.firstmember = None
            return m

        # Advance the file pointer.
        if self.offset != self.fileobj.tell():
            self.fileobj.seek(self.offset - 1)
            if not self.fileobj.read(1):
                raise tarfile.ReadError('unexpected end of data')

        # Read the next block.
        tarinfo = None
        while True:
            try:
                tarinfo = self.tarinfo.fromtarfile(self)
            except EOFHeaderError as e:
                if self.ignore_zeros:
                    self._dbg(2, '0x%X: %s' % (self.offset, e))
                    self.offset += BLOCKSIZE
                    continue
            except InvalidHeaderError as e:
                if self.ignore_zeros:
                    self._dbg(2, '0x%X: %s' % (self.offset, e))
                    self.offset += BLOCKSIZE
                    continue
                elif self.offset == 0:
                    raise ReadError(str(e)) from e
            except EmptyHeaderError as e:
                if self.offset == 0:
                    raise ReadError('empty file') from e
            except TruncatedHeaderError as e:
                if self.offset == 0:
                    raise ReadError(str(e)) from e
            except SubsequentHeaderError as e:
                raise ReadError(str(e)) from e
            break

        if tarinfo is None:
            self._loaded = True

        return tarinfo


class StreamingUntar(object):
    """
    A class used to support decompressing .tar.gz streamly.
    1. The first step is to decompress the gzip file, chunk by chunk, to the tarball
    2. Then use TarFileWithoutCache to untar the tarball with a fixed memory usage.
    3. TarFileWithoutCache is a subclass of TarFile, but remove the cache in its next function.
    eg:
        convert xxx.tar.gz -> xxx
    """

    def __init__(self, fm: FileManager, chunksize: int = CHUNK_SIZE) -> None:
        super().__init__()
        self._fm = fm
        self.chunksize = chunksize

    def _uncompressed(self, source: str, temp_file: BinaryIO) -> str:
        try:
            with gzip.GzipFile(source, 'rb') as gf:
                stream = gf.read(self.chunksize)
                while stream:
                    temp_file.write(stream)
                    stream = gf.read(self.chunksize)
        except Exception as e:
            logging.error(f'failed to streaming decompress file from:{source}, ex: {e}')
        return temp_file.name

    def _untar(self, source: str, dest: str) -> None:
        tar = _TarFileWithoutCache.open(source)
        try:
            entry = tar.next()
            while entry:
                tar.extract(entry, path=dest)
                entry = tar.next()
        except Exception as e:
            logging.error(f'failed to streaming untar file, from {source} to {dest}, ex: {e}')
        finally:
            tar.close()

    # TODO(lixiaoguang.01): remove this function after using FileManager
    def _trim_prefix(self, path: str) -> str:
        if path.startswith(FILE_PREFIX):
            return path.split(FILE_PREFIX, 1)[1]
        return path

    def untar(self, source: str, dest: str) -> None:
        """
        untar the source.tar.gz to the dest directory, with a fixed memory usage.

        Args:
            source: source path, only support local file system
            dest:  destination path, only support local file system

        Raises:
            ValueError: if tarfile not ends with .tar/.tar.gz
            Exception: if io operation failed
        """
        # TODO(lixiaoguang.01): use FileManager in untar and uncompressed
        source = self._trim_prefix(source)
        dest = self._trim_prefix(dest)

        if not source.endswith(TAR_SUFFIX + GZIP_SUFFIX):
            raise ValueError(f'{source} is not ends with tarfile or gzip extension')
        with tempfile.NamedTemporaryFile('wb') as temp:
            if source.endswith(GZIP_SUFFIX):
                source = self._uncompressed(source, temp)
            self._untar(source, dest)
