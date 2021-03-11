import datetime
import logging
import os

import pytz


class Config(object):
    DATA_JOIN_METRICS_SAMPLE_RATE = \
        os.environ.get('DATA_JOIN_METRICS_SAMPLE_RATE', 0.3),
    RAW_DATA_METRICS_SAMPLE_RATE = \
        os.environ.get('RAW_DATA_METRICS_SAMPLE_RATE', 0.01),
    ES_BATCH_SIZE = os.environ.get('ES_BATCH_SIZE', 1000),
    TIMEZONE = pytz.timezone(os.environ.get('TZ', 'UTC'))


# YYYY-MM-DD'T'hh:mm:ss.SSSSSSZ
_es_datetime_format = 'strict_date_optional_time'
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
        "tags": {
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
                }
            },
            "process_time": {
                "format": _es_datetime_format,
                "type": "date"
            }
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
        "tags": {
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
                },
                "process_time": {
                    "format": _es_datetime_format,
                    "type": "date"
                }
            }
        }
    }
}
INDEX_NAME = {'metrics': 'metrics_v2',
              'raw_data': 'raw_data',
              'data_join': 'data_join'}
INDEX_TYPE = INDEX_NAME.keys()
INDEX_MAP = {'metrics': METRICS_MAPPINGS,
             'raw_data': RAW_DATA_MAPPINGS,
             'data_join': DATA_JOIN_MAPPINGS}


def get_es_template(index_type, es_version):
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
                "number_of_shards": "1",
                "number_of_replicas": "1",
            }
        }
    }
    if es_version == 6:
        template['mappings'] = {'_doc': INDEX_MAP[index_type]}
    else:
        template['mappings'] = INDEX_MAP[index_type]
    return template


def convert_to_iso_format(value):
    """
    Args:
        value: datetime object | bytes | str | int | float.
            Value to be converted. Expected to be a numeric in the format of
            yyyymmdd or yyyymmddhhnnss, or a datetime object.

    Returns: str.
    Try to convert a datetime str or numeric to a UTC iso format str.
        1. Try to convert based on the length of str.
        2. Try to convert assuming it is a timestamp.
        3. If it does not match any pattern, return iso format of timestamp=0.
        Timezone will be set according to system TZ env if unset and
        then converted back to UTC.
    """
    assert isinstance(value, (datetime.datetime, bytes, str, int, float))
    if isinstance(value, datetime.datetime):
        if value.tzinfo is None:
            value = Config.TIMEZONE.localize(value)
        return pytz.utc.normalize(value).isoformat(timespec='microseconds')

    if isinstance(value, bytes):
        value = value.decode()
    elif isinstance(value, (int, float)):
        value = str(value)
    # first try to parse datetime from value
    try:
        if len(value) == 8:
            date_time = Config.TIMEZONE.localize(
                datetime.datetime.strptime(value, '%Y%m%d'))
            return pytz.utc.normalize(date_time) \
                .isoformat(timespec='microseconds')
        if len(value) == 14:
            date_time = Config.TIMEZONE.localize(
                datetime.datetime.strptime(value, '%Y%m%d%H%M%S'))
            return pytz.utc.normalize(date_time) \
                .isoformat(timespec='microseconds')
    except ValueError:  # Not fitting any of above patterns
        pass
    # then try to convert assuming it is a timestamp
    # not in the same `try` block b/c the length of some strings might be equal
    # to 14 but it is not a datetime format string
    try:
        date_time = datetime.datetime.fromtimestamp(float(value), tz=pytz.utc)
    except ValueError:  # might be a non-number str
        logging.warning('Unable to parse time %s to iso format, '
                        'defaults to 0.', value)
        date_time = datetime.datetime.fromtimestamp(0, tz=pytz.utc)
    return date_time.isoformat(timespec='microseconds')
