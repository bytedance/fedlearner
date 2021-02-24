import os

import pytz

# WARNING: ARBITRARY MODIFICATIONS OF INDICES BELOW WILL RESULT IN HUGE USAGE OF
# ES DISK SPACE, PLEASE MODIFY WITH CAUTION. DO NOT MODIFY EXISTING FIELDS
# WITHOUT PERMISSION AND TEST, OTHERWISE ERRORS MIGHT OCCUR.
RAW_DATA_MAPPINGS = {
    "mappings": {
        "_doc": {
            "dynamic": True,
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
                "has_click_id": {
                    "type": "boolean"
                },
                "has_example_id": {
                    "type": "boolean"
                },
                "application_id": {
                    "ignore_above": 128,
                    "type": "keyword"
                }
            }
        }
    }
}
DATA_JOIN_MAPPINGS = {
    "mappings": {
        "_doc": {
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
}
METRICS_MAPPINGS = {
    "mappings": {
        "_doc": {
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
}
INDEX_NAME = {'metrics': 'metrics_v2',
              'raw_data': 'raw_data',
              'data_join': 'data_join'}
RAW_DATA_TEMPLATE = {
    "index_patterns": ["metrics_v2-*"],
    "settings": {
        "index": {
            "codec": "best_compression",
            "routing": {
                "allocation": {
                    "total_shards_per_node": "1"
                }
            },
            "refresh_interval": "60s",
            "number_of_shards": "2",
            "number_of_replicas": "1",
            # lifecycle should be configured during deployment
            # "lifecycle.name": "fedlearner_raw_data_ilm",
            # "lifecycle.rollover_alias": "metrics_v2"
        }
    },
    "mappings": RAW_DATA_MAPPINGS
}
DATA_JOIN_TEMPLATE = {
    "index_patterns": ["data_join-*"],
    "settings": {
        "index": {
            "codec": "best_compression",
            "routing": {
                "allocation": {
                    "total_shards_per_node": "1"
                }
            },
            "refresh_interval": "60s",
            "number_of_shards": "2",
            "number_of_replicas": "1",
            # "lifecycle.name": "fedlearner_data_join_ilm",
            # "lifecycle.rollover_alias": "data_join"
        }
    },
    "mappings": DATA_JOIN_MAPPINGS
}
METRICS_TEMPLATE = {
    "index_patterns": ["metrics_v2-*"],
    "settings": {
        "index": {
            "codec": "best_compression",
            "routing": {
                "allocation": {
                    "total_shards_per_node": "1"
                }
            },
            "refresh_interval": "60s",
            "number_of_shards": "2",
            "number_of_replicas": "1",
            # "lifecycle.name": "fedlearner_metrics_ilm",
            # "lifecycle.rollover_alias": "metrics_v2"
        }
    },
    "mappings": METRICS_MAPPINGS
}
TEMPLATE_MAP = {'metrics': METRICS_TEMPLATE,
                'raw_data': RAW_DATA_TEMPLATE,
                'data_join': DATA_JOIN_TEMPLATE}
CONFIGS = {
    'data_join_metrics_sample_rate':
        os.environ.get('DATA_JOIN_METRICS_SAMPLE_RATE', 0.3),
    'raw_data_metrics_sample_rate':
        os.environ.get('RAW_DATA_METRICS_SAMPLE_RATE', 0.01),
    'es_batch_size': os.environ.get('ES_BATCH_SIZE', 1000),
    'timezone': pytz.timezone('Asia/Shanghai')
}
