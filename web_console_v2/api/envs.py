import os

import pytz


class Envs(object):
    TZ = pytz.timezone(os.environ.get('TZ', 'UTC'))
    HDFS_SERVER = os.environ.get('HDFS_SERVER', None)
    ES_HOST = os.environ.get('ES_HOST', 'fedlearner-stack-elasticsearch-client')
    ES_PORT = os.environ.get('ES_PORT', 9200)
    ES_USERNAME = os.environ.get('ES_USERNAME', 'elastic')
    ES_PASSWORD = os.environ.get('ES_PASSWORD', 'Fedlearner123')
    KIBANA_SERVICE_HOST_PORT = os.environ.get(
        'KIBANA_SERVICE_HOST_PORT', 'http://fedlearner-stack-kibana:443'
    )
    KIBANA_ADDRESS = os.environ.get('KIBANA_ADDRESS', 'localhost:1993')
    OPERATOR_LOG_MATCH_PHRASE = os.environ.get(
        'OPERATOR_LOG_MATCH_PHRASE', None)
    # Whether to use the real jwt_required decorator or fake one
    DEBUG = os.environ.get('DEBUG', False)
    ES_INDEX = os.environ.get('ES_INDEX', 'filebeat-*')
    # Indicates which k8s namespace fedlearner pods belong to
    K8S_NAMESPACE = os.environ.get('K8S_NAMESPACE', 'default')
    K8S_CONFIG_PATH = os.environ.get('K8S_CONFIG_PATH', None)
    FEDLEARNER_WEBCONSOLE_LOG_DIR = os.environ.get('FEDLEARNER_WEBCONSOLE_LOG_DIR', '.')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
