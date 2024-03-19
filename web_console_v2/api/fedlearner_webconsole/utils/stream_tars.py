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
# pylint: disable=redefined-builtin, no-else-continue, broad-except, consider-using-with
import os
from io import BytesIO
from tarfile import TarFile, NUL, BLOCKSIZE, TarInfo
import tempfile
import gzip
import logging
from typing import BinaryIO, AnyStr, Union

from fedlearner_webconsole.utils.file_manager import FileManager, FILE_PREFIX

CHUNK_SIZE = 1 << 22


class FileStream:

    def __init__(self):
        self.buffer = BytesIO()
        self.offset = 0

    def write(self, s: AnyStr):
        self.buffer.write(s)
        self.offset += len(s)

    def tell(self):
        return self.offset

    def close(self):
        self.buffer.close()

    def read_all(self):
        try:
            return self.buffer.getvalue()
        finally:
            self.buffer.close()
            self.buffer = BytesIO()


class _TarFileWithoutCache(TarFile):
    """ Building a tar file chunk-by-chunk.
    """

    def __init__(self, directories: Union[str, list], file_chunk_size: int = CHUNK_SIZE):  # pylint: disable=super-init-not-called
        self._contents = [directories]
        self._file_chunk_size = file_chunk_size
        self._is_multiple = False
        if isinstance(directories, list):
            self._is_multiple = True
            self._contents = directories

    @staticmethod
    def _stream_file_into_tar(tarinfo: TarInfo, tar: TarFile, fh: BinaryIO, buf_size: int):
        out = tar.fileobj

        for b in iter(lambda: fh.read(buf_size), b''):
            out.write(b)
            yield

        blocks, remainder = divmod(tarinfo.size, BLOCKSIZE)
        if remainder > 0:
            out.write(NUL * (BLOCKSIZE - remainder))
            blocks += 1
        tar.offset += blocks * BLOCKSIZE
        yield

    def __iter__(self):
        out = FileStream()
        tar = TarFile(fileobj=out, mode='w')
        for content in self._contents:
            if os.path.isdir(content):
                prefix, name = os.path.split(content)
                prefix_len = len(prefix) + len(os.path.sep)
                tar.add(name=content, arcname=name, recursive=False)
                for path, dirs, files in os.walk(content):
                    arcpath = path[prefix_len:]
                    # Add files
                    # Use this script instead of tar.add() to avoid the non-fixed memory usage caused by the invoke of
                    # tar.addfile(), which will cache tarinfo in TarFile.members
                    for f in files:
                        filepath = os.path.join(path, f)
                        with open(filepath, 'rb') as fh:
                            tarinfo = tar.gettarinfo(name=filepath, arcname=os.path.join(arcpath, f), fileobj=fh)
                            tar.addfile(tarinfo)
                            for _ in self._stream_file_into_tar(tarinfo, tar, fh, self._file_chunk_size):
                                yield out.read_all()

                    # Add directories
                    for d in dirs:
                        tar.add(name=os.path.join(path, d), arcname=os.path.join(arcpath, d), recursive=False)
                    yield out.read_all()
            else:
                filepath = content
                filename = os.path.basename(filepath)
                with open(filepath, 'rb') as fh:
                    tarinfo = tar.gettarinfo(name=filepath, arcname=filename, fileobj=fh)
                    tar.addfile(tarinfo)
                    for _ in self._stream_file_into_tar(tarinfo, tar, fh, self._file_chunk_size):
                        yield out.read_all()

        tar.close()
        yield out.read_all()
        out.close()


class StreamingTar(object):
    """ Building a tar file chunk-by-chunk.
    """

    def __init__(self, fm: FileManager, chunksize: int = CHUNK_SIZE) -> None:
        super().__init__()
        self._fm = fm
        self.chunksize = chunksize

    def _archive(self, source_path: Union[str, list], target_path: str):
        logging.info(f'will archive {source_path} to {target_path}')
        tarfile = _TarFileWithoutCache(source_path, self.chunksize)
        with open(target_path, 'wb') as target_f:
            for chunk in tarfile:
                target_f.write(chunk)

    def _compress(self, filename: str, target_path: str):
        with open(filename, 'rb') as tar_f:
            with gzip.GzipFile(target_path, 'wb') as gzip_f:
                stream = tar_f.read(self.chunksize)
                while stream:
                    gzip_f.write(stream)
                    stream = tar_f.read(self.chunksize)

    # TODO(lixiaoguang.01): remove this function after using FileManager
    def _trim_prefix(self, path: str) -> str:
        if path.startswith(FILE_PREFIX):
            return path.split(FILE_PREFIX, 1)[1]
        return path

    # TODO(zeju): provide tar file in-memory option
    def archive(self, source_path: Union[str, list], target_path: str, gzip_compress: bool = False):
        # TODO(lixiaoguang.01): use FileManager in archive and compress
        if isinstance(source_path, str):
            source_path = self._trim_prefix(source_path)
        else:  # list
            trimmed_source_path = []
            for single_path in source_path:
                trimmed_source_path.append(self._trim_prefix(single_path))
            source_path = trimmed_source_path
        target_path = self._trim_prefix(target_path)

        with tempfile.NamedTemporaryFile('wb') as temp:
            if gzip_compress:
                self._archive(source_path, temp.name)
                self._compress(temp.name, target_path)
            else:
                self._archive(source_path, target_path)
