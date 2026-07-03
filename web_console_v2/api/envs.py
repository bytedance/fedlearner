import os
import json

import pytz


def _parse_bool_env(name: str, default: bool = False) -> bool:
    """Parse an environment variable as a strict boolean.

    Motivation: `os.environ.get('DEBUG', False)` returns the raw string when
    the variable is set, so `DEBUG=False`, `DEBUG=0`, or `DEBUG=no` all
    evaluate to truthy in a boolean context, silently bypassing auth guards
    that key off `Envs.DEBUG`. Any string other than the well-known truthy
    values below is treated as False.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ('1', 'true', 't', 'yes', 'y', 'on')


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
    # Whether to use the real jwt_required decorator or fake one.
    # Parsed as a strict boolean so misconfigurations like DEBUG=False (a
    # non-empty string) do not silently disable JWT enforcement.
    DEBUG = _parse_bool_env('DEBUG', default=False)
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
