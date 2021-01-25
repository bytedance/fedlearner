import copy
import logging
import random
from collections import defaultdict
from datetime import datetime
from itertools import chain

import fedlearner.common.data_join_service_pb2 as dj_pb
from fedlearner.common import metrics


class OptionalStats:
    """
    Cumulative stats for optional fields in data join, will count total joined
        num and total num of different values of every optional stats field.
        E.g., for optional field=`label`, the values of field `label` will be
        0(positive example) and 1(negative_example):
        {
            'joined': {
                # '#None#' for examples without label field
                'label_1': 123,
                'label_0': 345,
                'label_#None#': 45
                ...
            },
            'unjoined': {
                'label_1': 234,
                'label_0': 456,
                'label_#None#': 56
                ...
            }
        }
        then there are 123 positives joined, with a total of 234 positives;
        345 negatives joined, with a total of 456 negatives;
        45 examples without `label` field joined, with a total of 56 examples
        without `label` field.
    This will only count local examples as optional fields are not transmitted
        from peer.
    If raw_data_options.sample_unjoined = True, will sample unjoined example ids
        based on reservoir sampling.
    """

    def __init__(self, raw_data_options, metric_tags):
        """
        Args:
            raw_data_options: dj_pb.RawDataOptions. A protobuf containing
                optional stats options and arguments.
        """
        assert isinstance(raw_data_options, dj_pb.RawDataOptions)
        self._stats_fields = raw_data_options.optional_fields
        self._stats = {
            'joined': defaultdict(int),
            'unjoined': defaultdict(int)
        }
        self._sample_reservoir = []
        self._sample_receive_num = 0
        self._reservoir_length = 10
        self._need_sample = raw_data_options.sample_unjoined
        self._tags = copy.deepcopy(metric_tags)

    def update_stats(self, item, kind='joined'):
        """
        Args:
            item: RawDataIter.Item. Item from iterating RawDataVisitor
            kind: str. 'joined' or 'unjoined'. Indicate where the item should be
                counted towards.

        Returns: None
        No-op if optional fields are not set in the raw data options, or empty
            optional_fields of raw data options.
        """
        assert kind in ('joined', 'unjoined')
        if kind == 'unjoined':
            self.sample_unjoined(item.example_id)
        item_stat = {'joined': int(kind == 'joined')}
        tags = copy.deepcopy(self._tags)
        for field in self._stats_fields:
            value = self._convert_from_bytes(getattr(item, field, '#None#'))
            item_stat[field] = value
            self._stats[kind]['{}={}'.format(field, value)] += 1
        tags.update(item_stat)
        tags['example_id'] = self._convert_from_bytes(item.example_id)
        tags['raw_id'] = self._convert_from_bytes(item.raw_id)
        tags['event_time'] = self._convert_from_bytes(item.event_time)
        tags['timestamp'] = self._convert_to_timestamp(item.event_time)
        metrics.emit_store(name='datajoin', value=0, tags=tags)

    def emit_optional_stats(self, metrics_tags=None):
        """
        Args:
            metrics_tags: dict. Metrics tags for Kibana.

        Returns: None
        Emit the result to ES or logger. Clear the reservoir for next block.
        field_and_value: a `field`_`value` pair, e.g., for field = `label`,
            field_and_value may be `label_1`, `label_0` and `label_#None#`
        """
        field_and_values = list(set(chain(
            self._stats['joined'].keys(), self._stats['unjoined'].keys()
        )))
        field_and_values.sort()  # for better order in logging
        for field_and_value in field_and_values:
            joined_count = self._stats['joined'][field_and_value]
            unjoined_count = self._stats['unjoined'][field_and_value]
            tags = copy.deepcopy(metrics_tags)
            tags.update({'optional_stat_count': field_and_value})
            self._emit_metrics(
                joined_count, unjoined_count, field_and_value, tags)
        if self._need_sample:
            logging.info('Unjoined example ids: %s',
                         self._sample_reservoir)
            self._sample_reservoir = []
            self._sample_receive_num = 0

    def sample_unjoined(self, example_id):
        """
        Args:
            example_id: bytes. example_id to be sampled into the reservoir.

        Returns: None
        Sample example_id based on reservoir sampling. For N example_ids to be
            sampled, each id has a probability of self._reservoir_length / N to
            be eventually sampled.
        """
        if self._need_sample:
            if len(self._sample_reservoir) < self._reservoir_length:
                self._sample_reservoir.append(example_id)
                self._sample_receive_num += 1
                return
            reservoir_idx = random.randint(0, self._sample_receive_num)
            if reservoir_idx < self._reservoir_length:
                self._sample_reservoir[reservoir_idx] = example_id
                self._sample_receive_num += 1

    @staticmethod
    def _convert_to_timestamp(value):
        """
        Args:
            value: bytes | str | int | float. Value to be converted.

        Returns: int.
        Try to convert a datetime str to timestamp. First try to convert based
            on the length of str. If this str does not match any datetime format
            supported, return the default timestamp 0. If value is already
            numeric, convert to float WITHOUT checking if it is a valid timestamp.
        """
        if isinstance(value, bytes):
            value = value.decode()
        assert isinstance(value, (str, int, float))
        # first try to parse datetime from value
        if isinstance(value, str):
            try:
                if len(value) == 8:
                    value = datetime.timestamp(
                        datetime.strptime(value, '%Y%m%d')
                    )
                elif len(value) == 14:
                    value = datetime.timestamp(
                        datetime.strptime(value, '%Y%m%d%H%M%S')
                    )
            except ValueError:  # Not fitting any of above patterns
                pass
        # then try to convert directly
        try:
            value = float(value)
        except ValueError:  # might be a non-number str
            value = 0.
        return value

    @staticmethod
    def _convert_from_bytes(value):
        if isinstance(value, bytes):
            value = value.decode()
        return value

    @staticmethod
    def _emit_metrics(joined_count, unjoined_count, field_value, metrics_tags):
        total_count = joined_count + unjoined_count
        join_rate = joined_count / max(total_count, 1) * 100
        metrics.emit_store(name='{}_total_num'.format(field_value),
                           value=total_count,
                           tags=metrics_tags)
        metrics.emit_store(name='{}_join_num'.format(field_value),
                           value=joined_count,
                           tags=metrics_tags)
        metrics.emit_store(name='{}_join_rate_percent'.format(field_value),
                           value=join_rate,
                           tags=metrics_tags)
        logging.info(
            'Cumulative stats of `%s`:\n '
            'total: %d, joined: %d, unjoined: %d, join_rate: %f',
            field_value, total_count, joined_count, unjoined_count, join_rate
        )
