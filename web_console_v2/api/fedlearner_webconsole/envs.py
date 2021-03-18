import os

import pytz


class Envs(object):
    SUPPORT_HDFS = bool(os.environ.get('SUPPORT_HDFS'))
    TZ = pytz.timezone(os.environ.get('TZ', 'UTC'))
    HDFS_SERVER = os.environ.get('HDFS_SERVER', None)
    ES_HOST = os.environ.get('ES_HOST', 'fedlearner-stack-elasticsearch-client')
    ES_PORT = os.environ.get('ES_PORT', 9200)
    ES_USERNAME = os.environ.get('ES_USERNAME', 'elastic')
    ES_PASSWORD = os.environ.get('ES_PASSWORD', 'Fedlearner123')
    KIBANA_SERVICE_HOST_PORT = os.environ.get(
        'KIBANA_SERVICE_HOST_PORT', 'http://fedlearner-stack-kibana:443'
    )
    KIBANA_INGRESS_HOST = os.environ.get('KIBANA_INGRESS_HOST', 'localhost')
    KIBANA_INGRESS_PORT = os.environ.get('KIBANA_INGRESS_PORT', '5601')
