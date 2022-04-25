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
import json
import os
import threading
import time
import logging
from functools import wraps

import elasticsearch as es7
import elasticsearch6 as es6
import pytz
from elasticsearch import helpers as helpers7
from elasticsearch6 import helpers as helpers6

from .common import Config, INDEX_NAME, INDEX_TYPE, get_es_template

from . import fl_logging
from .metric_collector import MetricCollector


class Handler(object):
    def __init__(self, name):
        self._name = name

    def emit(self, name, value, tags=None, index_type='metrics'):
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

    def emit(self, name, value, tags=None, index_type='metrics'):
        fl_logging.debug('[metrics] name[%s] value[%s] tags[%s]',
                      name, value, str(tags))


class ElasticSearchHandler(Handler):
    """
    Emit documents to ElasticSearch
    """

    def __init__(self, ip, port):
        super(ElasticSearchHandler, self).__init__('elasticsearch')
        self._es = es7.Elasticsearch([ip], port=port,
                                     http_auth=(Config.ES_USERNAME,
                                                Config.ES_PASSWORD))
        self._helpers = helpers7
        self._version = int(self._es.info()['version']['number'].split('.')[0])
        # ES 6.8 has differences in APIs compared to ES 7.6,
        # These `put_template`s is supposed to be done during deployment, here
        # is for old clients.
        if self._version == 6:
            self._es = es6.Elasticsearch([ip], port=port)
            self._helpers = helpers6
            for index_type, index_name in INDEX_NAME.items():
                if not self._es.indices.exists_template(
                    '{}-template'.format(index_name)
                ):
                    self._create_template_and_index(index_type)
        # suppress ES logger
        logging.getLogger('elasticsearch').setLevel(logging.CRITICAL)
        self._emit_batch = []
        self._batch_size = Config.ES_BATCH_SIZE
        self._lock = threading.RLock()

    def emit(self, name, value, tags=None, index_type='metrics'):
        assert index_type in INDEX_TYPE
        if tags is None:
            tags = {}
        document = self._produce_document(name, value, tags, index_type)
        if not Config.METRICS_TO_STDOUT:
            # if filebeat not yet refurbished, directly emit to ES
            action = {'_index': INDEX_NAME[index_type],
                      '_source': document}
            if self._version == 6:
                action['_type'] = '_doc'
            with self._lock:
                # emit when there are enough documents
                self._emit_batch.append(action)
                if len(self._emit_batch) >= self._batch_size:
                    self.flush()
        else:
            # if filebeat refurbished,
            # print to std out and use filebeat to ship to ES
            document['index_type__'] = index_type
            print(json.dumps(document))

    def flush(self):
        emit_batch = []
        with self._lock:
            if self._emit_batch:
                emit_batch = self._emit_batch
                self._emit_batch = []
        if emit_batch:
            fl_logging.info('Emitting %d documents to ES', len(emit_batch))
            self._helpers.bulk(self._es, emit_batch)

    @staticmethod
    def _produce_document(name, value, tags, index_type):
        application_id = os.environ.get('APPLICATION_ID', '')
        if application_id:
            tags['application_id'] = str(application_id)
        if index_type == 'metrics':
            tags['process_time'] = datetime.datetime.now(tz=pytz.utc) \
                .isoformat(timespec='microseconds')
            document = {
                "name": name,
                "value": value,
                "tags": tags
            }
        else:
            document = {
                "tags": tags
            }
        return document

    def _create_template_and_index(self, index_type):
        """
        Args:
            index_type: ES index type.

        Creates a template and an index on ES.

        """
        assert index_type in INDEX_TYPE
        self._es.indices.put_template(
            name='{}-template'.format(INDEX_NAME[index_type]),
            body=get_es_template(index_type, self._version)
        )
        try:
            self._es.indices.create(index=INDEX_NAME[index_type])
            return
        # index may have been created by other jobs
        except (es6.exceptions.RequestError, es7.exceptions.RequestError) as e:
            # if due to other reasons, re-raise exception
            if e.info['error']['type'] != 'resource_already_exists_exception':
                raise e


class Metrics(object):
    def __init__(self):
        self.handlers = []
        self._lock = threading.RLock()
        self.handler_initialized = False
        atexit.register(self.flush_handler)

    def init_handlers(self):
        with self._lock:
            if self.handler_initialized:
                return
            logging_handler = LoggingHandler()
            self.add_handler(logging_handler)
            es_host = os.environ.get('ES_HOST', '')
            es_port = os.environ.get('ES_PORT', '')
            if es_host and es_port:
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

    def emit(self, name, value, tags=None, index_type='metrics'):
        self.init_handlers()
        if not self.handlers or len(self.handlers) == 0:
            fl_logging.info('No handlers. Not emitting.')
            return

        for hdlr in self.handlers:
            try:
                hdlr.emit(name, value, tags, index_type)
            except Exception as e:  # pylint: disable=broad-except
                fl_logging.warning('Handler [%s] emit failed. Error repr: [%s]',
                                hdlr.get_name(), repr(e))

    def flush_handler(self):
        for hdlr in self.handlers:
            try:
                hdlr.flush()
            except Exception as e:  # pylint: disable=broad-except
                fl_logging.warning('Handler [%s] flush failed. '
                                   'Some metrics might not be emitted. '
                                   'Error repr: %s',
                                   hdlr.get_name(), repr(e))


_metrics_client = Metrics()


def emit(name, value, tags=None, index_type='metrics'):
    _metrics_client.emit(name, value, tags, index_type)


# Currently no actual differences among the methods below
emit_counter = emit
emit_store = emit
emit_timer = emit

metric_collector = MetricCollector()


def timer(func_name, tags=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            time_start = time.time()
            result = func(*args, **kwargs)
            time_end = time.time()
            time_spend = time_end - time_start
            emit(func_name, time_spend, tags)
            return result

        return wrapper

    return decorator
