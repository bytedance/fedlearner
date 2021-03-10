import os

import pytz

SUPPORT_HDFS = bool(os.getenv('SUPPORT_HDFS'))
TZ = pytz.timezone(os.environ.get('TZ', 'UTC'))
