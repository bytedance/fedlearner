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

import time
import os
import logging
import socket
from influxdb import InfluxDBClient

_metrics_client = None
hostname = socket.gethostname()
local_ip = socket.gethostbyname(hostname)

class MetricsClient(object):
    def __init__(self, host, port, user, passwd, db):
        self._client = InfluxDBClient(host, port, user, passwd, db)

    def emit(self, metrics_name, tagkv, fields, time=None):
        emit_body = []
        emit_item = {
            "measurement": metrics_name,
            "tags": tagkv,
            "time": time if time else int(round(time.time() * 1000)),
            "fields": fields}

        emit_body.append(emit_item)
        logging.debug('Metrics Client emit emit body %s', str(emit_body))
        return self._client.write_points(emit_body)


def config(use_mock_cli=False, host=None, port=None, user=None, 
           passwd=None, db=None):
    global _metrics_client  # pylint: disable=global-statement
    if not host:
        host = os.environ.get('INFLUXDB_HOST', None)
    if not port:
        port = os.environ.get('INFLUXDB_PORT', None)
    if not user:
        user = os.environ.get('INFLUXDB_USER', None)
    if not passwd:
        passwd = os.environ.get('INFLUXDB_PASSWD', None)
    if not db:
        db = os.environ.get('INFLUXDB_DB', None)
    
    if not host or not port or not user or not passwd or not db:
        return False

    _metrics_client = MetricsClient(host=host,
                                    port=port,
                                    user=user,
                                    passwd=passwd,
                                    db=db)
    return True

def emit(metrics_name, fields, tagkv={}):
    if not _metrics_client:
        if not config():
            return None
    
    if not isinstance(fields, dict):
        raise TypeError('Metrics fields only support dict')

    if not isinstance(tagkv, dict):
        raise TypeError('Metrics tagkv only support dict')

    if 'host' not in tagkv:
        tagkv['host'] = local_ip
  
    return _metrics_client.emit(metrics_name, tagkv, fields)
