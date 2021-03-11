# TODO THIS FILE SHOULD BE MERGED WITH fedlearner.common.common
# TODO MIND THE SUBTLE DIFFERENCES DUE TO ES COMPATIBILITY WHEN MERGING
# YYYY-MM-DD'T'hh:mm:ss.SSSSSSZ
_es_datetime_format = 'strict_date_optional_time'
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
            "type": "short"
        },
        "application_id": {
            "ignore_above": 128,
            "type": "keyword"
        },
        "event_time": {
            "format": _es_datetime_format,
            "type": "date"
        },
        "process_time": {
            "format": _es_datetime_format,
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
            "type": "short"
        },
        "joined": {
            "type": "byte"
        },
        "label": {
            "ignore_above": 32,
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
            "format": _es_datetime_format,
            "type": "date"
        },
        "event_time": {
            "format": _es_datetime_format,
            "type": "date"
        }
    }
}
METRICS_MAPPINGS = {
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
        "name": {
            "type": "keyword"
        },
        "value": {
            "type": "float"
        },
        "date_time": {
            "format": _es_datetime_format,
            "type": "date"
        },
        "tags": {
            "properties": {
                "partition": {
                    "type": "short"
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
                "event_time": {
                    "type": "date",
                    "format": _es_datetime_format
                }
            }
        }
    }
}
ALIAS_NAME = {'metrics': 'metrics_v2',
              'raw_data': 'raw_data',
              'data_join': 'data_join'}
INDEX_MAP = {'metrics': METRICS_MAPPINGS,
             'raw_data': RAW_DATA_MAPPINGS,
             'data_join': DATA_JOIN_MAPPINGS}


def get_es_template(index_type, shards):
    assert index_type in ALIAS_NAME
    alias_name = ALIAS_NAME[index_type]
    template = {"index_patterns": ["{}-*".format(alias_name)],
                "settings": {
                    "index": {
                        "lifecycle": {
                            "name": "fedlearner_{}_ilm".format(index_type),
                            "rollover_alias": alias_name
                        },
                        "codec": "best_compression",
                        "routing": {
                            "allocation": {
                                "total_shards_per_node": "1"
                            }
                        },
                        "refresh_interval": "60s",
                        "number_of_shards": str(shards),
                        "number_of_replicas": "1",
                    }
                },
                'mappings': INDEX_MAP[index_type]}
    return template
