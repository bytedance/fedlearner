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
import re
import secrets
from typing import Optional
from urllib.parse import unquote
from google.protobuf.json_format import Parse, ParseError

import pytz

from fedlearner_webconsole.proto import setting_pb2
from fedlearner_webconsole.utils.const import API_VERSION

# SQLALCHEMY_DATABASE_URI pattern dialect+driver://username:password@host:port/database
_SQLALCHEMY_DATABASE_URI_PATTERN = re.compile(
    r'^(?P<dialect>[^+:]+)(\+(?P<driver>[^:]+))?://'
    r'((?P<username>[^:@]+)?:(?P<password>[^@]+)?@((?P<host>[^:/]+)(:(?P<port>[0-9]+))?)?)?'
    r'/(?P<database>[^?]+)?')

# Limit one thread used by OpenBLAS to avoid many threads that hang.
# ref: https://stackoverflow.com/questions/30791550/limit-number-of-threads-in-numpy
os.environ['OMP_NUM_THREADS'] = '1'


class Envs(object):
    SERVER_HOST = os.environ.get('SERVER_HOST', 'http://localhost:666/')
    TZ = pytz.timezone(os.environ.get('TZ', 'UTC'))
    ES_HOST = os.environ.get('ES_HOST', 'fedlearner-stack-elasticsearch-client')
    ES_PORT = os.environ.get('ES_PORT', 9200)
    ES_USERNAME = os.environ.get('ES_USERNAME', 'elastic')
    ES_PASSWORD = os.environ.get('ES_PASSWORD', 'Fedlearner123')
    # apm-server service address which is used to collect trace and custom metrics
    APM_SERVER_ENDPOINT = os.environ.get('APM_SERVER_ENDPOINT', 'http://fedlearner-stack-apm-server:8200')
    # addr to Kibana in pod/cluster
    KIBANA_SERVICE_ADDRESS = os.environ.get('KIBANA_SERVICE_ADDRESS', 'http://fedlearner-stack-kibana:443')
    # addr to Kibana outside cluster, typically comply with port-forward
    KIBANA_ADDRESS = os.environ.get('KIBANA_ADDRESS', 'localhost:1993')
    # What fields are allowed in peer query.
    KIBANA_ALLOWED_FIELDS = set(f for f in os.environ.get('KIBANA_ALLOWED_FIELDS', '*').split(',') if f)
    # Kibana dashboard list of dashboard information consist of [`name`, `uuid`] in json format
    KIBANA_DASHBOARD_LIST = os.environ.get('KIBANA_DASHBOARD_LIST', '[]')
    OPERATOR_LOG_MATCH_PHRASE = os.environ.get('OPERATOR_LOG_MATCH_PHRASE', None)
    # Whether to use the real credentials_required decorator or fake one
    DEBUG = os.environ.get('DEBUG', False)
    SWAGGER_URL_PREFIX = os.environ.get('SWAGGER_URL_PREFIX', API_VERSION)
    # grpc client can use this GRPC_SERVER_URL when DEBUG is True
    GRPC_SERVER_URL = os.environ.get('GRPC_SERVER_URL', None)
    GRPC_LISTEN_PORT = int(os.environ.get('GRPC_LISTEN_PORT', 1990))
    RESTFUL_LISTEN_PORT = int(os.environ.get('RESTFUL_LISTEN_PORT', 1991))
    # composer server listen port for health checking service
    COMPOSER_LISTEN_PORT = int(os.environ.get('COMPOSER_LISTEN_PORT', 1992))
    ES_INDEX = os.environ.get('ES_INDEX', 'filebeat-*')
    # Indicates which k8s namespace fedlearner pods belong to
    K8S_NAMESPACE = os.environ.get('K8S_NAMESPACE', 'default')
    K8S_CONFIG_PATH = os.environ.get('K8S_CONFIG_PATH', None)
    K8S_HOOK_MODULE_PATH = os.environ.get('K8S_HOOK_MODULE_PATH', None)
    FEDLEARNER_WEBCONSOLE_LOG_DIR = os.environ.get('FEDLEARNER_WEBCONSOLE_LOG_DIR', '.')
    LOG_LEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    CLUSTER = os.environ.get('CLUSTER', 'default')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', secrets.token_urlsafe(64))
    # In seconds
    GRPC_CLIENT_TIMEOUT = int(os.environ.get('GRPC_CLIENT_TIMEOUT', 5))
    # In seconds
    GRPC_STREAM_CLIENT_TIMEOUT = int(os.environ.get('GRPC_STREAM_CLIENT_TIMEOUT', 10))
    # storage filesystem
    STORAGE_ROOT = os.getenv('STORAGE_ROOT', '/data')
    # BASE_DIR
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    # Hooks
    PRE_START_HOOK = os.environ.get('PRE_START_HOOK', None)

    # Flags
    FLAGS = os.environ.get('FLAGS', '{}')

    # Third party SSO, see the example in test_sso.json
    SSO_INFOS = os.environ.get('SSO_INFOS', '[]')

    # Audit module storage setting
    AUDIT_STORAGE = os.environ.get('AUDIT_STORAGE', 'db')

    # system info, include name, domain name, ip
    SYSTEM_INFO = os.environ.get('SYSTEM_INFO', '{}')

    CUSTOMIZED_FILE_MANAGER = os.environ.get('CUSTOMIZED_FILE_MANAGER')
    SCHEDULER_POLLING_INTERVAL = os.environ.get('FEDLEARNER_WEBCONSOLE_POLLING_INTERVAL', 60)

    # DB related
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    DB_HOST = os.environ.get('DB_HOST')
    DB_PORT = os.environ.get('DB_PORT')
    DB_DATABASE = os.environ.get('DB_DATABASE')
    DB_USERNAME = os.environ.get('DB_USERNAME')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')

    # Fedlearner related
    KVSTORE_TYPE = os.environ.get('KVSTORE_TYPE')
    ETCD_NAME = os.environ.get('ETCD_NAME')
    ETCD_ADDR = os.environ.get('ETCD_ADDR')
    ETCD_BASE_DIR = os.environ.get('ETCD_BASE_DIR')
    ROBOT_USERNAME = os.environ.get('ROBOT_USERNAME')
    ROBOT_PWD = os.environ.get('ROBOT_PWD')
    WEB_CONSOLE_V2_ENDPOINT = os.environ.get('WEB_CONSOLE_V2_ENDPOINT')
    HADOOP_HOME = os.environ.get('HADOOP_HOME')
    JAVA_HOME = os.environ.get('JAVA_HOME')

    @staticmethod
    def _decode_url_codec(codec: str) -> str:
        if not codec:
            return codec
        return unquote(codec)

    @classmethod
    def _check_db_envs(cls) -> Optional[str]:
        # Checks if DB related envs are matched
        if cls.SQLALCHEMY_DATABASE_URI:
            matches = _SQLALCHEMY_DATABASE_URI_PATTERN.match(cls.SQLALCHEMY_DATABASE_URI)
            if not matches:
                return 'Invalid SQLALCHEMY_DATABASE_URI'
            if cls.DB_HOST:
                # Other DB_* envs should be set together
                db_host = cls._decode_url_codec(matches.group('host'))
                if cls.DB_HOST != db_host:
                    return 'DB_HOST does not match'
                db_port = cls._decode_url_codec(matches.group('port'))
                if cls.DB_PORT != db_port:
                    return 'DB_PORT does not match'
                db_database = cls._decode_url_codec(matches.group('database'))
                if cls.DB_DATABASE != db_database:
                    return 'DB_DATABASQLALCHEMY_DATABASE_URISE does not match'
                db_username = cls._decode_url_codec(matches.group('username'))
                if cls.DB_USERNAME != db_username:
                    return 'DB_USERNAME does not match'
                db_password = cls._decode_url_codec(matches.group('password'))
                if cls.DB_PASSWORD != db_password:
                    return 'DB_PASSWORD does not match'
        return None

    @classmethod
    def _check_system_info_envs(cls) -> Optional[str]:
        try:
            system_info = Parse(Envs.SYSTEM_INFO, setting_pb2.SystemInfo())
        except ParseError as err:
            return f'failed to parse SYSTEM_INFO {err}'
        if system_info.domain_name == '' or system_info.name == '':
            return 'domain_name or name is not set into SYSTEM_INFO'
        return None

    @classmethod
    def check(cls) -> Optional[str]:
        db_envs_error = cls._check_db_envs()
        if db_envs_error:
            return db_envs_error
        system_info_envs_error = cls._check_system_info_envs()
        if system_info_envs_error:
            return system_info_envs_error
        return None
