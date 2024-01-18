import datetime
import os
import logging

import pytz

from fedlearner.common import fl_logging


class Config(object):
    DATA_JOIN_METRICS_SAMPLE_RATE = \
        float(os.environ.get('DATA_JOIN_METRICS_SAMPLE_RATE', 0.3))
    RAW_DATA_METRICS_SAMPLE_RATE = \
        float(os.environ.get('RAW_DATA_METRICS_SAMPLE_RATE', 0.0))
    ES_BATCH_SIZE = int(float(os.environ.get('ES_BATCH_SIZE', 1000)))
    TZ = pytz.timezone(os.environ.get('TZ', 'UTC'))
    ES_USERNAME = os.environ.get('ES_USERNAME', 'elastic')
    ES_PASSWORD = os.environ.get('ES_PASSWORD', 'Fedlearner123')
    METRICS_TO_STDOUT = int(float(os.environ.get('METRICS_TO_STDOUT', 0)))


INVALID_DATETIME = datetime.datetime.fromtimestamp(0)
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
                },
                "process_time": {
                    "format": _es_datetime_format,
                    "type": "date"
                }
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


def convert_to_datetime(value, enable_tz=False):
    """
    Args:
        value: datetime object | bytes | str | int | float.
            Value to be converted. Expected to be a numeric in the format of
            yyyymmdd or yyyymmddhhnnss, or a datetime object.
        enable_tz: bool. whether converts to UTC and contains timezone info

    Returns: str.
    Try to convert a datetime str or numeric to a UTC iso format str.
        1. Try to convert based on the length of str.
        2. Try to convert assuming it is a timestamp.
        3. If it does not match any pattern, return iso format of timestamp=0.
        Timezone will be set according to system TZ env if unset and
        then converted back to UTC if enable_tz is True.
    """
    assert isinstance(value, (bytes, str, int, float))
    if isinstance(value, bytes):
        value = value.decode()
    elif isinstance(value, (int, float)):
        value = str(value)
    # 1. try to parse datetime from value
    try:
        date_time = convert_time_string_to_datetime(value)
    except ValueError:  # Not fitting any of above patterns
        # 2. try to convert assuming it is a timestamp
        # not in the same `try` block b/c the length of some strings might
        # be equal to 8 or 14 but it does not match any of the patterns
        try:
            date_time = datetime.datetime.fromtimestamp(float(value))
        except ValueError:  # might be a non-number str
            # 3. default to 0
            fl_logging.warning('Unable to parse time %s to iso format, '
                               'defaults to 0.', value)
            date_time = INVALID_DATETIME
    if enable_tz:
        date_time = set_timezone(date_time)
    return date_time


def set_timezone(date_time):
    if date_time.tzinfo is None:
        date_time = Config.TZ.localize(date_time)
    date_time = pytz.utc.normalize(date_time)
    return date_time


def convert_time_string_to_datetime(value):
    if len(value) == 8:
        date_time = datetime.datetime.strptime(value, '%Y%m%d')
    elif len(value) == 14:
        date_time = datetime.datetime.strptime(value, '%Y%m%d%H%M%S')
    else:
        raise ValueError
    return date_time


def set_logger():
    verbosity = os.environ.get('VERBOSITY', 1)
    if verbosity == 0:
        logging.getLogger().setLevel(logging.WARNING)
    elif verbosity == 1:
        logging.getLogger().setLevel(logging.INFO)
    elif verbosity > 1:
        logging.getLogger().setLevel(logging.DEBUG)
    logging.basicConfig(format="%(asctime)s %(filename)s "
                                "%(lineno)s %(levelname)s - %(message)s")


def time_diff(minuend, sub):
    """minuend and sub should be same time format and must be legal numeric.
    """
    ts_minuend = convert_to_datetime(minuend, enable_tz=False).timestamp()
    ts_sub = convert_to_datetime(sub, enable_tz=False).timestamp()
    return ts_minuend - ts_sub


def use_tls():
    enable = os.getenv("FL_GRPC_SGX_RA_TLS_ENABLE") == "on"
    if not enable:
        return False
    return True


def get_tf_config():
    return {
        "intra_op_parallelism_threads": \
            int(os.environ.get("INTRA_OP_PARALLELISM_THREADS", 16)),
        "inter_op_parallelism_threads": \
            int(os.environ.get("INTER_OP_PARALLELISM_THREADS", 16)),
        "grpc_server_channel_threads": \
            int(os.environ.get("GRPC_SERVER_CHANNEL_THREADS", 16))
    }
