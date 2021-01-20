import logging
import random
from collections import defaultdict

import fedlearner.common.data_join_service_pb2 as dj_pb
from fedlearner.common import metrics
from fedlearner.data_join import common

POOL_LENGTH = 10


class OptionalStats:
    """
    Cumulative stats for optional fields in data join, will count total joined
        num and total num of different values of every optional stats field.
        E.g., for optional field=`label`, the values of field `label` will be
        0(positive example) and 1(negative_example):
        {
            'joined': {
                # '__None__' for examples without label field
                'label': {'1': 123, '0': 345, '__None__': 45},
                'other_field': {...},
                ...
            },
            'total': {
                'label': {'1': 234, '0': 456, '__None__': 56}
                'other_field': {...},
                ...
            }
        }
        then there are 123 positives joined, with a total of 234 positives;
        345 negatives joined, with a total of 456 negatives;
        45 examples without `label` field joined, with a total of 56 examples
        without `label` field.
    This will only count local examples as optional fields are not transmitted
        from peer.
    """

    def __init__(self, raw_data_options, meta=None):
        """
        Args:
            raw_data_options: list(str). A list of str which stands for the
                fields that need stats.
            meta: dj_pb.DataBlockMeta. DataBlockMeta from latest data block.
                Restore stats from it if it's not None.
        """
        assert isinstance(raw_data_options, dj_pb.RawDataOptions)
        self._stats_fields = \
            raw_data_options.optional_fields['optional_stats'].fields
        if meta is None:
            self._stats = {
                'joined': {stat_field: defaultdict(int)
                           for stat_field in self._stats_fields},
                'total': {stat_field: defaultdict(int)
                          for stat_field in self._stats_fields}
            }
        else:
            assert isinstance(meta, dj_pb.DataBlockMeta)
            stats_info = meta.joiner_stats_info
            self._stats = {
                'joined': {field: defaultdict(
                    int, stats_info.joined_optional_stats[field].counter)
                    for field in stats_info.joined_optional_stats},
                'total': {field: defaultdict(
                    int, stats_info.total_optional_stats[field].counter)
                    for field in stats_info.joined_optional_stats}
            }
        self._unjoined_example_id_pool = []
        self._pool_index = 0
        self._need_sample = raw_data_options.sample_unjoined

    def update_stats(self, item, kind='joined'):
        """
        Args:
            item: RawDataIter.Item. Item from iterating RawDataVisitor
            kind: str. 'joined' or 'total'. Indicate where the item should be
                counted towards.
        Returns: None
        No-op if optional fields are not set in the raw data options, or no
            `optional_stats` entry in the optional fields of raw data options.
        """
        if item.optional_fields == common.NoOptionalFields:
            return
        for field in self._stats_fields:
            self._stats[kind][field][item.optional_fields[field]] += 1

    def need_sample(self):
        """
        Returns: bool
        Whether needs sampling unjoined example ids.
        """
        return self._need_sample

    def need_stats(self):
        """
        Returns: bool.
        """
        return len(self._stats_fields) > 0

    def create_join_stats_info(self):
        """
        Returns: dj_pb.JoinerStatsInfo
        Gather all the stats accumulated and dump in a protobuf for data block
            dumping.
        """
        joined_map, total_map = {}, {}
        if len(self._stats_fields) > 0:
            for field, counter in self._stats['joined'].items():
                joined_map[field] = dj_pb.OptionalStatsCounter(counter=counter)
            for field, counter in self._stats['total'].items():
                total_map[field] = dj_pb.OptionalStatsCounter(counter=counter)
        return dj_pb.JoinerStatsInfo(joined_optional_stats=joined_map,
                                     total_optional_stats=total_map)

    def emit_optional_stats(self, metrics_tags=None):
        """
        Args:
            metrics_tags: dict. Metrics tag for Kibana.

        Returns: None
        Emit the result to ES or logger. Clear the unjoined pool for next block.
        """
        # will pass the for loop if total_optional_stats is empty
        for field, total_counter in self._stats['total'].items():
            joined_counter = self._stats['joined'][field]
            # overall joined and total example nums for each field
            overall_joined = 0
            overall_total = 0
            for value, total in total_counter.items():
                # total: total example nums for one value of this field
                # joined: joined example nums for one value of this field
                # E.g., 1 and 0 are two values of `label` field, for value = 1,
                # total = nums of all positive examples,
                # joined = nums of all joined positive examples.
                joined = joined_counter[value]
                overall_joined += joined
                overall_total += total
                prefix = '{f}_{v}'.format(f=field, v=value)
                join_rate = joined / max(total, 1) * 100
                self._emit_metrics(total, joined, prefix, metrics_tags)
                logging.info('Cumulative stats of `%s`:\n total: %d, '
                             'joined: %d, join_rate: %f',
                             prefix, total, joined, join_rate)
            total_join_rate = overall_joined / max(overall_total, 1) * 100
            self._emit_metrics(
                overall_total, overall_joined, field, metrics_tags
            )
            logging.info('Cumulative overall stats of field `%s`:\n '
                         'total: %d, joined: %d, join_rate: %f',
                         field, overall_total, overall_joined, total_join_rate)
        if self._need_sample:
            logging.info('Unjoined example ids: %s',
                         self._unjoined_example_id_pool)
            self._unjoined_example_id_pool = []
            self._pool_index = 0

    def add_unjoined(self, example_id):
        """
        Args:
            example_id: bytes. example_id to be sampled into the sample pool.

        Returns: None
        Sample example_id. For N example_id to be sampled, each has a
            probability of POOL_LENGTH / N to be eventually sampled.
        """
        if len(self._unjoined_example_id_pool) < POOL_LENGTH:
            self._unjoined_example_id_pool.append(example_id)
            self._pool_index += 1
            return
        insert_idx = random.randint(0, self._pool_index)
        if insert_idx < POOL_LENGTH:
            self._unjoined_example_id_pool[insert_idx] = example_id
            self._pool_index += 1

    @staticmethod
    def _emit_metrics(total_count, joined_count, prefix, metrics_tags):
        join_rate = joined_count / max(total_count, 1) * 100
        metrics.emit_store(name='{}_total_num'.format(prefix),
                           value=total_count,
                           tags=metrics_tags)
        metrics.emit_store(name='{}_join_num'.format(prefix),
                           value=joined_count,
                           tags=metrics_tags)
        metrics.emit_store(name='{}_join_rate_percent'.format(prefix),
                           value=join_rate,
                           tags=metrics_tags)
