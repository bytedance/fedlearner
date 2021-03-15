# Copyright 2020 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
from elasticsearch import Elasticsearch

from fedlearner_webconsole.utils.es_misc import get_es_template, ALIAS_NAME


class ElasticSearchClient(object):
    def __init__(self):
        self._es_client = None

    def init_app(self, app):
        if 'ES_HOST' in app.config and 'ES_PORT' in app.config:
            self._es_client = Elasticsearch([
                {
                    'host': app.config['ES_HOST'],
                    'port': app.config['ES_PORT']
                }])
            if int(
                self._es_client.info()['version']['number'].split('.')[0]
            ) == 7:
                self._es_client.ilm.start()
                for index_type, alias_name in ALIAS_NAME.items():
                    self.put_ilm('fedlearner_{}_ilm'.format(index_type))
                    self._put_index_template(index_type, shards=1)
                    # if alias already exists, no need to set write index
                    if not self._es_client.indices.exists_alias(alias_name):
                        # if index with the same name as alias exists, delete it
                        if self._es_client.indices.exists(alias_name):
                            self._es_client.indices.delete(alias_name)
                        self._put_write_index(index_type)
                self.put_ilm('filebeat-7.0.1', hot_age='1d')

    def search(self, *args, **kwargs):
        return self._es_client.search(*args, **kwargs)

    def query_log(self, index, keyword, pod_name, start_time, end_time,
                  match_phrase=None):
        query_body = {
            'version': True,
            'size': 8000,
            'sort': [
                {'@timestamp': 'desc'},
                {
                    'log.offset': {
                        'order': 'desc',
                        'unmapped_type': 'long'
                    }
                }
            ],
            '_source': ['message'],
            'query': {
                'bool': {
                    'must': []
                }
            }
        }

        keyword_list = [{
            'query_string': {
                'query': keyword,
                'analyze_wildcard': True,
                'default_operator': 'AND',
                'default_field': '*'
            }
        }] if keyword else []
        match_phrase_list = [
            match_phrase if match_phrase else
            {
                'prefix': {
                    'kubernetes.pod.name': pod_name
                }
            },
            {
                'range': {
                    '@timestamp': {
                        'gte': start_time,
                        'lte': end_time,
                        'format': 'epoch_millis'
                    }
                }
            }
        ]
        query_body['query']['bool']['must'] = keyword_list + match_phrase_list
        response = self._es_client.search(index=index, body=query_body)
        return [item['_source']['message'] for item in response['hits']['hits']]

    def query_data_join_metrics(self, job_name, num_buckets):
        STAT_AGG = {
            "JOINED": {
                "filter": {
                    "term": {
                        "joined": True
                    }
                }
            },
            "FAKE": {
                "filter": {
                    "term": {
                        "fake": True
                    }
                }
            },
            "TOTAL": {
                "filter": {
                    "term": {
                        "fake": False
                    }
                }
            },
            "UNJOINED": {
                "bucket_script": {
                    "buckets_path": {
                        "JOINED": "JOINED[_count]",
                        "TOTAL": "TOTAL[_count]"
                    },
                    "script": "params.TOTAL - params.JOINED"
                }
            },
            "JOIN_RATE": {
                "bucket_script": {
                    "buckets_path": {
                        "JOINED": "JOINED[_count]",
                        "TOTAL": "TOTAL[_count]",
                        "FAKE": "FAKE[_count]"
                    },
                    "script": "params.JOINED / (params.TOTAL + params.FAKE)"
                }
            }
        }

        query = {
            "size": 0,
            "query": {
                "bool": {
                    "must": [
                        {"term": {"application_id": job_name}}
                    ]
                }
            },
            "aggs": {
                "OVERALL": {
                    "terms": {
                        "field": "application_id"
                    },
                    "aggs": STAT_AGG
                },
                "EVENT_TIME": {
                    "auto_date_histogram": {
                        "field": "event_time",
                        "format": "strict_date_optional_time",
                        "buckets": num_buckets
                    },
                    "aggs": STAT_AGG
                },
                "PROCESS_TIME": {
                    "auto_date_histogram": {
                        "field": "process_time",
                        "format": "strict_date_optional_time",
                        "buckets": num_buckets
                    },
                    "aggs": {
                        "MAX_EVENT_TIME": {
                            "max": {
                                "field": "event_time",
                                "format": "strict_date_optional_time"
                            }
                        },
                        "MIN_EVENT_TIME": {
                            "min": {
                                "field": "event_time",
                                "format": "strict_date_optional_time"
                            }
                        }
                    }
                }
            }
        }

        return es.search(index='data_join*', body=query)

    def query_nn_metrics(self, job_name, num_buckets):
        query = {
            "size": 0,
            "query": {
                "bool": {
                    "must": [
                        {
                            "term": {
                                "tags.application_id.keyword": job_name
                            }
                        }
                    ]
                }
            },
            "aggs": {
                "PROCESS_TIME": {
                    "auto_date_histogram": {
                        "field": "date_time",
                        "format": "strict_date_optional_time",
                        "buckets": num_buckets
                    },
                    "aggs": {
                        "AUC": {
                            "filter": {
                                "term": {"name": "auc"}
                            },
                            "aggs": {
                                "AUC": {
                                    "avg": {
                                        "field": "value"
                                    }
                                }
                            }
                        },
                    }
                }
            }
        }

        return es.search(index='metrics*', body=query)

    def query_events(self, index, keyword, pod_name,
                     start_time, end_time):
        query_body = {
            'version': True,
            'size': 8000,
            'sort': [
                {'@timestamp': 'desc'},
                {
                    'log.offset': {
                        'order': 'desc',
                        'unmapped_type': 'long'
                    }
                }
            ],
            '_source': ['message'],
            'query': {
                'bool': {
                    'must': []
                }
            }
        }

        keyword_list = [
            {
                'query_string': {
                    'query': f'{keyword} AND Event',
                    'analyze_wildcard': True,
                    'default_operator': 'AND',
                    'default_field': '*'
                }
            }
        ] if keyword else []
        match_phrase_list = [
            {
                'prefix': {
                    'kubernetes.pod.name': pod_name
                }
            },
            {
                'range': {
                    '@timestamp': {
                        'gte': start_time,
                        'lte': end_time,
                        'format': 'epoch_millis'
                    }
                }
            }
        ]
        query_body['query']['bool']['must'] = keyword_list + match_phrase_list
        response = self._es_client.search(index=index, body=query_body)
        return [item['_source']['message'] for item in response['hits']['hits']]

    def put_ilm(self, ilm_name,
                hot_size='50gb', hot_age='10d', delete_age='30d'):
        if self._es_client is None:
            raise RuntimeError('ES client not yet initialized.')
        ilm_body = {
            "policy": {
                "phases": {
                    "hot": {
                        "min_age": "0ms",
                        "actions": {
                            "rollover": {
                                "max_size": hot_size,
                                "max_age": hot_age
                            }
                        }
                    },
                    "delete": {
                        "min_age": delete_age,
                        "actions": {
                            "delete": {}
                        }
                    }
                }
            }
        }
        self._es_client.ilm.put_lifecycle(ilm_name, body=ilm_body)

    def _put_index_template(self, index_type, shards):
        assert self._es_client is not None, 'ES client not yet initialized.'
        template_name = ALIAS_NAME[index_type] + '-template'
        template_body = get_es_template(index_type, shards=shards)
        self._es_client.indices.put_template(template_name, template_body)

    def _put_write_index(self, index_type):
        assert self._es_client is not None, 'ES client not yet initialized.'
        alias_name = ALIAS_NAME[index_type]
        self._es_client.indices.create(
            # resolves to alias_name-yyyy.mm.dd-000001 in ES
            f'<{alias_name}-{{now/d}}-000001>',
            body={"aliases": {alias_name: {"is_write_index": True}}}
        )


es = ElasticSearchClient()
