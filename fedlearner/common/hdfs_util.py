# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
from typing import Optional, Dict, List
import json
import logging
import re

import fsspec
from urllib.parse import urlparse
from hdfs.ext.kerberos import KerberosClient
from collections import namedtuple

KEYTAB_FILE_ENV = "KRB5CCNAME"
DEFAULT_SCHEME_TYPE = 'file'
KRB_FILE_PATH = 'KRB_FILE_PATH'
STORAGE_ROOT_PATH = 'MT_HDFS_ROOT_PATH'
HADOOP_SUPPORTED_FILE_PREFIXES = r'\.+\/|^\/|^viewfs:\/\/'
MT_HADOOP_SUPPORTED_FILE_PREFIXES = 'viewfs:'
client = KerberosClient(url='http://data-httpfs.vip.sankuai.com:15000')
File = namedtuple('File', ['path', 'size', 'is_directory'])


def init_env():
    if KEYTAB_FILE_ENV not in os.environ:
        os.environ[KEYTAB_FILE_ENV] = os.environ[KRB_FILE_PATH]
    logging.info(f'Kerberos env : {os.environ[KEYTAB_FILE_ENV]}')


def get_root_path():
    return os.environ[STORAGE_ROOT_PATH]


def parse_to_mt_path(path: str):
    url_parser = urlparse(path)
    path = url_parser.path
    if path.startswith('/'):
        if path.startswith('/data'):
            path = path[5:]
        if path.startswith(_get_path_no_protocol(get_root_path())):
            return f'{MT_HADOOP_SUPPORTED_FILE_PREFIXES}//{path}'
        return f'{get_root_path()}{path}'
    else:
        if path.startswith('data'):
            path = path[4:]
        if path.startswith(_get_path_no_protocol(get_root_path())):
            return f'{MT_HADOOP_SUPPORTED_FILE_PREFIXES}//{path}'
        return f'{get_root_path()}/{path}'


def upload_to_mt_hdfs(path: str):
    fs = fsspec.filesystem('file')
    if fs.isdir(path):
        mt_path = parse_to_mt_path(remove_last_path(path))
    else:
        mt_path = parse_to_mt_path(path)
    logging.info(f'upload local path : {path} to mt hdfs path : {mt_path}')
    upload(path, mt_path)


def _get_path_no_protocol(path: str):
    return re.sub(r'^\w+://', '', path)


def mkdir(path: str) -> bool:
    if path.endswith("*"):
        path = remove_last_path(path)
    if is_mt_hdfs(path):
        if not exists(path):
            return client.makedirs(_get_path_no_protocol(path))
    elif not fsspec.get_mapper(path).fs.exists(path):
        return fsspec.get_mapper(path).fs.mkdir(path)
    return True


def is_mt_hdfs(path: str) -> bool:
    return path.startswith(MT_HADOOP_SUPPORTED_FILE_PREFIXES)


def mt_hadoop_download(hdfs_path: str, is_dir=True) -> str:
    if is_mt_hdfs(hdfs_path):
        local_input_batch_path = get_local_temp_path(hdfs_path)
        logging.info(f'download hdfs file : {hdfs_path}  to local path : {local_input_batch_path}')
        local_path = remove_last_path(local_input_batch_path)
        mkdir(local_path)
        if is_dir:
            download(local_path, hdfs_path)
        elif local_input_batch_path.endswith("*"):
            local_path = remove_last_path(local_path)
            hdfs_path = remove_last_path(hdfs_path)
            download(local_path, hdfs_path)
        else:
            download(local_input_batch_path, hdfs_path)
        return local_input_batch_path
    else:
        return hdfs_path


def remove_last_path(path: str) -> str:
    # 如果路径以 "/" 结尾，先去掉末尾的 "/"
    if path.endswith("/"):
        path = path[:-1]
    new_path = "/".join(path.split("/")[:-1])
    # 如果新的路径为空，说明原路径只有一层，直接返回 "/"
    if not new_path:
        return "/"
    # 如果原路径以 "//" 结尾，新路径也要以 "//" 结尾
    if path.endswith("//"):
        new_path += "/"
    return new_path


def exists(path: str) -> bool:
    if is_mt_hdfs(path):
        info = client.status(_get_path_no_protocol(path), False)
        return info is not None
    else:
        return fsspec.get_mapper(path).fs.exists(path)


def isdir(path: str) -> bool:
    info = client.status(_get_path_no_protocol(path), False)
    if info and info['type'] == 'DIRECTORY':
        return True
    return False


def download(local_path: str, hdfs_path: str) -> bool:
    try:
        logging.info(f'real download hdfs file : {hdfs_path}  to local path : {local_path}')
        client.download(_get_path_no_protocol(hdfs_path), _get_path_no_protocol(local_path), overwrite=True)
        return True
    except Exception as e:
        logging.error(f'download file error : {str(e)}')
        return False


def upload(source: str, destination: str) -> bool:
    try:
        client.upload(_get_path_no_protocol(destination), _get_path_no_protocol(source), overwrite=True)
        return True
    except Exception as e:
        logging.error(f'upload file error : {str(e)}')
        return False


def get_local_temp_path(path: str) -> str:
    if not path.startswith(DEFAULT_SCHEME_TYPE):
        return f'{DEFAULT_SCHEME_TYPE}:///data{_get_path_no_protocol(path)}'
    return path
