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
import json
from elasticsearch import Elasticsearch

from fedlearner_webconsole.envs import Envs


class ElasticSearchClient(object):
    def __init__(self):
        self._es_client = None
        self._es_client = Elasticsearch([{'host': Envs.ES_HOST,
                                          'port': Envs.ES_PORT}],
                                        http_auth=(Envs.ES_USERNAME,
                                                   Envs.ES_PASSWORD))

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
            json.loads(match_phrase) if match_phrase else
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

    def query_events(self, index, keyword, pod_name,
                     start_time, end_time, match_phrase=None):
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
            json.loads(match_phrase) if match_phrase else
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

    def query_data_join_metrics(self, job_name, num_buckets):
        STAT_AGG = {
            "JOINED": {
                "filter": {
                    "term": {
                        "tags.joined": 1
                    }
                }
            },
            "FAKE": {
                "filter": {
                    "term": {
                        "tags.joined": 0
                    }
                }
            },
            "UNJOINED": {
                "filter": {
                    "term": {
                        "tags.joined": -1
                    }
                }
            },
            "TOTAL": {
                "bucket_script": {
                    "buckets_path": {
                        "JOINED": "JOINED[_count]",
                        "UNJOINED": "UNJOINED[_count]"
                    },
                    "script": "params.JOINED + params.UNJOINED"
                }
            },
            "TOTAL_WITH_FAKE": {
                "bucket_script": {
                    "buckets_path": {
                        "JOINED": "JOINED[_count]",
                        "FAKE": "FAKE[_count]",
                        "UNJOINED": "UNJOINED[_count]"
                    },
                    "script": "params.JOINED + params.UNJOINED + params.FAKE"
                }
            },
            "JOIN_RATE": {
                "bucket_script": {
                    "buckets_path": {
                        "JOINED": "JOINED[_count]",
                        "TOTAL": "TOTAL[value]",
                        "FAKE": "FAKE[_count]"
                    },
                    "script": "params.JOINED / params.TOTAL"
                }
            },
            "JOIN_RATE_WITH_FAKE": {
                "bucket_script": {
                    "buckets_path": {
                        "JOINED": "JOINED[_count]",
                        "TOTAL_WITH_FAKE": "TOTAL_WITH_FAKE[value]",
                        "FAKE": "FAKE[_count]"
                    },
                    "script": "(params.JOINED + params.FAKE) / "
                              "params.TOTAL_WITH_FAKE"
                }
            }
        }

        query = {
            "size": 0,
            "query": {
                "bool": {
                    "must": [
                        {"term": {"tags.application_id": job_name}}
                    ]
                }
            },
            "aggs": {
                "OVERALL": {
                    "terms": {
                        "field": "tags.application_id"
                    },
                    "aggs": STAT_AGG
                },
                "EVENT_TIME": {
                    "auto_date_histogram": {
                        "field": "tags.event_time",
                        "format": "strict_date_optional_time",
                        "buckets": num_buckets
                    },
                    "aggs": STAT_AGG
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
                                "tags.application_id": job_name
                            }
                        },
                        {
                            "term": {
                                "name": "auc"
                            }
                        }
                    ]
                }
            },
            "aggs": {
                "PROCESS_TIME": {
                    "auto_date_histogram": {
                        "field": "tags.process_time",
                        "format": "strict_date_optional_time",
                        "buckets": num_buckets
                    },
                    "aggs": {
                        "AUC": {
                            "avg": {
                                "field": "value"
                            }
                        }
                    }
                }
            }
        }

        return es.search(index='metrics*', body=query)

    def query_time_metrics(self, job_name, num_buckets, index='raw_data*'):
        query = {
            "size": 0,
            "query": {
                "bool": {
                    "must": [
                        {
                            "term": {
                                "tags.application_id": job_name
                            }
                        },
                        {
                            "term": {
                                "tags.partition": 1
                            }
                        }
                    ]
                }
            },
            "aggs": {
                "PROCESS_TIME": {
                    "auto_date_histogram": {
                        "field": "tags.process_time",
                        "format": "strict_date_optional_time",
                        "buckets": num_buckets
                    },
                    "aggs": {
                        "MAX_EVENT_TIME": {
                            "max": {
                                "field": "tags.event_time"
                            }
                        },
                        "MIN_EVENT_TIME": {
                            "min": {
                                "field": "tags.event_time"
                            }
                        }
                    }
                }
            }
        }
        return es.search(index=index, body=query)


es = ElasticSearchClient()
