import os
from fedlearner.scheduler.db import DBTYPE

# pylint: disable=C0301

#DATABASE = {
#    'db_type': DBTYPE.MYSQL,
#    'db_name': 'bytefl',
#    'user': 'root',
#    'passwd': 'root',
#    'host': '127.0.0.1',
#    'port': 3306,
#    'max_connections': 100,
#    'stale_timeout': 30}

DATABASE = {
    'db_name': 'bytefl',
    'db_type': DBTYPE.SQLITE,
    'db_path': 'bytefl.db'
}

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

FEDLEARNER_HOME = './'

STDERR_PATH = os.path.join(FEDLEARNER_HOME, 'fedlearner_scheduler.err')
STDOUT_PATH = os.path.join(FEDLEARNER_HOME, 'fedlearner_scheduler.out')
LOG_PATH = os.path.join(FEDLEARNER_HOME, 'fedlearner_scheduler.log')
PID_FILE = os.path.join(FEDLEARNER_HOME, 'fedlearner.pid')

LOGGING_LEVEL = 'DEBUG'
SIMPLE_LOG_FORMAT = '%%(asctime)s %%(levelname)s - %%(message)s'
'''
    FedLearner kubernetes config.
'''
FL_CRD_GROUP = 'fedlearner.k8s.io'
FL_CRD_VERSION = 'v1alpha1'  # str | The custom resource's plural name.
FL_CRD_PLURAL = 'flapps'  # str | The custom resource's plural name.
FL_KIND = 'FLApp'

K8S_TOKEN_PATH = '/data00/home/lilongyijia.dev/github.com/fedlearner_env/aliyun.token'
K8S_CAS_PATH = '/data00/home/lilongyijia.dev/github.com/fedlearner_env/aliyun.ca.crt'
KUBERNETES_SERVICE_HOST = '10.108.20.135'
KUBERNETES_SERVICE_PORT = '6443'
'''
    FedLearner proxy on public network communication.
'''
PROXY_ADDRESS = ''
'''
    FedLearner Worker Config.
'''
CHECKPOINT_PATH_PREFIX = '.'
EXPORT_PATH_PREFIX = '.'
