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

import atexit
import datetime
import logging
import os
import threading
import time
from collections import defaultdict
from functools import wraps

import elasticsearch as es7
import elasticsearch6 as es6
import pytz
from elasticsearch import helpers

# use to constrain ES document size, please modify WITH PRECAUTION to minimize
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
            "format": "strict_date_hour_minute_second",
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
                    "format": "strict_date_hour_minute_second",
                    "type": "date"
                },
                "event_time": {
                    "format": "strict_date_hour_minute_second",
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

    def flush(self):
        pass


class LoggingHandler(Handler):
    def __init__(self):
        super(LoggingHandler, self).__init__('logging')

    def emit(self, name, value, tags=None):
        logging.debug('[metrics] name[%s] value[%s] tags[%s]',
                      name, value, str(tags))


class ElasticSearchHandler(Handler):
    """
    Emit documents to ElasticSearch
    """
    def __init__(self, ip, port):
        super(ElasticSearchHandler, self).__init__('elasticsearch')
        self._es = es7.Elasticsearch([ip], port=port)
        self._version = int(self._es.info()['version']['number'].split('.')[0])
        # ES 6.8 has differences in mapping initialization compared to ES 7.6
        if self._version == 6:
            self._es = es6.Elasticsearch([ip], port=port)
        # suppress ES logger
        logger = logging.getLogger('elasticsearch')
        logger.setLevel(logging.CRITICAL)
        logger.addHandler(logging.FileHandler('indexer.log'))
        self._tz = pytz.timezone('Asia/Shanghai')
        self._emit_batch = defaultdict(list)
        self._lock = threading.RLock()
        index = ES_INDEX.format(
            datetime.datetime.now(tz=self._tz).strftime('%Y.%m.%d')
        )
        if not self._es.indices.exists(index=index):
            self._create_index(index)
        else:
            # if index exists, put mapping in case mapping is modified.
            # compatibility measures for mapping changes
            if self._version == 7:
                self._es.indices.put_mapping(index=index, body=ES_MAPPING)
            else:
                self._es.indices.put_mapping(index=index, body=ES_MAPPING,
                                             doc_type='_doc')

    def emit(self, name, value, tags=None):
        if tags is None:
            tags = {}
        date = datetime.datetime.now(tz=self._tz).strftime('%Y.%m.%d')
        index = ES_INDEX.format(date)
        # if not exists, create one, and check if existing documents are
        # out-dated. if so, emit them and pop
        with self._lock:
            if not self._es.indices.exists(index=index):
                self._create_index(index)
                for idx in self._emit_batch.keys():
                    if not idx.endswith(date):
                        self._emit_and_pop(idx)
        application_id = os.environ.get('APPLICATION_ID', '')
        if application_id:
            tags['application_id'] = str(application_id)
        action = {
            # _index = which index to emit to, _source = document
            '_index': index,
            '_source': {
                "name": name,
                "value": value,
                "tags": tags,
                "date_time": datetime.datetime.now(
                    tz=self._tz).isoformat(timespec='seconds')
            }
        }
        if self._version == 6:
            action['_type'] = '_doc'
        self._emit_batch[index].append(action)
        # emit and pop when there are 1000 documents to emit
        with self._lock:
            if len(self._emit_batch[index]) >= 1000:
                logging.info('METRICS: Emitting 1000 documents to ES.')
                self._emit_and_pop(index)

    def flush(self):
        # emit and pop all existing documents
        with self._lock:
            for index in self._emit_batch.keys():
                self._emit_and_pop(index)

    def _create_index(self, index):
        """
        Args:
            index: ES index name.

        Creates an index on ES, with compatibility with ES 6 and ES 7.

        """
        with self._lock:
            if self._version == 6:
                body = {'mappings': {'_doc': ES_MAPPING}}
            else:
                body = {'mappings': ES_MAPPING}
            self._es.indices.create(index=index, body=body)

    def _emit_and_pop(self, index):
        with self._lock:
            helpers.bulk(self._es, self._emit_batch[index])
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

    def emit(self, name, value, tags=None):
        self.init_handlers()
        if not self.handlers or len(self.handlers) == 0:
            logging.info('No handlers. Not emitting.')
            return

        for hdlr in self.handlers:
            try:
                hdlr.emit(name, value, tags)
            except Exception as e:  # pylint: disable=broad-except
                logging.warning('Handler [%s] emit failed. Error repr: [%s]',
                                hdlr.get_name(), repr(e))

    def flush_handler(self):
        for hdlr in self.handlers:
            try:
                hdlr.flush()
            except Exception as e:  # pylint: disable=broad-except
                logging.warning('Handler [%s] flush failed. Some metrics might '
                                'not be emitted. Error repr: %s',
                                hdlr.get_name(), repr(e))


_metrics_client = Metrics()
atexit.register(_metrics_client.flush_handler)


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
