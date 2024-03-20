import copy
import random
from datetime import datetime

import pytz

import fedlearner.data_join.common as djc
from fedlearner.common import metrics, common
from fedlearner.data_join.common import convert_to_str
from fedlearner.common.common import convert_to_datetime


class MetricStats:
    def __init__(self, raw_data_options, metric_tags):
        self._tags = copy.deepcopy(metric_tags)
        self._stat_fields = raw_data_options.optional_fields
        self._sample_ratio = common.Config.RAW_DATA_METRICS_SAMPLE_RATE

    def emit_metric(self, item):
        if random.random() < self._sample_ratio:
            tags = copy.deepcopy(self._tags)
            for field in self._stat_fields:
                value = convert_to_str(getattr(item, field, '#None#'))
                tags[field] = value
            if item.example_id != djc.InvalidExampleId:
                tags['example_id'] = convert_to_str(item.example_id)
            if item.event_time != djc.InvalidEventTime:
                tags['event_time'] = convert_to_datetime(
                    item.event_time, True
                ).isoformat(timespec='microseconds')

            tags['process_time'] = datetime.now(tz=pytz.utc) \
                .isoformat(timespec='microseconds')
            metrics.emit_store(name='input_data', value=0, tags=tags,
                               index_type='raw_data')
