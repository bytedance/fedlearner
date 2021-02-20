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
from config import Config


class ElasticSearchClient(object):
    def __init__(self, host, port):
        self._es_client = Elasticsearch([{'host': host,
                                          'port': port}])

    def query_log(self, index, keyword, pod_name, start_time, end_time,
                  match_phrase=None):
        query_body = {
            'version': True,
            'size': 8000,
            'sort': [
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
            },
            'sort': [{'@timestamp': 'asc'}]
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


es = ElasticSearchClient(Config.ES_HOST, Config.ES_PORT)
