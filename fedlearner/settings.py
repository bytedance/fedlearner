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

import os
import logging
from fedlearner.scheduler.db import DBTYPE
from fedlearner.configuration import FEDLEARNER_HOME,\
                                     FEDLEARNER_CONFIG, conf

# pylint: disable=C0301
logging.getLogger().setLevel(logging.INFO)

HEADER = '\n'.join([
    r"——————————————————————————————————————————————————————————————————————————————————",
    r"███████╗███████╗██████╗ ██╗     ███████╗ █████╗ ██████╗ ███╗   ██╗███████╗██████╗ ",
    r"██╔════╝██╔════╝██╔══██╗██║     ██╔════╝██╔══██╗██╔══██╗████╗  ██║██╔════╝██╔══██╗",
    r"█████╗  █████╗  ██║  ██║██║     █████╗  ███████║██████╔╝██╔██╗ ██║█████╗  ██████╔╝",
    r"██╔══╝  ██╔══╝  ██║  ██║██║     ██╔══╝  ██╔══██║██╔══██╗██║╚██╗██║██╔══╝  ██╔══██╗",
    r"██║     ███████╗██████╔╝███████╗███████╗██║  ██║██║  ██║██║ ╚████║███████╗██║  ██║",
    r"╚═╝     ╚══════╝╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝",
    r"——————————————————————————————————————————————————————————————————————————————————",
])

if not conf.sections():
    raise Exception('fedlearner conf [%s] not exist.' % FEDLEARNER_CONFIG)

database_class = conf.get("database", "database_class")
if database_class == "sqlite":
    DATABASE = {
        'db_name': conf.get("database", "database_name"),
        'db_type': DBTYPE.SQLITE,
        'db_path': conf.get("database", "sqlite_path"),
    }
elif database_class == "mysql":
    DATABASE = {
        'db_name': conf.get("database", "database_name"),
        'db_type': DBTYPE.SQLITE,
        'user': conf.get("database", "mysql_user"),
        'passwd': conf.get("database", "mysql_passwd"),
        'host': conf.get("database", "mysql_host"),
        'port': conf.get("database", "mysql_port"),
        'max_connections': conf.get("database", "mysql_max_connections")
    }
else:
    raise Exception(
        'database do not support databases other than mysql and sqlite')

STDERR_PATH = os.path.join(FEDLEARNER_HOME, 'fedlearner_scheduler.err')
STDOUT_PATH = os.path.join(FEDLEARNER_HOME, 'fedlearner_scheduler.out')
LOG_PATH = os.path.join(FEDLEARNER_HOME, 'fedlearner_scheduler.log')
PID_FILE = os.path.join(FEDLEARNER_HOME, 'fedlearner.pid')

LOGGING_LEVEL = logging.INFO
LOG_FORMAT = conf.get('logging', 'log_format')
SIMPLE_LOG_FORMAT = conf.get('logging', 'simple_log_format')
'''
    FedLearner kubernetes config.
'''
FL_CRD_GROUP = conf.get('kubernetes', 'crd_group')
FL_CRD_VERSION = conf.get('kubernetes', 'crd_version')
FL_CRD_PLURAL = conf.get('kubernetes', 'crd_plural')
FL_KIND = conf.get('kubernetes', 'crd_kind')

K8S_NAMESPACE = conf.get('kubernetes', 'namespace')
K8S_TOKEN_PATH = conf.get('kubernetes', 'token_file')
K8S_CAS_PATH = conf.get('kubernetes', 'cert_file')
KUBERNETES_SERVICE_HOST = conf.get('kubernetes', 'server_host')
KUBERNETES_SERVICE_PORT = conf.get('kubernetes', 'server_port')
'''
    FedLearner Worker Config.
'''
CHECKPOINT_PATH_PREFIX = conf.get('train', 'checkpoint_path')
EXPORT_PATH_PREFIX = conf.get('train', 'export_path')
