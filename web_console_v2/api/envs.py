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
    KIBANA_ADDRESS = os.environ.get('KIBANA_ADDRESS', 'localhost:32099')
    OPERATOR_LOG_MATCH_PHRASE = os.environ.get(
        'OPERATOR_LOG_MATCH_PHRASE', None)
    # Whether to use the real jwt_required decorator or fake one
    DEBUG = os.environ.get('DEBUG', False)
    ES_INDEX = os.environ.get('ES_INDEX', 'filebeat-*')
    FEDLEARNER_WEBCONSOLE_LOG_DIR = os.environ.get('FEDLEARNER_WEBCONSOLE_LOG_DIR', '.')
