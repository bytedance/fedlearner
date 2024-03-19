# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

fake_es_query_nn_metrics_result = {
    'took': 6,
    'timed_out': False,
    '_shards': {
        'total': 4,
        'successful': 4,
        'skipped': 0,
        'failed': 0
    },
    'hits': {
        'total': {
            'value': 4000,
            'relation': 'eq'
        },
        'max_score': None,
        'hits': []
    },
    'aggregations': {
        'acc': {
            'doc_count': 2000,
            'PROCESS_TIME': {
                'buckets': [{
                    'key_as_string': '2022-02-17T10:27:30.000Z',
                    'key': 1645093650000,
                    'doc_count': 169,
                    'VALUE': {
                        'value': 0.37631335140332667
                    }
                }, {
                    'key_as_string': '2022-02-17T10:27:35.000Z',
                    'key': 1645093655000,
                    'doc_count': 270,
                    'VALUE': {
                        'value': 0.6482393520849722
                    }
                }, {
                    'key_as_string': '2022-02-17T10:27:40.000Z',
                    'key': 1645093660000,
                    'doc_count': 290,
                    'VALUE': {
                        'value': 0.749889914331765
                    }
                }, {
                    'key_as_string': '2022-02-17T10:27:45.000Z',
                    'key': 1645093665000,
                    'doc_count': 260,
                    'VALUE': {
                        'value': 0.7920331122783514
                    }
                }, {
                    'key_as_string': '2022-02-17T10:27:50.000Z',
                    'key': 1645093670000,
                    'doc_count': 119,
                    'VALUE': {
                        'value': 0.8848890877571427
                    }
                }, {
                    'key_as_string': '2022-02-17T10:27:55.000Z',
                    'key': 1645093675000,
                    'doc_count': 240,
                    'VALUE': {
                        'value': 0.8932028951744239
                    }
                }, {
                    'key_as_string': '2022-02-17T10:28:00.000Z',
                    'key': 1645093680000,
                    'doc_count': 160,
                    'VALUE': {
                        'value': 0.8983024559915066
                    }
                }, {
                    'key_as_string': '2022-02-17T10:28:05.000Z',
                    'key': 1645093685000,
                    'doc_count': 160,
                    'VALUE': {
                        'value': 0.9003030106425285
                    }
                }, {
                    'key_as_string': '2022-02-17T10:28:10.000Z',
                    'key': 1645093690000,
                    'doc_count': 150,
                    'VALUE': {
                        'value': 0.9026716228326161
                    }
                }, {
                    'key_as_string': '2022-02-17T10:28:15.000Z',
                    'key': 1645093695000,
                    'doc_count': 182,
                    'VALUE': {
                        'value': 0.9047519653053074
                    }
                }],
                'interval': '1s'
            }
        },
        'loss': {
            'doc_count': 2000,
            'PROCESS_TIME': {
                'buckets': [{
                    'key_as_string': '2022-02-17T10:27:30.000Z',
                    'key': 1645093650000,
                    'doc_count': 169,
                    'VALUE': {
                        'value': 1.8112774487783219
                    }
                }, {
                    'key_as_string': '2022-02-17T10:27:35.000Z',
                    'key': 1645093655000,
                    'doc_count': 270,
                    'VALUE': {
                        'value': 0.8499700573859391
                    }
                }, {
                    'key_as_string': '2022-02-17T10:27:40.000Z',
                    'key': 1645093660000,
                    'doc_count': 290,
                    'VALUE': {
                        'value': 0.5077963560819626
                    }
                }, {
                    'key_as_string': '2022-02-17T10:27:45.000Z',
                    'key': 1645093665000,
                    'doc_count': 260,
                    'VALUE': {
                        'value': 0.4255857397157412
                    }
                }, {
                    'key_as_string': '2022-02-17T10:27:50.000Z',
                    'key': 1645093670000,
                    'doc_count': 119,
                    'VALUE': {
                        'value': 0.3902850116000456
                    }
                }, {
                    'key_as_string': '2022-02-17T10:27:55.000Z',
                    'key': 1645093675000,
                    'doc_count': 240,
                    'VALUE': {
                        'value': 0.3689204063266516
                    }
                }, {
                    'key_as_string': '2022-02-17T10:28:00.000Z',
                    'key': 1645093680000,
                    'doc_count': 160,
                    'VALUE': {
                        'value': 0.34096595416776837
                    }
                }, {
                    'key_as_string': '2022-02-17T10:28:05.000Z',
                    'key': 1645093685000,
                    'doc_count': 160,
                    'VALUE': {
                        'value': 0.3247630867641419
                    }
                }, {
                    'key_as_string': '2022-02-17T10:28:10.000Z',
                    'key': 1645093690000,
                    'doc_count': 150,
                    'VALUE': {
                        'value': 0.3146447554727395
                    }
                }, {
                    'key_as_string': '2022-02-17T10:28:15.000Z',
                    'key': 1645093695000,
                    'doc_count': 182,
                    'VALUE': {
                        'value': 0.3103061146461047
                    }
                }],
                'interval': '1s'
            }
        },
        'abs': {
            'doc_count': 0,
            'PROCESS_TIME': {
                'buckets': [],
                'interval': '1s'
            }
        },
        'mse': {
            'doc_count': 0,
            'PROCESS_TIME': {
                'buckets': [],
                'interval': '1s'
            }
        },
        'auc': {
            'doc_count': 0,
            'PROCESS_TIME': {
                'buckets': [],
                'interval': '1s'
            }
        }
    }
}

fake_es_query_tree_metrics_result = {
    'took': 2,
    'timed_out': False,
    '_shards': {
        'total': 4,
        'successful': 4,
        'skipped': 0,
        'failed': 0
    },
    'hits': {
        'total': {
            'value': 100,
            'relation': 'eq'
        },
        'max_score': None,
        'hits': []
    },
    'aggregations': {
        'ACC': {
            'doc_count': 10,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            },
            'TRAIN': {
                'doc_count': 10,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 10,
                            'relation': 'eq'
                        },
                        'max_score':
                            None,
                        'hits': [{
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'u5l-Bn8BDVkhsHlSOwtF',
                            '_score': None,
                            '_source': {
                                'value': 0.857,
                                'tags': {
                                    'iteration': 1
                                }
                            },
                            'sort': [1645081410370]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'eJl-Bn8BDVkhsHlSTmZo',
                            '_score': None,
                            '_source': {
                                'value': 0.862,
                                'tags': {
                                    'iteration': 2
                                }
                            },
                            'sort': [1645081415270]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'jJl-Bn8BDVkhsHlSYcPm',
                            '_score': None,
                            '_source': {
                                'value': 0.868,
                                'tags': {
                                    'iteration': 3
                                }
                            },
                            'sort': [1645081420260]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'PJp-Bn8BDVkhsHlSdBpj',
                            '_score': None,
                            '_source': {
                                'value': 0.872,
                                'tags': {
                                    'iteration': 4
                                }
                            },
                            'sort': [1645081424992]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'v5p-Bn8BDVkhsHlShnT8',
                            '_score': None,
                            '_source': {
                                'value': 0.886,
                                'tags': {
                                    'iteration': 5
                                }
                            },
                            'sort': [1645081429754]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'oJp-Bn8BDVkhsHlSmdSC',
                            '_score': None,
                            '_source': {
                                'value': 0.883,
                                'tags': {
                                    'iteration': 6
                                }
                            },
                            'sort': [1645081434496]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': '95t-Bn8BDVkhsHlSqyrd',
                            '_score': None,
                            '_source': {
                                'value': 0.884,
                                'tags': {
                                    'iteration': 7
                                }
                            },
                            'sort': [1645081439195]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'OZt-Bn8BDVkhsHlSvn4y',
                            '_score': None,
                            '_source': {
                                'value': 0.895,
                                'tags': {
                                    'iteration': 8
                                }
                            },
                            'sort': [1645081443888]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': '6pt-Bn8BDVkhsHlS0csC',
                            '_score': None,
                            '_source': {
                                'value': 0.896,
                                'tags': {
                                    'iteration': 9
                                }
                            },
                            'sort': [1645081448704]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'UJx-Bn8BDVkhsHlS4y3-',
                            '_score': None,
                            '_source': {
                                'value': 0.902,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1645081453564]
                        }]
                    }
                }
            }
        },
        'FN': {
            'doc_count': 10,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            },
            'TRAIN': {
                'doc_count': 10,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 10,
                            'relation': 'eq'
                        },
                        'max_score':
                            None,
                        'hits': [{
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'xJl-Bn8BDVkhsHlSOwtF',
                            '_score': None,
                            '_source': {
                                'value': 128.0,
                                'tags': {
                                    'iteration': 1
                                }
                            },
                            'sort': [1645081410370]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'gZl-Bn8BDVkhsHlSTmZo',
                            '_score': None,
                            '_source': {
                                'value': 123.0,
                                'tags': {
                                    'iteration': 2
                                }
                            },
                            'sort': [1645081415270]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'lZl-Bn8BDVkhsHlSYcPm',
                            '_score': None,
                            '_source': {
                                'value': 116.0,
                                'tags': {
                                    'iteration': 3
                                }
                            },
                            'sort': [1645081420260]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'RZp-Bn8BDVkhsHlSdBpj',
                            '_score': None,
                            '_source': {
                                'value': 115.0,
                                'tags': {
                                    'iteration': 4
                                }
                            },
                            'sort': [1645081424993]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'yJp-Bn8BDVkhsHlShnT8',
                            '_score': None,
                            '_source': {
                                'value': 102.0,
                                'tags': {
                                    'iteration': 5
                                }
                            },
                            'sort': [1645081429754]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'qZp-Bn8BDVkhsHlSmdSC',
                            '_score': None,
                            '_source': {
                                'value': 104.0,
                                'tags': {
                                    'iteration': 6
                                }
                            },
                            'sort': [1645081434496]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'AJt-Bn8BDVkhsHlSqyvd',
                            '_score': None,
                            '_source': {
                                'value': 105.0,
                                'tags': {
                                    'iteration': 7
                                }
                            },
                            'sort': [1645081439195]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'Qpt-Bn8BDVkhsHlSvn4y',
                            '_score': None,
                            '_source': {
                                'value': 99.0,
                                'tags': {
                                    'iteration': 8
                                }
                            },
                            'sort': [1645081443888]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': '85t-Bn8BDVkhsHlS0csC',
                            '_score': None,
                            '_source': {
                                'value': 97.0,
                                'tags': {
                                    'iteration': 9
                                }
                            },
                            'sort': [1645081448705]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'WZx-Bn8BDVkhsHlS4y3-',
                            '_score': None,
                            '_source': {
                                'value': 93.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1645081453564]
                        }]
                    }
                }
            }
        },
        'KS': {
            'doc_count': 10,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            },
            'TRAIN': {
                'doc_count': 10,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 10,
                            'relation': 'eq'
                        },
                        'max_score':
                            None,
                        'hits': [{
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'wJl-Bn8BDVkhsHlSOwtF',
                            '_score': None,
                            '_source': {
                                'value': 0.47770564314760644,
                                'tags': {
                                    'iteration': 1
                                }
                            },
                            'sort': [1645081410370]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'fZl-Bn8BDVkhsHlSTmZo',
                            '_score': None,
                            '_source': {
                                'value': 0.5349813321918623,
                                'tags': {
                                    'iteration': 2
                                }
                            },
                            'sort': [1645081415270]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'kZl-Bn8BDVkhsHlSYcPm',
                            '_score': None,
                            '_source': {
                                'value': 0.5469192171410906,
                                'tags': {
                                    'iteration': 3
                                }
                            },
                            'sort': [1645081420260]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'QZp-Bn8BDVkhsHlSdBpj',
                            '_score': None,
                            '_source': {
                                'value': 0.5596894247461416,
                                'tags': {
                                    'iteration': 4
                                }
                            },
                            'sort': [1645081424993]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'xJp-Bn8BDVkhsHlShnT8',
                            '_score': None,
                            '_source': {
                                'value': 0.5992009702504102,
                                'tags': {
                                    'iteration': 5
                                }
                            },
                            'sort': [1645081429754]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'pZp-Bn8BDVkhsHlSmdSC',
                            '_score': None,
                            '_source': {
                                'value': 0.6175715202967825,
                                'tags': {
                                    'iteration': 6
                                }
                            },
                            'sort': [1645081434496]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': '_Jt-Bn8BDVkhsHlSqyrd',
                            '_score': None,
                            '_source': {
                                'value': 0.6366317091151221,
                                'tags': {
                                    'iteration': 7
                                }
                            },
                            'sort': [1645081439195]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'Ppt-Bn8BDVkhsHlSvn4y',
                            '_score': None,
                            '_source': {
                                'value': 0.6989964566835509,
                                'tags': {
                                    'iteration': 8
                                }
                            },
                            'sort': [1645081443888]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': '75t-Bn8BDVkhsHlS0csC',
                            '_score': None,
                            '_source': {
                                'value': 0.7088535349932226,
                                'tags': {
                                    'iteration': 9
                                }
                            },
                            'sort': [1645081448704]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'VZx-Bn8BDVkhsHlS4y3-',
                            '_score': None,
                            '_source': {
                                'value': 0.7418848541057288,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1645081453564]
                        }]
                    }
                }
            }
        },
        'RECALL': {
            'doc_count': 10,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            },
            'TRAIN': {
                'doc_count': 10,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 10,
                            'relation': 'eq'
                        },
                        'max_score':
                            None,
                        'hits': [{
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'vZl-Bn8BDVkhsHlSOwtF',
                            '_score': None,
                            '_source': {
                                'value': 0.40186915887850466,
                                'tags': {
                                    'iteration': 1
                                }
                            },
                            'sort': [1645081410370]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'epl-Bn8BDVkhsHlSTmZo',
                            '_score': None,
                            '_source': {
                                'value': 0.4252336448598131,
                                'tags': {
                                    'iteration': 2
                                }
                            },
                            'sort': [1645081415270]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'jpl-Bn8BDVkhsHlSYcPm',
                            '_score': None,
                            '_source': {
                                'value': 0.45794392523364486,
                                'tags': {
                                    'iteration': 3
                                }
                            },
                            'sort': [1645081420260]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'Ppp-Bn8BDVkhsHlSdBpj',
                            '_score': None,
                            '_source': {
                                'value': 0.46261682242990654,
                                'tags': {
                                    'iteration': 4
                                }
                            },
                            'sort': [1645081424992]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'wZp-Bn8BDVkhsHlShnT8',
                            '_score': None,
                            '_source': {
                                'value': 0.5233644859813084,
                                'tags': {
                                    'iteration': 5
                                }
                            },
                            'sort': [1645081429754]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'opp-Bn8BDVkhsHlSmdSC',
                            '_score': None,
                            '_source': {
                                'value': 0.514018691588785,
                                'tags': {
                                    'iteration': 6
                                }
                            },
                            'sort': [1645081434496]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': '-Zt-Bn8BDVkhsHlSqyrd',
                            '_score': None,
                            '_source': {
                                'value': 0.5093457943925234,
                                'tags': {
                                    'iteration': 7
                                }
                            },
                            'sort': [1645081439195]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'O5t-Bn8BDVkhsHlSvn4y',
                            '_score': None,
                            '_source': {
                                'value': 0.5373831775700935,
                                'tags': {
                                    'iteration': 8
                                }
                            },
                            'sort': [1645081443888]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': '7Jt-Bn8BDVkhsHlS0csC',
                            '_score': None,
                            '_source': {
                                'value': 0.5467289719626168,
                                'tags': {
                                    'iteration': 9
                                }
                            },
                            'sort': [1645081448704]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'Upx-Bn8BDVkhsHlS4y3-',
                            '_score': None,
                            '_source': {
                                'value': 0.5654205607476636,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1645081453564]
                        }]
                    }
                }
            }
        },
        'FP': {
            'doc_count': 10,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            },
            'TRAIN': {
                'doc_count': 10,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 10,
                            'relation': 'eq'
                        },
                        'max_score':
                            None,
                        'hits': [{
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'w5l-Bn8BDVkhsHlSOwtF',
                            '_score': None,
                            '_source': {
                                'value': 15.0,
                                'tags': {
                                    'iteration': 1
                                }
                            },
                            'sort': [1645081410370]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'gJl-Bn8BDVkhsHlSTmZo',
                            '_score': None,
                            '_source': {
                                'value': 15.0,
                                'tags': {
                                    'iteration': 2
                                }
                            },
                            'sort': [1645081415270]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'lJl-Bn8BDVkhsHlSYcPm',
                            '_score': None,
                            '_source': {
                                'value': 16.0,
                                'tags': {
                                    'iteration': 3
                                }
                            },
                            'sort': [1645081420260]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'RJp-Bn8BDVkhsHlSdBpj',
                            '_score': None,
                            '_source': {
                                'value': 13.0,
                                'tags': {
                                    'iteration': 4
                                }
                            },
                            'sort': [1645081424993]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'x5p-Bn8BDVkhsHlShnT8',
                            '_score': None,
                            '_source': {
                                'value': 12.0,
                                'tags': {
                                    'iteration': 5
                                }
                            },
                            'sort': [1645081429754]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'qJp-Bn8BDVkhsHlSmdSC',
                            '_score': None,
                            '_source': {
                                'value': 13.0,
                                'tags': {
                                    'iteration': 6
                                }
                            },
                            'sort': [1645081434496]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': '_5t-Bn8BDVkhsHlSqyrd',
                            '_score': None,
                            '_source': {
                                'value': 11.0,
                                'tags': {
                                    'iteration': 7
                                }
                            },
                            'sort': [1645081439195]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'QZt-Bn8BDVkhsHlSvn4y',
                            '_score': None,
                            '_source': {
                                'value': 6.0,
                                'tags': {
                                    'iteration': 8
                                }
                            },
                            'sort': [1645081443888]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': '8pt-Bn8BDVkhsHlS0csC',
                            '_score': None,
                            '_source': {
                                'value': 7.0,
                                'tags': {
                                    'iteration': 9
                                }
                            },
                            'sort': [1645081448705]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'WJx-Bn8BDVkhsHlS4y3-',
                            '_score': None,
                            '_source': {
                                'value': 5.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1645081453564]
                        }]
                    }
                }
            }
        },
        'F1': {
            'doc_count': 10,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            },
            'TRAIN': {
                'doc_count': 10,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 10,
                            'relation': 'eq'
                        },
                        'max_score':
                            None,
                        'hits': [{
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'vpl-Bn8BDVkhsHlSOwtF',
                            '_score': None,
                            '_source': {
                                'value': 0.546031746031746,
                                'tags': {
                                    'iteration': 1
                                }
                            },
                            'sort': [1645081410370]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'e5l-Bn8BDVkhsHlSTmZo',
                            '_score': None,
                            '_source': {
                                'value': 0.56875,
                                'tags': {
                                    'iteration': 2
                                }
                            },
                            'sort': [1645081415270]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'j5l-Bn8BDVkhsHlSYcPm',
                            '_score': None,
                            '_source': {
                                'value': 0.5975609756097561,
                                'tags': {
                                    'iteration': 3
                                }
                            },
                            'sort': [1645081420260]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'P5p-Bn8BDVkhsHlSdBpj',
                            '_score': None,
                            '_source': {
                                'value': 0.607361963190184,
                                'tags': {
                                    'iteration': 4
                                }
                            },
                            'sort': [1645081424993]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'wpp-Bn8BDVkhsHlShnT8',
                            '_score': None,
                            '_source': {
                                'value': 0.6627218934911242,
                                'tags': {
                                    'iteration': 5
                                }
                            },
                            'sort': [1645081429754]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'o5p-Bn8BDVkhsHlSmdSC',
                            '_score': None,
                            '_source': {
                                'value': 0.6528189910979227,
                                'tags': {
                                    'iteration': 6
                                }
                            },
                            'sort': [1645081434496]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': '-pt-Bn8BDVkhsHlSqyrd',
                            '_score': None,
                            '_source': {
                                'value': 0.6526946107784432,
                                'tags': {
                                    'iteration': 7
                                }
                            },
                            'sort': [1645081439195]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'PJt-Bn8BDVkhsHlSvn4y',
                            '_score': None,
                            '_source': {
                                'value': 0.6865671641791044,
                                'tags': {
                                    'iteration': 8
                                }
                            },
                            'sort': [1645081443888]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': '7Zt-Bn8BDVkhsHlS0csC',
                            '_score': None,
                            '_source': {
                                'value': 0.6923076923076923,
                                'tags': {
                                    'iteration': 9
                                }
                            },
                            'sort': [1645081448704]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'U5x-Bn8BDVkhsHlS4y3-',
                            '_score': None,
                            '_source': {
                                'value': 0.711764705882353,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1645081453564]
                        }]
                    }
                }
            }
        },
        'PRECISION': {
            'doc_count': 10,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            },
            'TRAIN': {
                'doc_count': 10,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 10,
                            'relation': 'eq'
                        },
                        'max_score':
                            None,
                        'hits': [{
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'vJl-Bn8BDVkhsHlSOwtF',
                            '_score': None,
                            '_source': {
                                'value': 0.8514851485148515,
                                'tags': {
                                    'iteration': 1
                                }
                            },
                            'sort': [1645081410370]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'eZl-Bn8BDVkhsHlSTmZo',
                            '_score': None,
                            '_source': {
                                'value': 0.8584905660377359,
                                'tags': {
                                    'iteration': 2
                                }
                            },
                            'sort': [1645081415270]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'jZl-Bn8BDVkhsHlSYcPm',
                            '_score': None,
                            '_source': {
                                'value': 0.8596491228070176,
                                'tags': {
                                    'iteration': 3
                                }
                            },
                            'sort': [1645081420260]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'PZp-Bn8BDVkhsHlSdBpj',
                            '_score': None,
                            '_source': {
                                'value': 0.8839285714285714,
                                'tags': {
                                    'iteration': 4
                                }
                            },
                            'sort': [1645081424992]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'wJp-Bn8BDVkhsHlShnT8',
                            '_score': None,
                            '_source': {
                                'value': 0.9032258064516129,
                                'tags': {
                                    'iteration': 5
                                }
                            },
                            'sort': [1645081429754]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'oZp-Bn8BDVkhsHlSmdSC',
                            '_score': None,
                            '_source': {
                                'value': 0.8943089430894309,
                                'tags': {
                                    'iteration': 6
                                }
                            },
                            'sort': [1645081434496]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': '-Jt-Bn8BDVkhsHlSqyrd',
                            '_score': None,
                            '_source': {
                                'value': 0.9083333333333333,
                                'tags': {
                                    'iteration': 7
                                }
                            },
                            'sort': [1645081439195]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'Opt-Bn8BDVkhsHlSvn4y',
                            '_score': None,
                            '_source': {
                                'value': 0.9504132231404959,
                                'tags': {
                                    'iteration': 8
                                }
                            },
                            'sort': [1645081443888]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': '65t-Bn8BDVkhsHlS0csC',
                            '_score': None,
                            '_source': {
                                'value': 0.9435483870967742,
                                'tags': {
                                    'iteration': 9
                                }
                            },
                            'sort': [1645081448704]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'UZx-Bn8BDVkhsHlS4y3-',
                            '_score': None,
                            '_source': {
                                'value': 0.9603174603174603,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1645081453564]
                        }]
                    }
                }
            }
        },
        'AUC': {
            'doc_count': 10,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            },
            'TRAIN': {
                'doc_count': 10,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 10,
                            'relation': 'eq'
                        },
                        'max_score':
                            None,
                        'hits': [{
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'v5l-Bn8BDVkhsHlSOwtF',
                            '_score': None,
                            '_source': {
                                'value': 0.8011640626857863,
                                'tags': {
                                    'iteration': 1
                                }
                            },
                            'sort': [1645081410370]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'fJl-Bn8BDVkhsHlSTmZo',
                            '_score': None,
                            '_source': {
                                'value': 0.8377684240565029,
                                'tags': {
                                    'iteration': 2
                                }
                            },
                            'sort': [1645081415270]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'kJl-Bn8BDVkhsHlSYcPm',
                            '_score': None,
                            '_source': {
                                'value': 0.8533328577203871,
                                'tags': {
                                    'iteration': 3
                                }
                            },
                            'sort': [1645081420260]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'QJp-Bn8BDVkhsHlSdBpj',
                            '_score': None,
                            '_source': {
                                'value': 0.860663242253454,
                                'tags': {
                                    'iteration': 4
                                }
                            },
                            'sort': [1645081424993]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'w5p-Bn8BDVkhsHlShnT8',
                            '_score': None,
                            '_source': {
                                'value': 0.8797977455946351,
                                'tags': {
                                    'iteration': 5
                                }
                            },
                            'sort': [1645081429754]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'pJp-Bn8BDVkhsHlSmdSC',
                            '_score': None,
                            '_source': {
                                'value': 0.8921428741290338,
                                'tags': {
                                    'iteration': 6
                                }
                            },
                            'sort': [1645081434496]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': '-5t-Bn8BDVkhsHlSqyrd',
                            '_score': None,
                            '_source': {
                                'value': 0.9041610187629308,
                                'tags': {
                                    'iteration': 7
                                }
                            },
                            'sort': [1645081439195]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'PZt-Bn8BDVkhsHlSvn4y',
                            '_score': None,
                            '_source': {
                                'value': 0.9179270409740553,
                                'tags': {
                                    'iteration': 8
                                }
                            },
                            'sort': [1645081443888]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': '7pt-Bn8BDVkhsHlS0csC',
                            '_score': None,
                            '_source': {
                                'value': 0.928827495184419,
                                'tags': {
                                    'iteration': 9
                                }
                            },
                            'sort': [1645081448704]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'VJx-Bn8BDVkhsHlS4y3-',
                            '_score': None,
                            '_source': {
                                'value': 0.9439282062257736,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1645081453564]
                        }]
                    }
                }
            }
        },
        'ABS': {
            'doc_count': 0,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            },
            'TRAIN': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            }
        },
        'TN': {
            'doc_count': 10,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            },
            'TRAIN': {
                'doc_count': 10,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 10,
                            'relation': 'eq'
                        },
                        'max_score':
                            None,
                        'hits': [{
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'wpl-Bn8BDVkhsHlSOwtF',
                            '_score': None,
                            '_source': {
                                'value': 771.0,
                                'tags': {
                                    'iteration': 1
                                }
                            },
                            'sort': [1645081410370]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'f5l-Bn8BDVkhsHlSTmZo',
                            '_score': None,
                            '_source': {
                                'value': 771.0,
                                'tags': {
                                    'iteration': 2
                                }
                            },
                            'sort': [1645081415270]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'k5l-Bn8BDVkhsHlSYcPm',
                            '_score': None,
                            '_source': {
                                'value': 770.0,
                                'tags': {
                                    'iteration': 3
                                }
                            },
                            'sort': [1645081420260]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'Q5p-Bn8BDVkhsHlSdBpj',
                            '_score': None,
                            '_source': {
                                'value': 773.0,
                                'tags': {
                                    'iteration': 4
                                }
                            },
                            'sort': [1645081424993]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'xpp-Bn8BDVkhsHlShnT8',
                            '_score': None,
                            '_source': {
                                'value': 774.0,
                                'tags': {
                                    'iteration': 5
                                }
                            },
                            'sort': [1645081429754]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'p5p-Bn8BDVkhsHlSmdSC',
                            '_score': None,
                            '_source': {
                                'value': 773.0,
                                'tags': {
                                    'iteration': 6
                                }
                            },
                            'sort': [1645081434496]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': '_pt-Bn8BDVkhsHlSqyrd',
                            '_score': None,
                            '_source': {
                                'value': 775.0,
                                'tags': {
                                    'iteration': 7
                                }
                            },
                            'sort': [1645081439195]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'QJt-Bn8BDVkhsHlSvn4y',
                            '_score': None,
                            '_source': {
                                'value': 780.0,
                                'tags': {
                                    'iteration': 8
                                }
                            },
                            'sort': [1645081443888]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': '8Zt-Bn8BDVkhsHlS0csC',
                            '_score': None,
                            '_source': {
                                'value': 779.0,
                                'tags': {
                                    'iteration': 9
                                }
                            },
                            'sort': [1645081448704]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'V5x-Bn8BDVkhsHlS4y3-',
                            '_score': None,
                            '_source': {
                                'value': 781.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1645081453564]
                        }]
                    }
                }
            }
        },
        'TP': {
            'doc_count': 10,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            },
            'TRAIN': {
                'doc_count': 10,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 10,
                            'relation': 'eq'
                        },
                        'max_score':
                            None,
                        'hits': [{
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'wZl-Bn8BDVkhsHlSOwtF',
                            '_score': None,
                            '_source': {
                                'value': 86.0,
                                'tags': {
                                    'iteration': 1
                                }
                            },
                            'sort': [1645081410370]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'fpl-Bn8BDVkhsHlSTmZo',
                            '_score': None,
                            '_source': {
                                'value': 91.0,
                                'tags': {
                                    'iteration': 2
                                }
                            },
                            'sort': [1645081415270]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'kpl-Bn8BDVkhsHlSYcPm',
                            '_score': None,
                            '_source': {
                                'value': 98.0,
                                'tags': {
                                    'iteration': 3
                                }
                            },
                            'sort': [1645081420260]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'Qpp-Bn8BDVkhsHlSdBpj',
                            '_score': None,
                            '_source': {
                                'value': 99.0,
                                'tags': {
                                    'iteration': 4
                                }
                            },
                            'sort': [1645081424993]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'xZp-Bn8BDVkhsHlShnT8',
                            '_score': None,
                            '_source': {
                                'value': 112.0,
                                'tags': {
                                    'iteration': 5
                                }
                            },
                            'sort': [1645081429754]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'ppp-Bn8BDVkhsHlSmdSC',
                            '_score': None,
                            '_source': {
                                'value': 110.0,
                                'tags': {
                                    'iteration': 6
                                }
                            },
                            'sort': [1645081434496]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': '_Zt-Bn8BDVkhsHlSqyrd',
                            '_score': None,
                            '_source': {
                                'value': 109.0,
                                'tags': {
                                    'iteration': 7
                                }
                            },
                            'sort': [1645081439195]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'P5t-Bn8BDVkhsHlSvn4y',
                            '_score': None,
                            '_source': {
                                'value': 115.0,
                                'tags': {
                                    'iteration': 8
                                }
                            },
                            'sort': [1645081443888]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': '8Jt-Bn8BDVkhsHlS0csC',
                            '_score': None,
                            '_source': {
                                'value': 117.0,
                                'tags': {
                                    'iteration': 9
                                }
                            },
                            'sort': [1645081448704]
                        }, {
                            '_index': 'metrics_v2-2022.02.16-000010',
                            '_type': '_doc',
                            '_id': 'Vpx-Bn8BDVkhsHlS4y3-',
                            '_score': None,
                            '_source': {
                                'value': 121.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1645081453564]
                        }]
                    }
                }
            }
        },
        'MSRE': {
            'doc_count': 0,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            },
            'TRAIN': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            }
        },
        'MSE': {
            'doc_count': 0,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            },
            'TRAIN': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            }
        }
    }
}

fake_es_query_eval_tree_metrics_result = {
    'took': 202,
    'timed_out': False,
    '_shards': {
        'total': 4,
        'successful': 4,
        'skipped': 0,
        'failed': 0
    },
    'hits': {
        'total': {
            'value': 80,
            'relation': 'eq'
        },
        'max_score': None,
        'hits': []
    },
    'aggregations': {
        'ACC': {
            'doc_count': 8,
            'EVAL': {
                'doc_count': 8,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 8,
                            'relation': 'eq'
                        },
                        'max_score':
                            None,
                        'hits': [{
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'R8d4kX8Bft9MydwO744D',
                            '_score': None,
                            '_source': {
                                'value': 0.792236328125,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413096191]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'pqV4kX8BPdYgu5bg9fKY',
                            '_score': None,
                            '_source': {
                                'value': 0.810791015625,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413097876]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'sUV4kX8BHocuEQgl-vL9',
                            '_score': None,
                            '_source': {
                                'value': 0.796142578125,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413099258]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'u0V5kX8BHocuEQglAfIo',
                            '_score': None,
                            '_source': {
                                'value': 0.7973116377785638,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413100836]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': '2qh5kX8BdTI5PJt-CJEU',
                            '_score': None,
                            '_source': {
                                'value': 0.806396484375,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413102609]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'Ucd5kX8Bft9MydwODo6l',
                            '_score': None,
                            '_source': {
                                'value': 0.80224609375,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413104290]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'ieN5kX8BxCxOvEoxFTIT',
                            '_score': None,
                            '_source': {
                                'value': 0.802734375,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413105935]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': '5Kh5kX8BdTI5PJt-GZHE',
                            '_score': None,
                            '_source': {
                                'value': 0.8078552175587216,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413107136]
                        }]
                    }
                }
            },
            'TRAIN': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            }
        },
        'FN': {
            'doc_count': 8,
            'EVAL': {
                'doc_count': 8,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 8,
                            'relation': 'eq'
                        },
                        'max_score':
                            None,
                        'hits': [{
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'UMd4kX8Bft9MydwO744D',
                            '_score': None,
                            '_source': {
                                'value': 746.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413096191]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'r6V4kX8BPdYgu5bg9fKY',
                            '_score': None,
                            '_source': {
                                'value': 692.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413097876]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'ukV4kX8BHocuEQgl-vL9',
                            '_score': None,
                            '_source': {
                                'value': 740.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413099258]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'xEV5kX8BHocuEQglAfIo',
                            '_score': None,
                            '_source': {
                                'value': 504.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413100836]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': '46h5kX8BdTI5PJt-CJEU',
                            '_score': None,
                            '_source': {
                                'value': 681.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413102609]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'Wsd5kX8Bft9MydwODo6l',
                            '_score': None,
                            '_source': {
                                'value': 705.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413104290]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'kuN5kX8BxCxOvEoxFTIT',
                            '_score': None,
                            '_source': {
                                'value': 701.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413105935]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': '7ah5kX8BdTI5PJt-GZHE',
                            '_score': None,
                            '_source': {
                                'value': 429.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413107136]
                        }]
                    }
                }
            },
            'TRAIN': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            }
        },
        'KS': {
            'doc_count': 8,
            'EVAL': {
                'doc_count': 8,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 8,
                            'relation': 'eq'
                        },
                        'max_score':
                            None,
                        'hits': [{
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'TMd4kX8Bft9MydwO744D',
                            '_score': None,
                            '_source': {
                                'value': 0.3645519339138261,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413096191]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'q6V4kX8BPdYgu5bg9fKY',
                            '_score': None,
                            '_source': {
                                'value': 0.3804289511482969,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413097876]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'tkV4kX8BHocuEQgl-vL9',
                            '_score': None,
                            '_source': {
                                'value': 0.4052552047443612,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413099258]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'wEV5kX8BHocuEQglAfIo',
                            '_score': None,
                            '_source': {
                                'value': 0.3894954124503266,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413100836]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': '36h5kX8BdTI5PJt-CJEU',
                            '_score': None,
                            '_source': {
                                'value': 0.3670764787932738,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413102609]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'Vsd5kX8Bft9MydwODo6l',
                            '_score': None,
                            '_source': {
                                'value': 0.3761368377138089,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413104290]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'juN5kX8BxCxOvEoxFTIT',
                            '_score': None,
                            '_source': {
                                'value': 0.3470963824157124,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413105935]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': '6ah5kX8BdTI5PJt-GZHE',
                            '_score': None,
                            '_source': {
                                'value': 0.377164202014282,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413107136]
                        }]
                    }
                }
            },
            'TRAIN': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            }
        },
        'RECALL': {
            'doc_count': 8,
            'EVAL': {
                'doc_count': 8,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 8,
                            'relation': 'eq'
                        },
                        'max_score':
                            None,
                        'hits': [{
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'Scd4kX8Bft9MydwO744D',
                            '_score': None,
                            '_source': {
                                'value': 0.2021390374331551,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413096191]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'qKV4kX8BPdYgu5bg9fKY',
                            '_score': None,
                            '_source': {
                                'value': 0.22681564245810057,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413097876]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 's0V4kX8BHocuEQgl-vL9',
                            '_score': None,
                            '_source': {
                                'value': 0.20600858369098712,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413099258]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'vUV5kX8BHocuEQglAfIo',
                            '_score': None,
                            '_source': {
                                'value': 0.2112676056338028,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413100836]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': '3Kh5kX8BdTI5PJt-CJEU',
                            '_score': None,
                            '_source': {
                                'value': 0.2348314606741573,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413102609]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'U8d5kX8Bft9MydwODo6l',
                            '_score': None,
                            '_source': {
                                'value': 0.21666666666666667,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413104290]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'i-N5kX8BxCxOvEoxFTIT',
                            '_score': None,
                            '_source': {
                                'value': 0.2043132803632236,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413105935]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': '5qh5kX8BdTI5PJt-GZHE',
                            '_score': None,
                            '_source': {
                                'value': 0.2393617021276596,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413107136]
                        }]
                    }
                }
            },
            'TRAIN': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            }
        },
        'FP': {
            'doc_count': 8,
            'EVAL': {
                'doc_count': 8,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 8,
                            'relation': 'eq'
                        },
                        'max_score':
                            None,
                        'hits': [{
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'T8d4kX8Bft9MydwO744D',
                            '_score': None,
                            '_source': {
                                'value': 105.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413096191]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'rqV4kX8BPdYgu5bg9fKY',
                            '_score': None,
                            '_source': {
                                'value': 83.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413097876]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'uUV4kX8BHocuEQgl-vL9',
                            '_score': None,
                            '_source': {
                                'value': 95.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413099258]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'w0V5kX8BHocuEQglAfIo',
                            '_score': None,
                            '_source': {
                                'value': 69.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413100836]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': '4qh5kX8BdTI5PJt-CJEU',
                            '_score': None,
                            '_source': {
                                'value': 112.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413102609]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'Wcd5kX8Bft9MydwODo6l',
                            '_score': None,
                            '_source': {
                                'value': 105.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413104290]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'keN5kX8BxCxOvEoxFTIT',
                            '_score': None,
                            '_source': {
                                'value': 107.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413105935]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': '7Kh5kX8BdTI5PJt-GZHE',
                            '_score': None,
                            '_source': {
                                'value': 70.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413107136]
                        }]
                    }
                }
            },
            'TRAIN': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            }
        },
        'F1': {
            'doc_count': 8,
            'EVAL': {
                'doc_count': 8,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 8,
                            'relation': 'eq'
                        },
                        'max_score':
                            None,
                        'hits': [{
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'Ssd4kX8Bft9MydwO744D',
                            '_score': None,
                            '_source': {
                                'value': 0.3075671277461351,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413096191]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'qaV4kX8BPdYgu5bg9fKY',
                            '_score': None,
                            '_source': {
                                'value': 0.3437764606265876,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413097876]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'tEV4kX8BHocuEQgl-vL9',
                            '_score': None,
                            '_source': {
                                'value': 0.3150123051681706,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413099258]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'vkV5kX8BHocuEQglAfIo',
                            '_score': None,
                            '_source': {
                                'value': 0.3202846975088967,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413100836]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': '3ah5kX8BdTI5PJt-CJEU',
                            '_score': None,
                            '_source': {
                                'value': 0.34516928158546656,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413102609]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'VMd5kX8Bft9MydwODo6l',
                            '_score': None,
                            '_source': {
                                'value': 0.32499999999999996,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413104290]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'jON5kX8BxCxOvEoxFTIT',
                            '_score': None,
                            '_source': {
                                'value': 0.30821917808219174,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413105935]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': '56h5kX8BdTI5PJt-GZHE',
                            '_score': None,
                            '_source': {
                                'value': 0.3511053315994798,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413107136]
                        }]
                    }
                }
            },
            'TRAIN': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            }
        },
        'PRECISION': {
            'doc_count': 8,
            'EVAL': {
                'doc_count': 8,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 8,
                            'relation': 'eq'
                        },
                        'max_score':
                            None,
                        'hits': [{
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'SMd4kX8Bft9MydwO744D',
                            '_score': None,
                            '_source': {
                                'value': 0.6428571428571429,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413096191]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'p6V4kX8BPdYgu5bg9fKY',
                            '_score': None,
                            '_source': {
                                'value': 0.7097902097902098,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413097876]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'skV4kX8BHocuEQgl-vL9',
                            '_score': None,
                            '_source': {
                                'value': 0.6689895470383276,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413099258]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'vEV5kX8BHocuEQglAfIo',
                            '_score': None,
                            '_source': {
                                'value': 0.6617647058823529,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413100836]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': '26h5kX8BdTI5PJt-CJEU',
                            '_score': None,
                            '_source': {
                                'value': 0.6510903426791277,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413102609]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'Usd5kX8Bft9MydwODo6l',
                            '_score': None,
                            '_source': {
                                'value': 0.65,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413104290]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'iuN5kX8BxCxOvEoxFTIT',
                            '_score': None,
                            '_source': {
                                'value': 0.627177700348432,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413105935]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': '5ah5kX8BdTI5PJt-GZHE',
                            '_score': None,
                            '_source': {
                                'value': 0.6585365853658537,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413107136]
                        }]
                    }
                }
            },
            'TRAIN': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            }
        },
        'AUC': {
            'doc_count': 8,
            'EVAL': {
                'doc_count': 8,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 8,
                            'relation': 'eq'
                        },
                        'max_score':
                            None,
                        'hits': [{
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'S8d4kX8Bft9MydwO744D',
                            '_score': None,
                            '_source': {
                                'value': 0.7464538569159221,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413096191]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'qqV4kX8BPdYgu5bg9fKY',
                            '_score': None,
                            '_source': {
                                'value': 0.749997294839776,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413097876]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'tUV4kX8BHocuEQgl-vL9',
                            '_score': None,
                            '_source': {
                                'value': 0.7596473266848613,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413099258]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'v0V5kX8BHocuEQglAfIo',
                            '_score': None,
                            '_source': {
                                'value': 0.760564095521739,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413100836]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': '3qh5kX8BdTI5PJt-CJEU',
                            '_score': None,
                            '_source': {
                                'value': 0.7533225973771089,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413102609]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'Vcd5kX8Bft9MydwODo6l',
                            '_score': None,
                            '_source': {
                                'value': 0.7539168752607426,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413104290]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'jeN5kX8BxCxOvEoxFTIT',
                            '_score': None,
                            '_source': {
                                'value': 0.7379395321660138,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413105935]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': '6Kh5kX8BdTI5PJt-GZHE',
                            '_score': None,
                            '_source': {
                                'value': 0.7488383167104478,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413107136]
                        }]
                    }
                }
            },
            'TRAIN': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            }
        },
        'ABS': {
            'doc_count': 0,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            },
            'TRAIN': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            }
        },
        'TN': {
            'doc_count': 8,
            'EVAL': {
                'doc_count': 8,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 8,
                            'relation': 'eq'
                        },
                        'max_score':
                            None,
                        'hits': [{
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'Tsd4kX8Bft9MydwO744D',
                            '_score': None,
                            '_source': {
                                'value': 3056.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413096191]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'raV4kX8BPdYgu5bg9fKY',
                            '_score': None,
                            '_source': {
                                'value': 3118.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413097876]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'uEV4kX8BHocuEQgl-vL9',
                            '_score': None,
                            '_source': {
                                'value': 3069.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413099258]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'wkV5kX8BHocuEQglAfIo',
                            '_score': None,
                            '_source': {
                                'value': 2119.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413100836]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': '4ah5kX8BdTI5PJt-CJEU',
                            '_score': None,
                            '_source': {
                                'value': 3094.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413102609]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'WMd5kX8Bft9MydwODo6l',
                            '_score': None,
                            '_source': {
                                'value': 3091.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413104290]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'kON5kX8BxCxOvEoxFTIT',
                            '_score': None,
                            '_source': {
                                'value': 3108.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413105935]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': '66h5kX8BdTI5PJt-GZHE',
                            '_score': None,
                            '_source': {
                                'value': 1963.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413107136]
                        }]
                    }
                }
            },
            'TRAIN': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            }
        },
        'TP': {
            'doc_count': 8,
            'EVAL': {
                'doc_count': 8,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 8,
                            'relation': 'eq'
                        },
                        'max_score':
                            None,
                        'hits': [{
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'Tcd4kX8Bft9MydwO744D',
                            '_score': None,
                            '_source': {
                                'value': 189.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413096191]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'rKV4kX8BPdYgu5bg9fKY',
                            '_score': None,
                            '_source': {
                                'value': 203.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413097876]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 't0V4kX8BHocuEQgl-vL9',
                            '_score': None,
                            '_source': {
                                'value': 192.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413099258]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'wUV5kX8BHocuEQglAfIo',
                            '_score': None,
                            '_source': {
                                'value': 135.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413100836]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': '4Kh5kX8BdTI5PJt-CJEU',
                            '_score': None,
                            '_source': {
                                'value': 209.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413102609]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'V8d5kX8Bft9MydwODo6l',
                            '_score': None,
                            '_source': {
                                'value': 195.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413104290]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': 'j-N5kX8BxCxOvEoxFTIT',
                            '_score': None,
                            '_source': {
                                'value': 180.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413105935]
                        }, {
                            '_index': 'metrics_v2-2022.03.12-000035',
                            '_type': '_doc',
                            '_id': '6qh5kX8BdTI5PJt-GZHE',
                            '_score': None,
                            '_source': {
                                'value': 135.0,
                                'tags': {
                                    'iteration': 10
                                }
                            },
                            'sort': [1647413107136]
                        }]
                    }
                }
            },
            'TRAIN': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            }
        },
        'MSRE': {
            'doc_count': 0,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            },
            'TRAIN': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            }
        },
        'MSE': {
            'doc_count': 0,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            },
            'TRAIN': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': []
                    }
                }
            }
        }
    }
}

fake_es_query_tree_metrics_result_v2 = {
    'took': 38,
    'timed_out': False,
    '_shards': {
        'total': 72,
        'successful': 72,
        'skipped': 0,
        'failed': 0
    },
    'hits': {
        'total': {
            'value': 160,
            'relation': 'eq'
        },
        'max_score': None,
        'hits': []
    },
    'aggregations': {
        'ACC': {
            'doc_count': 160,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': [],
                    }
                },
            },
            'TRAIN': {
                'doc_count': 10,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 10,
                            'relation': 'eq'
                        },
                        'max_score':
                            3.7822056,
                        'hits': [
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'viMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.acc': 0.857,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 1,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'zyMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.acc': 0.895,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 8,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '3SMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.acc': 0.868,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 3,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '7yMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.acc': 0.862,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 2,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '-iMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.acc': 0.883,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 6,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'UxAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.acc': 0.886,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 5,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'WRAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.acc': 0.872,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 4,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'XhAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.acc': 0.884,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 7,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'dBAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.acc': 0.896,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 9,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'FCMeHoEBwUXAbMGy-DsO',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.acc': 0.902,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 10,
                                    },
                                },
                            },
                        ],
                    }
                },
            },
        },
        'FN': {
            'doc_count': 160,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': [],
                    }
                },
            },
            'TRAIN': {
                'doc_count': 10,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 10,
                            'relation': 'eq'
                        },
                        'max_score':
                            3.7822056,
                        'hits': [
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'qiMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.fn': 116,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 3,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'qyMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.fn': 105,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 7,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'zCMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.fn': 102,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 5,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '5yMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.fn': 123,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 2,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '7SMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.fn': 97,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 9,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'VxAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.fn': 99,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 8,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'ZRAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.fn': 115,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 4,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'bRAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.fn': 128,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 1,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'bhAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.fn': 104,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 6,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'FSMeHoEBwUXAbMGy-DsO',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.fn': 93,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 10,
                                    },
                                },
                            },
                        ],
                    }
                },
            },
        },
        'KS': {
            'doc_count': 160,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': [],
                    }
                },
            },
            'TRAIN': {
                'doc_count': 10,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 10,
                            'relation': 'eq'
                        },
                        'max_score':
                            3.7822056,
                        'hits': [
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'qSMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.ks': 0.5469192171410906,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 3,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'siMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.ks': 0.6989964566835509,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 8,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'uCMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.ks': 0.5349813321918623,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 2,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'uSMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.ks': 0.7088535349932226,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 9,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '0iMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.ks': 0.5992009702504102,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 5,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '8yMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.ks': 0.47770564314760644,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 1,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '9CMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.ks': 0.6175715202967825,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 6,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'BiMeHoEBwUXAbMGy8jt4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.ks': 0.6366317091151221,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 7,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'cRAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.ks': 0.5596894247461416,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 4,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'DSMeHoEBwUXAbMGy-DsO',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.ks': 0.7418848541057288,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 10,
                                    },
                                },
                            },
                        ],
                    }
                },
            },
        },
        'RECALL': {
            'doc_count': 160,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': [],
                    }
                },
            },
            'TRAIN': {
                'doc_count': 10,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 10,
                            'relation': 'eq'
                        },
                        'max_score':
                            3.7822056,
                        'hits': [
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'wyMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.recall': 0.40186915887850466,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 1,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'ySMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.recall': 0.5373831775700935,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 8,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '8SMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.recall': 0.4252336448598131,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 2,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '8iMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.recall': 0.45794392523364486,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 3,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '-SMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.recall': 0.46261682242990654,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 4,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '-yMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.recall': 0.5467289719626168,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 9,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'VhAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.recall': 0.5233644859813084,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 5,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'axAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.recall': 0.5093457943925234,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 7,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'dRAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.recall': 0.514018691588785,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 6,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'ECMeHoEBwUXAbMGy-DsO',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.recall': 0.5654205607476636,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 10,
                                    },
                                },
                            },
                        ],
                    }
                },
            },
        },
        'FP': {
            'doc_count': 160,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': [],
                    }
                },
            },
            'TRAIN': {
                'doc_count': 10,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 10,
                            'relation': 'eq'
                        },
                        'max_score':
                            3.7822056,
                        'hits': [
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'pyMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.fp': 15,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 1,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'tCMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.fp': 16,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 3,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'wCMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.fp': 6,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 8,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '1CMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.fp': 15,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 2,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '2yMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.fp': 13,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 4,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '5iMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.fp': 12,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 5,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'AyMeHoEBwUXAbMGy8jt4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.fp': 13,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 6,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'TxAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.fp': 11,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 7,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'eBAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.fp': 7,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 9,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'EiMeHoEBwUXAbMGy-DsO',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.fp': 5,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 10,
                                    },
                                },
                            },
                        ],
                    }
                },
            },
        },
        'F1': {
            'doc_count': 160,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': [],
                    }
                },
            },
            'TRAIN': {
                'doc_count': 10,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 10,
                            'relation': 'eq'
                        },
                        'max_score':
                            3.7822056,
                        'hits': [
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'pCMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.f1': 0.5975609756097561,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 3,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'sCMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.f1': 0.6627218934911242,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 5,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'xCMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.f1': 0.6528189910979227,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 6,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'yiMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.f1': 0.6923076923076923,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 9,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '0CMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.f1': 0.546031746031746,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 1,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '1iMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.f1': 0.56875,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 2,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'BCMeHoEBwUXAbMGy8jt4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.f1': 0.6526946107784432,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 7,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'bBAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.f1': 0.607361963190184,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 4,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'dhAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.f1': 0.6865671641791044,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 8,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'CyMeHoEBwUXAbMGy-DsO',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.f1': 0.711764705882353,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 10,
                                    },
                                },
                            },
                        ],
                    }
                },
            },
        },
        'PRECISION': {
            'doc_count': 160,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': [],
                    }
                },
            },
            'TRAIN': {
                'doc_count': 10,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 10,
                            'relation': 'eq'
                        },
                        'max_score':
                            3.7822056,
                        'hits': [
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'oyMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.precision': 0.8584905660377359,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 2,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '1SMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.precision': 0.8596491228070176,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 3,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '3iMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.precision': 0.9083333333333333,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 7,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '5CMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.precision': 0.8839285714285714,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 4,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '5SMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.precision': 0.9435483870967742,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 9,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '8CMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.precision': 0.8943089430894309,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 6,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '9yMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.precision': 0.9032258064516129,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 5,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '-CMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.precision': 0.9504132231404959,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 8,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'XxAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.precision': 0.8514851485148515,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 1,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'DyMeHoEBwUXAbMGy-DsO',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.precision': 0.9603174603174603,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 10,
                                    },
                                },
                            },
                        ],
                    }
                },
            },
        },
        'AUC': {
            'doc_count': 160,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': [],
                    }
                },
            },
            'TRAIN': {
                'doc_count': 10,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 10,
                            'relation': 'eq'
                        },
                        'max_score':
                            3.7822056,
                        'hits': [
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'pSMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.auc': 0.8797977455946351,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 5,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'sSMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.auc': 0.9041610187629308,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 7,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'xSMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.auc': 0.860663242253454,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 4,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '0SMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.auc': 0.8533328577203871,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 3,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '1yMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.auc': 0.928827495184419,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 9,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'BSMeHoEBwUXAbMGy8jt4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.auc': 0.8377684240565029,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 2,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'VBAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.auc': 0.8921428741290338,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 6,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'YBAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.auc': 0.8011640626857863,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 1,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'ZBAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.auc': 0.9179270409740553,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 8,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'DCMeHoEBwUXAbMGy-DsO',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.auc': 0.9439282062257736,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 10,
                                    },
                                },
                            },
                        ],
                    }
                },
            },
        },
        'ABS': {
            'doc_count': 160,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': [],
                    }
                },
            },
            'TRAIN': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': [],
                    }
                },
            },
        },
        'TN': {
            'doc_count': 160,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': [],
                    }
                },
            },
            'TRAIN': {
                'doc_count': 10,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 10,
                            'relation': 'eq'
                        },
                        'max_score':
                            3.7822056,
                        'hits': [
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'syMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.tn': 775,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 7,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'yyMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.tn': 770,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 3,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '_iMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.tn': 771,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 2,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'AiMeHoEBwUXAbMGy8jt4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.tn': 779,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 9,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'TRAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.tn': 774,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 5,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'WhAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.tn': 771,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 1,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'YhAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.tn': 773,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 6,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'YxAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.tn': 780,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 8,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'dxAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.tn': 773,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 4,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'ESMeHoEBwUXAbMGy-DsO',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.tn': 781,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 10,
                                    },
                                },
                            },
                        ],
                    }
                },
            },
        },
        'TP': {
            'doc_count': 160,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': [],
                    }
                },
            },
            'TRAIN': {
                'doc_count': 10,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 10,
                            'relation': 'eq'
                        },
                        'max_score':
                            3.7822056,
                        'hits': [
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'uiMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.tp': 99,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 4,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'vyMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.tp': 115,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 8,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '0yMeHoEBwUXAbMGy8jph',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.tp': 86,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 1,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '2iMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.tp': 117,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 9,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '6yMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.tp': 98,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 3,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': '_CMeHoEBwUXAbMGy8jp4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.tp': 91,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 2,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'ASMeHoEBwUXAbMGy8jt4',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.tp': 109,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 7,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'YRAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.tp': 112,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 5,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'aBAeHoEBFisd-m428sSP',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.tp': 110,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 6,
                                    },
                                },
                            },
                            {
                                '_index': 'apm-7.16.0-metric-000002',
                                '_type': '_doc',
                                '_id': 'DiMeHoEBwUXAbMGy-DsO',
                                '_score': 3.7822056,
                                '_source': {
                                    'values.model.train.tree_vertical.tp': 121,
                                    'labels': {
                                        'k8s_job_name': 'ue1d22f070d634ae494d-tree-model',
                                        'iteration': 10,
                                    },
                                },
                            },
                        ],
                    }
                },
            },
        },
        'MSRE': {
            'doc_count': 160,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': [],
                    }
                },
            },
            'TRAIN': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': [],
                    }
                },
            },
        },
        'MSE': {
            'doc_count': 160,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': [],
                    }
                },
            },
            'TRAIN': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': [],
                    }
                },
            },
        },
    },
}

fake_es_query_nn_metrics_result_v2 = {
    'aggregations': {
        'LOSS': {
            'meta': {},
            'doc_count': 10,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': [],
                    }
                },
            },
            'TRAIN': {
                'doc_count': 1,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 1,
                            'relation': 'eq'
                        },
                        'max_score':
                            3.902454,
                        'hits': [{
                            '_index': 'apm-7.16.0-metric-000001',
                            '_type': '_doc',
                            '_id': 'ffB9sIIBX3IR_A7a36a2',
                            '_score': 3.902454,
                            '_source': {
                                '@timestamp': '2022-08-18T10:26:54.467Z',
                                'values.model.train.nn_vertical.loss': 5.694229602813721,
                                'labels': {
                                    'k8s_job_name': 'u30d9521ce4b34c1f8f0-nn-model'
                                },
                            },
                        }],
                    }
                },
            },
        },
        'AUC': {
            'meta': {},
            'doc_count': 10,
            'EVAL': {
                'doc_count': 0,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 0,
                            'relation': 'eq'
                        },
                        'max_score': None,
                        'hits': [],
                    }
                },
            },
            'TRAIN': {
                'doc_count': 1,
                'TOP': {
                    'hits': {
                        'total': {
                            'value': 1,
                            'relation': 'eq'
                        },
                        'max_score':
                            3.902454,
                        'hits': [{
                            '_index': 'apm-7.16.0-metric-000001',
                            '_type': '_doc',
                            '_id': 'fvB9sIIBX3IR_A7a36a2',
                            '_score': 3.902454,
                            '_source': {
                                '@timestamp': '2022-08-18T10:26:54.467Z',
                                'values.model.train.nn_vertical.auc': 0.6585884094238281,
                                'labels': {
                                    'k8s_job_name': 'u30d9521ce4b34c1f8f0-nn-model'
                                },
                            },
                        }],
                    }
                },
            },
        },
    },
}
