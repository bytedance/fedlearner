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

import datetime
import logging
import os
import threading
import time
from collections import defaultdict
from functools import wraps

import pytz
from elasticsearch import Elasticsearch, helpers

# use to constrain ES document size, please modify with precaution to minimize
# disk space
ES_MAPPING = {
    "dynamic": True,
    "properties": {
        "name": {
            "type": "keyword"
        },
        "value": {
            "type": "float"
        },
        "date_time": {
            "format": "yyyy-MM-dd'T'HH:mm:ss.SSSSSSZ",
            "type": "date"
        },
        "tags": {
            "properties": {
                "partition": {
                    "type": "byte"
                },
                "original": {
                    "type": "byte"
                },
                "joined": {
                    "type": "byte"
                },
                "fake": {
                    "type": "byte"
                },
                "label": {
                    "ignore_above": 32,
                    "type": "keyword"
                },
                "type": {
                    "ignore_above": 256,
                    "type": "keyword"
                },
                "application_id": {
                    "ignore_above": 128,
                    "type": "keyword"
                },
                "data_source_name": {
                    "ignore_above": 128,
                    "type": "keyword"
                },
                "joiner_name": {
                    "ignore_above": 32,
                    "type": "keyword"
                },
                "role": {
                    "ignore_above": 32,
                    "type": "keyword"
                },
                "process_time": {
                    "format": "yyyy-MM-dd'T'HH:mm:ss.SSSSSSZ",
                    "type": "date"
                },
                "event_time": {
                    "format": "yyyy-MM-dd'T'HH:mm:ss.SSSSSSZ",
                    "type": "date"
                }
            }
        }
    }
}
ES_INDEX = 'metrics_v2-{}'


class Handler(object):
    def __init__(self, name):
        self._name = name

    def emit(self, name, value, tags=None):
        """
        Do whatever it takes to actually log the specified logging record.

        This version is intended to be implemented by subclasses and so
        raises a NotImplementedError.
        """
        raise NotImplementedError('emit must be implemented '
                                  'by Handler subclasses')

    def get_name(self):
        return self._name


class LoggingHandler(Handler):
    def __init__(self):
        super(LoggingHandler, self).__init__('logging')

    def emit(self, name, value, tags=None):
        logging.debug('[metrics] name[%s] value[%s] tags[%s]',
                      name, value, str(tags))


class ElasticSearchHandler(Handler):
    def __init__(self, ip, port):
        super(ElasticSearchHandler, self).__init__('elasticsearch')
        self._es = Elasticsearch([ip], port=port)
        self._tz = pytz.timezone('Asia/Shanghai')
        self._emit_batch = defaultdict(list)
        index = ES_INDEX.format(
            datetime.datetime.now(tz=self._tz).strftime('%Y.%m.%d')
        )
        if not self._es.indices.exists(index=index):
            self._es.indices.create(index=index, body={'mappings': ES_MAPPING})
        else:
            self._es.indices.put_mapping(index=index, body=ES_MAPPING)

    def emit(self, name, value, tags=None):
        if tags is None:
            tags = {}
        date = datetime.datetime.now(tz=self._tz).strftime('%Y.%m.%d')
        index = ES_INDEX.format(date)
        if not self._es.indices.exists(index=index):
            self._es.indices.create(index=index, body={'mappings': ES_MAPPING})
            for idx, actions in self._emit_batch.items():
                if not idx.endswith(date):
                    helpers.bulk(self._es, actions)
                    self._emit_batch.pop(idx)
        application_id = os.environ.get('APPLICATION_ID', '')
        if application_id:
            tags['application_id'] = str(application_id)
        action = {
            '_index': index,
            '_source': {
                "name": name,
                "value": value,
                "tags": tags,
            }
        }
        self._emit_batch[index].append(action)
        if len(self._emit_batch[index]) == 1000:
            logging.info('METRICS: Logging 1000 entries to ES.')
            helpers.bulk(self._es, self._emit_batch)
            self._emit_batch.pop(index)


class Metrics(object):
    def __init__(self):
        self.handlers = []
        self._lock = threading.RLock()
        self.handler_initialized = False

    def init_handlers(self):
        with self._lock:
            if self.handler_initialized:
                return
            logging_handler = LoggingHandler()
            self.add_handler(logging_handler)
            es_host = os.environ.get('ES_HOST', None)
            es_port = os.environ.get('ES_PORT', None)
            if es_host is not None and es_port is not None:
                es_handler = ElasticSearchHandler(es_host, es_port)
                self.add_handler(es_handler)
            self.handler_initialized = True

    def add_handler(self, hdlr):
        """
        Add the specified handler to this logger.
        """
        with self._lock:
            if hdlr not in self.handlers:
                self.handlers.append(hdlr)

    def remove_handler(self, hdlr):
        """
        Remove the specified handler from this logger.
        """
        with self._lock:
            if hdlr in self.handlers:
                self.handlers.remove(hdlr)

    def emit(self, name, value, tags=None, metrics_type=None):
        self.init_handlers()
        if not self.handlers or len(self.handlers) == 0:
            print('no handlers. do nothing.')
            return

        for hdlr in self.handlers:
            try:
                hdlr.emit(name, value, tags, metrics_type)
            except Exception as e:  # pylint: disable=broad-except
                print('handler [%s] emit failed. [%s]' %
                      (hdlr.get_name(), repr(e)))


_metrics_client = Metrics()


def emit(name, value, tags=None):
    _metrics_client.emit(name, value, tags)


# Should use emit in new codes. Below are compatibility measures
emit_counter = emit
emit_store = emit
emit_timer = emit


def timer(func_name, tags=None):
    def func_wrapper(func):
        @wraps(func)
        def return_wrapper(*args, **kwargs):
            time_start = time.time()
            result = func(*args, **kwargs)
            time_end = time.time()
            time_spend = time_end - time_start
            emit(func_name, time_spend, tags)
            return result

        return return_wrapper

    return func_wrapper
