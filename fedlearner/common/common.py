import os

import pytz

INDEX_TYPE = ('metrics', 'data_join', 'raw_data')
# WARNING: MAPPINGS BELOW ARE COMPATIBILITY MEASURES AND SHOULD NOT BE MODIFIED.
RAW_DATA_MAPPINGS = {
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
        "application_id": {
            "ignore_above": 128,
            "type": "keyword"
        },
        "event_time": {
            "format": "strict_date_hour_minute_second",
            "type": "date"
        }
    }
}
DATA_JOIN_MAPPINGS = {
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
        "has_click_id": {
            "type": "boolean"
        },
        "has_example_id": {
            "type": "boolean"
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
METRICS_MAPPINGS = {
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
INDEX_NAME = {'metrics': 'metrics_v2',
              'raw_data': 'raw_data',
              'data_join': 'data_join'}
INDEX_MAP = {'metrics': METRICS_MAPPINGS,
             'raw_data': RAW_DATA_MAPPINGS,
             'data_join': DATA_JOIN_MAPPINGS}
CONFIGS = {
    'data_join_metrics_sample_rate':
        os.environ.get('DATA_JOIN_METRICS_SAMPLE_RATE', 0.3),
    'raw_data_metrics_sample_rate':
        os.environ.get('RAW_DATA_METRICS_SAMPLE_RATE', 0.01),
    'es_batch_size': os.environ.get('ES_BATCH_SIZE', 1000),
    'timezone': pytz.timezone('Asia/Shanghai')
}


def get_template(index_type, es_version):
    index_name = INDEX_NAME[index_type]
    template = {
        "index_patterns": ["{}-*".format(index_name), index_name],
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
            }
        }
    }
    if es_version == 6:
        template['mappings'] = {'_doc': INDEX_MAP[index_type]}
    else:
        template['mappings'] = INDEX_MAP[index_type]
    return template
