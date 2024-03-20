import os
import json

import pytz


class Envs(object):
    TZ = pytz.timezone(os.environ.get('TZ', 'UTC'))
    ES_HOST = os.environ.get('ES_HOST',
                             'fedlearner-stack-elasticsearch-client')
    ES_READ_HOST = os.environ.get('ES_READ_HOST', ES_HOST)
    ES_PORT = os.environ.get('ES_PORT', 9200)
    ES_USERNAME = os.environ.get('ES_USERNAME', 'elastic')
    ES_PASSWORD = os.environ.get('ES_PASSWORD', 'Fedlearner123')
    # addr to Kibana in pod/cluster
    KIBANA_SERVICE_ADDRESS = os.environ.get(
        'KIBANA_SERVICE_ADDRESS', 'http://fedlearner-stack-kibana:443')
    # addr to Kibana outside cluster, typically comply with port-forward
    KIBANA_ADDRESS = os.environ.get('KIBANA_ADDRESS', 'localhost:1993')
    # What fields are allowed in peer query.
    KIBANA_ALLOWED_FIELDS = set(
        f for f in os.environ.get('KIBANA_ALLOWED_FIELDS', '*').split(',')
        if f)
    OPERATOR_LOG_MATCH_PHRASE = os.environ.get('OPERATOR_LOG_MATCH_PHRASE',
                                               None)
    # Whether to use the real jwt_required decorator or fake one
    DEBUG = os.environ.get('DEBUG', False)
    ES_INDEX = os.environ.get('ES_INDEX', 'filebeat-*')
    # Indicates which k8s namespace fedlearner pods belong to
    K8S_NAMESPACE = os.environ.get('K8S_NAMESPACE', 'default')
    K8S_CONFIG_PATH = os.environ.get('K8S_CONFIG_PATH', None)
    # additional info for k8s.metadata.labels
    K8S_LABEL_INFO = json.loads(os.environ.get('K8S_LABEL_INFO', '{}'))
    FEDLEARNER_WEBCONSOLE_LOG_DIR = os.environ.get(
        'FEDLEARNER_WEBCONSOLE_LOG_DIR', '.')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    # In seconds
    GRPC_CLIENT_TIMEOUT = os.environ.get('GRPC_CLIENT_TIMEOUT', 5)
    # storage filesystem
    STORAGE_ROOT = os.getenv('STORAGE_ROOT', '/data')
    # BASE_DIR
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    # spark on k8s image url
    SPARKAPP_IMAGE_URL = os.getenv('SPARKAPP_IMAGE_URL', None)
    SPARKAPP_FILES_PATH = os.getenv('SPARKAPP_FILES_PATH', None)
    SPARKAPP_VOLUMES = os.getenv('SPARKAPP_VOLUMES', None)
    SPARKAPP_VOLUME_MOUNTS = os.getenv('SPARKAPP_VOLUME_MOUNTS', None)

    # Hooks
    PRE_START_HOOK = os.environ.get('PRE_START_HOOK', None)


class Features(object):
    FEATURE_MODEL_K8S_HOOK = os.getenv('FEATURE_MODEL_K8S_HOOK')
    FEATURE_MODEL_WORKFLOW_HOOK = os.getenv('FEATURE_MODEL_WORKFLOW_HOOK')
    DATA_MODULE_BETA = os.getenv('DATA_MODULE_BETA', None)
