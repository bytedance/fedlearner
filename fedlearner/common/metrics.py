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
import copy
import datetime
import logging
import os
import threading
import time
from functools import wraps

import elasticsearch as es7
import elasticsearch6 as es6
import pytz
from elasticsearch import helpers as helpers7
from elasticsearch6 import helpers as helpers6

# WARNING: ARBITRARY MODIFICATIONS OF INDICES BELOW WILL RESULT IN HUGE USAGE OF
# ES DISK SPACE, PLEASE MODIFY WITH CAUTION. DO NOT MODIFY EXISTING FIELDS
# WITHOUT PERMISSION AND TEST, OTHERWISE ERRORS MIGHT OCCUR.
DATA_JOIN_INDEX = {
    "settings": {
        "index": {
            "codec": "best_compression"
        }
    },
    "mappings": {
        "dynamic": True,
        # for dynamically adding string fields, use keyword to reduce space
        "dynamic_templates": [
            {
                "strings": {
                    "match_mapping_type": "string",
                    "mapping": {
                        "type": "keyword"
                    }
                }
            }
        ],
        "properties": {
            "partition": {
                "type": "byte"
            },
            "joined": {
                "type": "boolean"
            },
            "fake": {
                "type": "boolean"
            },
            "label": {
                "ignore_above": 8,
                "type": "keyword"
            },
            "type": {
                "ignore_above": 32,
                "type": "keyword"
            },
            "application_id": {
                "ignore_above": 128,
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
METRICS_INDEX = {
    "mappings": {
        "dynamic": True,
        "properties": {
            "name": {
                # for compatibility, use text here
                "type": "text"
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
                        "ignore_above": 16,
                        "type": "keyword"
                    }
                }
            }
        }
    }
}
INDEX_NAME = {'metrics': 'metrics_v2-{}',
              'data_join': 'data_join-{}'}
INDEX_MAP = {'metrics': METRICS_INDEX,
             'data_join': DATA_JOIN_INDEX}
CONFIGS = {
    'data_join_metrics_sample_rate':
        os.environ.get('DATA_JOIN_METRICS_SAMPLE_RATE', 0.3),
    'es_batch_size': os.environ.get('ES_BATCH_SIZE', 1000),
    'timezone': pytz.timezone('Asia/Shanghai')
}


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
        logging.debug('[metrics] name[%s] value[%s] tags[%s]',
                      name, value, str(tags))


class ElasticSearchHandler(Handler):
    """
    Emit documents to ElasticSearch
    """

    def __init__(self, ip, port):
        super(ElasticSearchHandler, self).__init__('elasticsearch')
        self._es = es7.Elasticsearch([ip], port=port)
        self._helpers = helpers7
        self._version = int(self._es.info()['version']['number'].split('.')[0])
        # ES 6.8 has differences in APIs compared to ES 7.6
        if self._version == 6:
            self._es = es6.Elasticsearch([ip], port=port)
            self._helpers = helpers6
        # suppress ES logger
        logging.getLogger('elasticsearch').setLevel(logging.CRITICAL)
        self._emit_batch = []
        self._current_date = ''
        self._batch_size = CONFIGS['es_batch_size']
        self._lock = threading.RLock()

    def emit(self, name, value, tags=None, index_type='metrics'):
        assert index_type in ('metrics', 'data_join')
        if tags is None:
            tags = {}
        date = datetime.datetime.now(
            tz=CONFIGS['timezone']).strftime('%Y.%m.%d')
        index = INDEX_NAME[index_type].format(date)
        # if indices not match, flush and create a new one
        with self._lock:
            if self._get_current_date() != date:
                # Date changed, should create new index and flush old ones
                logging.info('METRICS: Creating new index %s.', index)
                self._create_or_modify_index(index, INDEX_MAP[index_type])
                self._set_current_date(date)
        application_id = os.environ.get('APPLICATION_ID', '')
        if application_id:
            tags['application_id'] = str(application_id)
        if index_type == 'metrics':
            document = {
                "name": name,
                "value": value,
                "tags": tags,
                # convert to UTC+8 and strip down the timezone info
                "date_time": datetime.datetime.now(
                    tz=CONFIGS['timezone']).isoformat(timespec='seconds')[:-6]
            }
        else:
            document = tags
        action = {
            # _index = which index to emit to
            '_index': index,
            '_source': document
        }
        if self._version == 6:
            action['_type'] = '_doc'
        with self._lock:
            self._emit_batch.append(action)
            # emit and pop when there are enough documents to emit
            if len(self._emit_batch) >= self._batch_size:
                self.flush()

    def flush(self):
        if len(self._emit_batch) > 0:
            logging.info('METRICS: Emitting %d documents to ES',
                         len(self._emit_batch))
            self._helpers.bulk(self._es, self._emit_batch)
            self._emit_batch = []

    def _get_current_date(self):
        with self._lock:
            return self._current_date

    def _set_current_date(self, date):
        with self._lock:
            self._current_date = date

    def _create_or_modify_index(self, index, index_setting):
        """
        Args:
            index: ES index name.

        Creates an index on ES, with compatibility with ES 6 and ES 7.
        If Index already exists, will put mappings onto it in case mappings
        have been changed.

        """
        with self._lock:
            if not self._es.indices.exists(index=index):
                if self._version == 7:
                    body = index_setting
                    already_exists_exception = es7.exceptions.RequestError
                else:
                    body = copy.deepcopy(index_setting)
                    body['mappings'] = {'_doc': body['mappings']}
                    already_exists_exception = es6.exceptions.RequestError
                try:
                    self._es.indices.create(index=index, body=body)
                    return
                # index may have been created by other jobs
                except already_exists_exception as e:
                    # if due to other reasons, re-raise exception
                    if e.info['error']['type'] != \
                       'resource_already_exists_exception':
                        raise e
                    logging.info('METRICS: Index %s already exists.', index)

            # if index exists, put mapping in case mapping is modified.
            if self._version == 7:
                self._es.indices.put_mapping(index=index,
                                             body=index_setting['mappings'])
            else:
                self._es.indices.put_mapping(index=index,
                                             body=index_setting['mappings'],
                                             doc_type='_doc')


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

    def emit(self, name, value, tags=None, index_type='metrics'):
        self.init_handlers()
        if not self.handlers or len(self.handlers) == 0:
            logging.info('No handlers. Not emitting.')
            return

        for hdlr in self.handlers:
            try:
                hdlr.emit(name, value, tags, index_type)
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


def emit(name, value, tags=None, index_type='metrics'):
    _metrics_client.emit(name, value, tags, index_type)


# Currently no actual differences among the methods below
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
