import os

import pytz

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
INDEX_NAME = {'metrics': 'metrics_v2',
              'data_join': 'data_join'}
INDEX_MAP = {'metrics': METRICS_INDEX,
             'data_join': DATA_JOIN_INDEX}
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
            # "lifecycle.name": "fedlearner_metrics_ilm",
            # "lifecycle.rollover_alias": "data_join"
        }
    },
    "mappings": DATA_JOIN_INDEX['mappings']
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
            # lifecycle is ES7 only and should be configured during deployment
            # "lifecycle.name": "fedlearner_metrics_ilm",
            # "lifecycle.rollover_alias": "metrics_v2"
        }
    },
    "mappings": METRICS_INDEX['mappings']
}
TEMPLATE_MAP = {'metrics': METRICS_TEMPLATE,
                'data_join': DATA_JOIN_TEMPLATE}
CONFIGS = {
    'data_join_metrics_sample_rate':
        os.environ.get('DATA_JOIN_METRICS_SAMPLE_RATE', 0.3),
    'es_batch_size': os.environ.get('ES_BATCH_SIZE', 1000),
    'timezone': pytz.timezone('Asia/Shanghai')
}
# ILM (Index Lifecycle Management) related. These are supposed to be set during
# deployment, rather than in actual jobs.
ILM_POLICY = {
    "policy": {
        "phases": {
            "hot": {
                "min_age": "0ms",
                "actions": {
                    "rollover": {
                        "max_age": "1d"
                    }
                }
            },
            "delete": {
                "min_age": "30d",
                "actions": {
                    "delete": {}
                }
            }
        }
    }
}
ILM_NAME = 'fedlearner_metrics_ilm'
