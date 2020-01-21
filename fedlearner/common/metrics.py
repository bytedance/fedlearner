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
"""Metrics logger""" 

import time
import os
import logging
from influxdb import InfluxDBClient

_metrics_client = None


class MetricsClient(object):
    def __init__(self, host, port, user, passwd, db):
        self._client = InfluxDBClient(host, port, user, passwd, db)

    def emit(self, metrics_name, tagkv, fields):
        emit_body = []
        emit_item = {
            "measurement": metrics_name,
            "tags": tagkv,
            "time": int(round(time.time() * 1000)),
            "fields": fields
        }

        emit_body.append(emit_item)
        logging.debug('Metrics Client emit emit body %s', str(emit_body))
        return self._client.write_points(emit_body)


def config(host=None, port=None, user=None, passwd=None, db=None):
    global _metrics_client  # pylint: disable=global-statement
    if not host:
        host = os.environ.get('INFLUXDB_HOST')
    if not port:
        port = os.environ.get('INFLUXDB_PORT')
    if not user:
        user = os.environ.get('INFLUXDB_USER')
    if not passwd:
        passwd = os.environ.get('INFLUXDB_PASSWD')
    if not db:
        db = os.environ.get('INFLUXDB_DB')

    _metrics_client = MetricsClient(host=host,
                                    port=port,
                                    user=user,
                                    passwd=passwd,
                                    db=db)


def emit(metrics_name, tagkv, fields):
    if not _metrics_client:
        config()

    return _metrics_client.emit(metrics_name, tagkv, fields)
