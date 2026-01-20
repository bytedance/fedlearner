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
import enum
import os
import tempfile
import logging
from datetime import datetime
from typing import List, Optional
from urllib.parse import unquote
from werkzeug.formparser import FileStorage
from werkzeug.utils import secure_filename
from io import BytesIO
from envs import Envs
from flask import send_file
from flask_restful import Resource, Api
from google.protobuf.json_format import MessageToDict
from webargs.flaskparser import use_kwargs
from webargs import fields
from tensorflow.io import gfile

from fedlearner_webconsole.proto import common_pb2
from fedlearner_webconsole.auth.third_party_sso import credentials_required
from fedlearner_webconsole.exceptions import (InvalidArgumentException, NoAccessException, NotFoundException)
from fedlearner_webconsole.utils.file_manager import FileManager
from fedlearner_webconsole.utils.file_operator import FileOperator


class FileType(enum.Enum):
    FILE = 'file'
    DATASET = 'dataset'


# Files with these extentions will be displayed directly.
DISPLAYABLE_EXTENTION = ['.txt', '.py']
UPLOAD_FILE_PATH = f'upload_{FileType.FILE.value}'
IMAGE_EXTENSION = ('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')
FILE_WHITELIST = (Envs.STORAGE_ROOT, 'hdfs://')


def _is_path_accessible(path):
    return path.startswith(FILE_WHITELIST)


def _is_image_extension(filename):
    return filename.lower().endswith(IMAGE_EXTENSION)


class FileApi(Resource):

    def __init__(self):
        self._file_manager = FileManager()

    @credentials_required
    @use_kwargs({'path': fields.String(required=True, help='the filepath that you want to read')}, location='query')
    def get(self, path: str):
        """Get file content by filepath
        ---
        tags:
          - file
        description: >
            Get file content by filepath.
            Note that this api isn't design for binary content.
        parameters:
        - in: query
          name: path
          schema:
            type: string
        responses:
          200:
            description: content of the specified path
            content:
              application/json:
                schema:
                  type: string
        """
        filepath = path
        if not _is_path_accessible(filepath):
            raise NoAccessException('access to this file or directory is not allowed ')
        content = self._file_manager.read(filepath)
        return {'data': content}


class FilesApi(Resource):

    def __init__(self):
        self._storage_root = Envs.STORAGE_ROOT
        self._file_manager = FileManager()
        self._file_operator = FileOperator()
        self._file_dir = os.path.join(self._storage_root, UPLOAD_FILE_PATH)
        self._file_manager.mkdir(self._file_dir)
        # keep align with original upload directory
        self._dataset_dir = os.path.join(self._storage_root, 'upload')
        self._file_manager.mkdir(self._dataset_dir)

    @credentials_required
    @use_kwargs({'directory': fields.String(required=False, load_default=None)}, location='query')
    def get(self, directory: Optional[str]):
        """Get files and directories under some directory
        ---
        tags:
          - file
        description: Get files and directories under some directory
        parameters:
        - in: query
          name: directory
          schema:
            type: string
        responses:
          200:
            description: files and directories
            content:
              application/json:
                schema:
                  type: array
                  items:
                    type: object
                    properties:
                      path:
                        type: string
                      size:
                        type: integer
                      mtime:
                        type: integer
                      is_directory:
                        type: boolean
        """
        if directory is None:
            directory = os.path.join(self._storage_root, 'upload')
        if not _is_path_accessible(directory):
            raise NoAccessException('access to this file or directory is not allowed ')
        if not self._file_manager.isdir(directory):
            raise NotFoundException('directory is not exist ')
        files = self._file_manager.ls(directory, include_directory=True)
        return {'data': [dict(file._asdict()) for file in files]}

    @credentials_required
    @use_kwargs(
        {
            'kind':
                fields.String(required=False, load_default=FileType.FILE.value, help='file type'),
            'id':
                fields.String(required=False,
                              load_default='',
                              help='id to locate the file upload location. '
                              'For example, use jobs/job_id for algorithm '
                              'upload for a certain job.'),
            'extract':
                fields.String(
                    required=False, load_default='False', help='If it is necessary to '
                    'extract the uploaded file.'),
        },
        location='form')
    @use_kwargs({'file': fields.List(fields.Field(required=True))}, location='files')
    def post(self, kind: str, id: str, extract: str, file: List[FileStorage]):  # pylint: disable=redefined-builtin
        """Post one or a set of files for upload
        ---
        tags:
          - file
        description: Post one or a set of files for upload
        parameters:
        - in: form
          name: kind
          schema:
            type: string
        - in: form
          name: id
          schema:
            type: string
        - in: form
          name: extract
          schema:
            type: string
        - in: form
          name: file
          schema:
            type: array
            items:
              type: string
              format: binary
          description: list of files in binary format
        responses:
          200:
            description: information of uploaded files
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.UploadedFiles'
        """
        location_id = id
        extract = bool(extract.lower() == 'true')

        upload_files = file
        if extract:
            if len(upload_files) != 1:
                raise InvalidArgumentException('Extraction only allows 1 file each time.')

        # file root dir: {storage_root}/upload_file/{location_id}/
        root_dir = os.path.join(self._file_dir, location_id)
        if kind == FileType.DATASET.value:
            # TODO: clean dataset regularly
            location_id = datetime.utcnow().strftime('%Y%m%d_%H%M%S%f')
            root_dir = os.path.join(self._dataset_dir, location_id)

        response = common_pb2.UploadedFiles()
        # file root dir: {storage_root}/upload_file/{location_id}/{datetime}/
        self._file_manager.mkdir(root_dir)
        for upload_file in upload_files:
            file_content: bytes = upload_file.read()
            if extract:
                secure_tarfile_name = secure_filename(os.path.basename(upload_file.filename))
                target_dir_path = os.path.join(root_dir, secure_tarfile_name.split('.')[0])
                self._file_manager.mkdir(target_dir_path)
                logging.info(f'target_dir_path:{target_dir_path}')
                extension = '.' + secure_tarfile_name.split('.')[-1]
                with tempfile.NamedTemporaryFile(suffix=extension) as f:
                    f.write(file_content)
                    self._file_operator.extract_to(f.name, target_dir_path)
                response.uploaded_files.append(
                    common_pb2.UploadedFile(display_file_name=secure_tarfile_name,
                                            internal_path=target_dir_path,
                                            internal_directory=target_dir_path))
            else:
                # copy the file to the target destination.
                secure_file_name = secure_filename(os.path.basename(upload_file.filename))
                response.uploaded_files.append(
                    self._save_secured_file(root_dir,
                                            display_name=secure_file_name,
                                            secure_file_name=secure_file_name,
                                            content=file_content))
        return {'data': MessageToDict(response, preserving_proto_field_name=True)}

    def _save_secured_file(self, root_folder: str, display_name: str, secure_file_name: str, content: str) -> str:
        """Save the file to fedlearner and return the UI view."""
        self._file_manager.write(os.path.join(root_folder, secure_file_name), content)
        return common_pb2.UploadedFile(display_file_name=display_name,
                                       internal_path=os.path.join(root_folder, secure_file_name),
                                       internal_directory=root_folder)


class ImageApi(Resource):

    def __init__(self):
        self._file_manager = FileManager()

    @use_kwargs({'name': fields.String(required=True, help='image name that you want')}, location='query')
    def get(self, name: str):
        """Get image content by image path
        ---
        tags:
          - file
        description: Get image content by image path
        parameters:
        - in: query
          name: name
          schema:
            type: string
          description: file path of image
        responses:
          200:
            description:
            content:
              image/jpeg:
                type: string
                format: binary
        """
        if not _is_path_accessible(name):
            raise NoAccessException('access to this file or directory is not allowed ')
        if not _is_image_extension(name):
            raise InvalidArgumentException('access to this file or directory is not allowed ')
        content = gfile.GFile(unquote(name), 'rb').read()
        return send_file(BytesIO(content), mimetype='image/jpeg')


def initialize_files_apis(api: Api):
    api.add_resource(FilesApi, '/files')
    api.add_resource(FileApi, '/file')
    api.add_resource(ImageApi, '/image')
