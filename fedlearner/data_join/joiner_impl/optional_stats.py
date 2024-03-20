import copy
import logging
import random
from collections import defaultdict
from datetime import datetime
from itertools import chain

import pytz

import fedlearner.data_join.common as djc
import fedlearner.common.data_join_service_pb2 as dj_pb
from fedlearner.common.common import convert_to_datetime
from fedlearner.common.metrics import emit, Config


class OptionalStats(object):
    """
    Cumulative stats for optional fields in data join, will count total joined
        num and total num of different values of every optional stats field.
    This will only stat local examples as optional fields are not transmitted
        from peer. Each Item has a possibility of `self._sample_rate` to be
        emitted to ES.
    """

    def __init__(self, raw_data_options, metric_tags):
        """
        Args:
            raw_data_options: dj_pb.RawDataOptions. A protobuf containing
                optional stats options and arguments.
        """
        assert isinstance(raw_data_options, dj_pb.RawDataOptions)
        self._sample_reservoir = []
        self._sample_receive_num = 0
        self._reservoir_length = 10
        self._tags = copy.deepcopy(metric_tags)
        for k in list(self._tags.keys()):
            if k not in ('application_id', 'partition'):
                self._tags.pop(k)
        allowed_fields = {'label', 'type', 'joined'}
        optional_fields = set(raw_data_options.optional_fields)
        # prevent from adding too many fields to ES index
        self._stat_fields = optional_fields & allowed_fields
        self._sample_rate = Config.DATA_JOIN_METRICS_SAMPLE_RATE
        self._kind_map = {'unjoined': -1,
                          'fake': 0,
                          'joined': 1}
        # reversed map
        self._map_kind = {v: k for k, v in self._kind_map.items()}
        self._stats = {
            joined: defaultdict(int) for joined in self._kind_map.values()
        }

    def update_stats(self, item, kind='joined'):
        """
        Args:
            item: RawDataIter.Item. Item from iterating RawDataVisitor
            kind: str. 'joined', 'unjoined', 'fake'. Indicate where the item
                should be counted towards.

        Returns: None
        Update stats dict. Emit join status and other fields of each item to ES.
        """
        assert kind in ('joined', 'unjoined', 'fake')
        joined = getattr(item, 'joined', self._kind_map[kind])
        assert isinstance(joined, int)
        if joined == -1:
            self.sample_unjoined(item.example_id)
        item_stat = {'joined': joined}
        for field in self._stat_fields:
            value = self._convert_to_str(getattr(item, field, '#None#'))
            item_stat[field] = value
            self._stats[joined]['{}={}'.format(field, value)] += 1
        if random.random() < self._sample_rate:
            tags = copy.deepcopy(self._tags)
            tags.update(item_stat)
            if item.event_time != djc.InvalidEventTime:
                tags['event_time'] = convert_to_datetime(
                    item.event_time, True
                ).isoformat(timespec='microseconds')
            tags['process_time'] = datetime.now(tz=pytz.utc) \
                .isoformat(timespec='microseconds')
            emit(name='', value=0, tags=tags, index_type='data_join')

    def emit_optional_stats(self):
        """
        Emit the stats to logger. Clear the reservoir for next block.
        field_and_value: a `field`_`value` pair, e.g., for field = `label`,
            field_and_value may be `label_1`, `label_0` and `label_#None#`
        """
        # set union and deduplicate
        field_and_values = list(set(chain.from_iterable(
            iter(self._stats[v].keys()) for v in self._kind_map.values()
        )))
        field_and_values.sort()  # for better order in logging
        for field_and_value in field_and_values:
            joined_count = self._stats[1][field_and_value]
            fake_count = self._stats[0][field_and_value]
            unjoined_count = self._stats[-1][field_and_value]
            total_count = joined_count + unjoined_count
            fake_total_count = total_count + fake_count
            join_rate = joined_count / max(total_count, 1) * 100
            fake_join_rate = (joined_count + fake_count) / \
                             max(fake_total_count, 1) * 100
            logging.info(
                'Cumulative stats of `%s`:\n '
                'total: %d, joined: %d, unjoined: %d, join rate: %f, '
                'total w/ fake: %d, joined w/ fake: %d, join rate w/ fake: %f',
                field_and_value,
                total_count, joined_count, unjoined_count, join_rate,
                fake_total_count, joined_count + fake_count, fake_join_rate
            )
        logging.info('Unjoined example ids: %s', self._sample_reservoir)
        self._sample_reservoir = []
        self._sample_receive_num = 0

    def sample_unjoined(self, example_id):
        """
        Args:
            example_id: bytes. example_id to be sampled into the reservoir.

        Returns: None
        Sample example_id based on Reservoir Sampling. For N example_ids to be
            sampled, each id has a probability of self._reservoir_length / N to
            be eventually sampled.
        """
        if len(self._sample_reservoir) < self._reservoir_length:
            self._sample_reservoir.append(example_id)
            self._sample_receive_num += 1
            return
        reservoir_idx = random.randint(0, self._sample_receive_num)
        if reservoir_idx < self._reservoir_length:
            self._sample_reservoir[reservoir_idx] = example_id
            self._sample_receive_num += 1

    @staticmethod
    def _convert_to_str(value):
        if isinstance(value, bytes):
            value = value.decode()
        return str(value)
