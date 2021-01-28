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
    This will only stat local examples as optional fields are not transmitted
        from peer. This will emit each Item's status to ES and sample unjoined
        Items.
    """

    def __init__(self, raw_data_options, metric_tags):
        """
        Args:
            raw_data_options: dj_pb.RawDataOptions. A protobuf containing
                optional stats options and arguments.
        """
        assert isinstance(raw_data_options, dj_pb.RawDataOptions)
        self._stat_fields = raw_data_options.optional_fields
        self._stats = {
            'joined': defaultdict(int),
            'unjoined': defaultdict(int)
        }
        self._sample_reservoir = []
        self._sample_receive_num = 0
        self._reservoir_length = 10
        self._tags = copy.deepcopy(metric_tags)

    def update_stats(self, item, kind='joined'):
        """
        Args:
            item: RawDataIter.Item. Item from iterating RawDataVisitor
            kind: str. 'joined' or 'unjoined'. Indicate where the item should be
                counted towards.

        Returns: None
        Update stats dict. Emit join status and other fields of each item to ES.
        """
        assert kind in ('joined', 'unjoined')
        if kind == 'unjoined':
            self.sample_unjoined(item.example_id)
        item_stat = {'joined': int(kind == 'joined')}
        tags = copy.deepcopy(self._tags)
        for field in self._stat_fields:
            value = self._convert_to_str(getattr(item, field, '#None#'))
            item_stat[field] = value
            self._stats[kind]['{}={}'.format(field, value)] += 1
        tags.update(item_stat)
        tags['example_id'] = self._convert_to_str(item.example_id)
        tags['event_time'] = self._convert_to_str(item.event_time)
        tags['event_time_iso'] = self._convert_to_iso_format(item.event_time)
        metrics.emit_store(name='datajoin', value=0, tags=tags)

    def emit_optional_stats(self):
        """
        Emit the stats to logger. Clear the reservoir for next block.
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
            total_count = joined_count + unjoined_count
            join_rate = joined_count / max(total_count, 1) * 100
            logging.info(
                'Cumulative stats of `%s`:\n '
                'total: %d, joined: %d, unjoined: %d, join_rate: %f',
                field_and_value, total_count, joined_count, unjoined_count,
                join_rate
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
    def _convert_to_iso_format(value):
        """
        Args:
            value: bytes | str | int | float. Value to be converted. Expected to
                be a numeric in the format of yyyymmdd or yyyymmddhhnnss.

        Returns: str.
        Try to convert a datetime str or numeric to iso format datetime str.
            First try to convert based on the length of str. If it does not
            match any datetime format supported, convert the value assuming it
            is a timestamp. If the value is not a timestamp, return iso format
            of timestamp=0.
        """
        assert isinstance(value, (bytes, str, int, float))
        if isinstance(value, bytes):
            value = value.decode()
        elif isinstance(value, (int, float)):
            value = str(value)
        # first try to parse datetime from value
        try:
            if len(value) == 8:
                iso = datetime.strptime(value, '%Y%m%d').isoformat()
            elif len(value) == 14:
                iso = datetime.strptime(value, '%Y%m%d%H%M%S').isoformat()
            else:
                raise ValueError
            return iso
        except ValueError:  # Not fitting any of above patterns
            logging.info('OPTIONAL_STATS: event time %s not converted '
                         'correctly.', value)
            # then try to convert directly
            try:
                iso = datetime.fromtimestamp(float(value)).isoformat()
            except ValueError:  # might be a non-number str
                logging.info('OPTIONAL_STATS: unable to parse event time %s, '
                             'defaults to 0.', value)
                iso = datetime.fromtimestamp(0).isoformat()
            return iso

    @staticmethod
    def _convert_to_str(value):
        if isinstance(value, bytes):
            value = value.decode()
        return str(value)
