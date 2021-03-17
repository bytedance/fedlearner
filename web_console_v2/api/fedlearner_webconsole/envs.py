import os

import pytz

SUPPORT_HDFS = bool(os.getenv('SUPPORT_HDFS'))
TZ = pytz.timezone(os.environ.get('TZ', 'UTC'))
HDFS_SERVER = os.getenv('HDFS_SERVER', None)
ES_HOST = os.getenv('ES_HOST', 'fedlearner-stack-elasticsearch-client')
ES_PORT = os.getenv('ES_PORT', 9200)
ES_USERNAME = os.getenv('ES_USERNAME', 'elastic')
ES_PASSWORD = os.getenv('ES_PASSWORD', 'Fedlearner123')
KIBANA_SERVICE_HOST_PORT = os.getenv('KIBANA_SERVICE_HOST_PORT',
                                     'http://fedlearner-stack-kibana:443')
KIBANA_INGRESS_HOST = os.getenv('KIBANA_INGRESS_HOST', 'localhost')
KIBANA_INGRESS_PORT = os.getenv('KIBANA_INGRESS_PORT', '5601')
