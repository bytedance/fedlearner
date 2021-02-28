# Copyright 2020 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8

import os
import logging
import uuid
import threading
import time
from contextlib import contextmanager
from collections import OrderedDict
from collections import namedtuple
from datetime import datetime
from datetime import timezone

from guppy import hpy

import tensorflow_io # pylint: disable=unused-import
import tensorflow.compat.v1 as tf
from google.protobuf import text_format
from tensorflow.compat.v1 import gfile

import psutil

from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb

DataBlockSuffix = '.data'
DataBlockMetaSuffix = '.meta'
RawDataMetaPrefix = 'raw_data_'
RawDataPubSuffix = '.pub'
InvalidExampleId = ''.encode()
TmpFileSuffix = '.tmp'
DoneFileSuffix = '.done'
RawDataFileSuffix = '.rd'
InvalidEventTime = -9223372036854775808
InvalidRawId = ''.encode()  # deprecated in V2
InvalidBytes = ''.encode()
InvalidInt = -1

# must: both old and new version of raw data should have this field
ALLOWED_FIELD = namedtuple('ALLOW_FIELD', ['default_value', 'type', 'must'])
ALLOWED_FIELDS = dict({
    'example_id': ALLOWED_FIELD(InvalidExampleId, bytes, True),
    'event_time': ALLOWED_FIELD(InvalidEventTime, int, True),
    'index': ALLOWED_FIELD(InvalidInt, int, False),
    'event_time_deep': ALLOWED_FIELD(InvalidEventTime, int, False),
    'raw_id': ALLOWED_FIELD(InvalidRawId, bytes, False),
    'type': ALLOWED_FIELD(InvalidBytes, bytes, False),
    'id_type': ALLOWED_FIELD(InvalidBytes, bytes, False),
    'joined': ALLOWED_FIELD(InvalidInt, int, False),
    'click_id': ALLOWED_FIELD(InvalidBytes, bytes, False),
    'req_id': ALLOWED_FIELD(InvalidBytes, bytes, False),
    'label': ALLOWED_FIELD(InvalidInt, int, False),
    'cid': ALLOWED_FIELD(InvalidBytes, bytes, False)
})

@contextmanager
def make_tf_record_iter(fpath, options=None):
    record_iter = None
    expt = None
    try:
        record_iter = tf.io.tf_record_iterator(fpath, options)
        yield record_iter
    except Exception as e: # pylint: disable=broad-except
        logging.warning("Failed make tf_record_iterator for "\
                        "%s, reason %s", fpath, e)
        expt = e
    if record_iter is not None:
        del record_iter
    if expt is not None:
        raise expt

def partition_repr(partition_id):
    return 'partition_{:04}'.format(partition_id)

def encode_data_block_meta_fname(data_source_name,
                                 partition_id,
                                 data_block_index):
    return '{}.{}.{:08}{}'.format(
            data_source_name, partition_repr(partition_id),
            data_block_index, DataBlockMetaSuffix
        )

def encode_block_id(data_source_name, meta):
    return '{}.{}.{:08}.{}-{}'.format(
            data_source_name, partition_repr(meta.partition_id),
            meta.data_block_index, meta.start_time, meta.end_time
        )

def decode_block_id(block_id):
    segs = block_id.split('.')
    if len(segs) != 4:
        raise ValueError("{} invalid. Segmenet of block_id split "\
                          "by . shoud be 4".format(block_id))
    data_source_name = segs[0]
    partition_id = int(segs[1][len('partition_'):])
    data_block_index = int(segs[2])
    time_frame_segs = segs[3].split('-')
    if len(time_frame_segs) != 2:
        raise ValueError("{} invalid. Segmenet of time frame split "
                         "by - should be 2".format(block_id))
    start_time, end_time = int(time_frame_segs[0]), int(time_frame_segs[1])
    return {"data_source_name": data_source_name,
            "partition_id": partition_id,
            "data_block_index": data_block_index,
            "time_frame": (start_time, end_time)}

def encode_data_block_fname(data_source_name, meta):
    block_id = encode_block_id(data_source_name, meta)
    return '{}{}'.format(block_id, DataBlockSuffix)

def load_data_block_meta(meta_fpath):
    assert meta_fpath.endswith(DataBlockMetaSuffix)
    if not gfile.Exists(meta_fpath):
        return None
    with make_tf_record_iter(meta_fpath) as fitr:
        return text_format.Parse(next(fitr).decode(), dj_pb.DataBlockMeta())

def data_source_kvstore_base_dir(data_source_name):
    return os.path.join('data_source', data_source_name)

def retrieve_data_source(kvstore, data_source_name):
    kvstore_key = data_source_kvstore_base_dir(data_source_name)
    raw_data = kvstore.get_data(kvstore_key)
    if raw_data is None:
        raise ValueError("kvstore master key is None for {}".format(
            data_source_name)
        )
    return text_format.Parse(raw_data, common_pb.DataSource())

def commit_data_source(kvstore, data_source):
    kvstore_key = \
        data_source_kvstore_base_dir(data_source.data_source_meta.name)
    kvstore.set_data(kvstore_key, text_format.MessageToString(data_source))

def partition_manifest_kvstore_key(data_source_name, partition_id):
    return os.path.join(data_source_kvstore_base_dir(data_source_name),
                        'raw_data_dir', partition_repr(partition_id))

def raw_data_meta_kvstore_key(data_source_name, partition_id, process_index):
    manifest_kvstore_key = partition_manifest_kvstore_key(data_source_name,
                                                    partition_id)
    return os.path.join(manifest_kvstore_key,
                        '{}{:08}'.format(RawDataMetaPrefix, process_index))

def example_id_anchor_kvstore_key(data_source_name, partition_id):
    db_base_dir = data_source_kvstore_base_dir(data_source_name)
    return os.path.join(db_base_dir, 'dumped_example_id_anchor',
                        partition_repr(partition_id))

def raw_data_pub_kvstore_key(pub_base_dir, partition_id, process_index):
    return os.path.join(pub_base_dir, partition_repr(partition_id),
                        '{:08}{}'.format(process_index, RawDataPubSuffix))

_valid_basic_feature_type = (int, str, float)
def convert_dict_to_tf_example(src_dict):
    assert isinstance(src_dict, dict)
    tf_feature = {}
    for key, feature in src_dict.items():
        if not isinstance(key, str):
            raise RuntimeError('the key {}({}) of dict must a '\
                               'string'.format(key, type(key)))
        basic_type = type(feature)
        # all field value are type of str in csv format
        # convert field value into int if it's not bytes
        if basic_type == str and ALLOWED_FIELDS[key].type != bytes:
            if feature.lstrip('-').isdigit():
                feature = int(feature)
                basic_type = int
            else:
                try:
                    feature = float(feature)
                    basic_type = float
                except ValueError as e:
                    pass
        if isinstance(type(feature), list):
            if len(feature) == 0:
                logging.debug('skip %s since feature is empty list', key)
                continue
            basic_type = feature[0]
            if not all(isinstance(x, basic_type) for x in feature):
                raise RuntimeError('type of elements in feature of key {} '\
                                   'is not the same'.format(key))
        if not isinstance(feature, _valid_basic_feature_type):
            raise RuntimeError("feature type({}) of key {} is not support "\
                               "for tf Example".format(basic_type, key))
        if basic_type == int:
            value = feature if isinstance(feature, list) else [feature]
            tf_feature[key] = tf.train.Feature(
                int64_list=tf.train.Int64List(value=value))
        elif basic_type == str:
            value = [feat.encode() for feat in feature] if \
                     isinstance(feature, list) else [feature.encode()]
            tf_feature[key] = tf.train.Feature(
                bytes_list=tf.train.BytesList(value=value))
        else:
            assert basic_type == float
            value = feature if isinstance(feature, list) else [feature]
            tf_feature[key] = tf.train.Feature(
                float_list=tf.train.FloatList(value=value))
    return tf.train.Example(features=tf.train.Features(feature=tf_feature))

def convert_tf_example_to_dict(src_tf_example):
    assert isinstance(src_tf_example, tf.train.Example)
    dst_dict = OrderedDict()
    tf_feature = src_tf_example.features.feature
    for key, feat in tf_feature.items():
        if feat.HasField('int64_list'):
            csv_val = [item for item in feat.int64_list.value] # pylint: disable=unnecessary-comprehension
        elif feat.HasField('bytes_list'):
            csv_val = [item for item in feat.bytes_list.value] # pylint: disable=unnecessary-comprehension
        elif feat.HasField('float_list'):
            csv_val = [item for item in feat.float_list.value] #pylint: disable=unnecessary-comprehension
        else:
            assert False, "feat type must in int64, byte, float"
        assert isinstance(csv_val, list)
        dst_dict[key] = csv_val[0] if len(csv_val) == 1 else csv_val
    return dst_dict

def int2bytes(digit, byte_len, byteorder='little'):
    return int(digit).to_bytes(byte_len, byteorder)

def bytes2int(byte, byteorder='little'):
    return int.from_bytes(byte, byteorder)

def gen_tmp_fpath(fdir):
    return os.path.join(fdir, str(uuid.uuid1())+TmpFileSuffix)

def portal_kvstore_base_dir(portal_name):
    return os.path.join('portal', portal_name)

def portal_job_kvstore_key(portal_name, job_id):
    return os.path.join(portal_kvstore_base_dir(portal_name), 'job_dir',
                        '{:08}.pj'.format(job_id))

def portal_job_part_kvstore_key(portal_name, job_id, partition_id):
    return os.path.join(portal_job_kvstore_key(portal_name, job_id),
                        partition_repr(partition_id))

def portal_map_output_dir(map_base_dir, job_id):
    return os.path.join(map_base_dir, 'map_{:08}'.format(job_id))

def portal_reduce_output_dir(reduce_base_dir, job_id):
    return os.path.join(reduce_base_dir, 'reduce_{:08}'.format(job_id))

def data_source_data_block_dir(data_source):
    return os.path.join(data_source.output_base_dir, 'data_block')

def data_source_example_dumped_dir(data_source):
    return os.path.join(data_source.output_base_dir, 'example_dump')

class Singleton(type):
    _instances = {}
    _lck = threading.Lock()
    def __call__(cls, *args, **kwargs):
        with cls._lck:
            if cls not in cls._instances:
                cls._instances[cls] = super(Singleton, cls).__call__(*args,
                                                                     **kwargs)
            return cls._instances[cls]

class _MemUsageProxy(object, metaclass=Singleton):
    def __init__(self):
        self._lock = threading.Lock()
        self._mem_limit = int(os.environ.get('MEM_LIMIT', '17179869184'))
        self._reserved_mem = int(self._mem_limit * 0.5)
        if self._reserved_mem >= 2 << 30:
            self._reserved_mem = 2 << 30
        self._rss_mem_usage = 0
        self._rss_updated_tm = 0

    def check_heap_mem_water_level(self, heap_mem_usage, water_level_percent):
        with self._lock:
            avail_mem = self._mem_limit - self._reserved_mem
            return heap_mem_usage >= avail_mem * water_level_percent

    def check_rss_mem_water_level(self, water_level_percent):
        avail_mem = self._mem_limit - self._reserved_mem
        return self._update_rss_mem_usage() >= avail_mem * water_level_percent

    def get_heap_mem_usage(self):
        return hpy().heap().size

    def _update_rss_mem_usage(self):
        with self._lock:
            if time.time() - self._rss_updated_tm >= 0.25:
                self._rss_mem_usage = psutil.Process().memory_info().rss
                self._rss_updated_tm = time.time()
            return self._rss_mem_usage

def _get_mem_usage_proxy():
    return _MemUsageProxy()

class _HeapMemStats(object, metaclass=Singleton):
    class StatsRecord(object):
        def __init__(self, potential_mem_incr, stats_expiration_time):
            self._lock = threading.Lock()
            self._potential_mem_incr = potential_mem_incr
            self._stats_expiration_time = stats_expiration_time
            self._stats_ts = 0
            self._heap_mem_usage = 0

        def stats_expiration(self):
            return self._stats_ts <= 0 or \
                    (self._stats_expiration_time is not None and
                        time.time() - self._stats_ts >= \
                                self._stats_expiration_time)

        def update_stats(self):
            with self._lock:
                if self.stats_expiration():
                    self._heap_mem_usage = \
                        _get_mem_usage_proxy().get_heap_mem_usage()
                    self._stats_ts = time.time()

        def get_heap_mem_usage(self):
            return self._heap_mem_usage + self._potential_mem_incr

    def __init__(self, stats_expiration_time):
        self._lock = threading.Lock()
        self._stats_granular = 0
        self._stats_start_key = None
        self._stats_expiration_time = stats_expiration_time
        self._stats_map = {}

    def CheckOomRisk(self, stats_key,
                     water_level_percent,
                     potential_mem_incr=0):
        if not self._need_heap_stats(stats_key):
            return False
        inner_key = self._gen_inner_stats_key(stats_key)
        sr = None
        with self._lock:
            if inner_key not in self._stats_map:
                inner_key = self._gen_inner_stats_key(stats_key)
                self._stats_map[inner_key] = \
                        _HeapMemStats.StatsRecord(potential_mem_incr,
                                                  self._stats_expiration_time)
            sr = self._stats_map[inner_key]
            if not sr.stats_expiration():
                return _get_mem_usage_proxy().check_heap_mem_water_level(
                        sr.get_heap_mem_usage(),
                        water_level_percent
                    )
        assert sr is not None
        sr.update_stats()
        return _get_mem_usage_proxy().check_heap_mem_water_level(
                sr.get_heap_mem_usage(), water_level_percent
            )

    def _gen_inner_stats_key(self, stats_key):
        return int(stats_key // self._stats_granular * self._stats_granular)

    def _need_heap_stats(self, stats_key):
        with self._lock:
            if self._stats_granular <= 0 and \
                    _get_mem_usage_proxy().check_rss_mem_water_level(0.5):
                self._stats_granular = stats_key // 16
                self._stats_start_key = stats_key // 2
                if self._stats_granular <= 0:
                    self._stats_granular = 1
                logging.warning('auto turing the heap stats granular as %d',
                                self._stats_granular)
            return self._stats_granular > 0 and \
                    stats_key >= self._stats_start_key

def get_heap_mem_stats(stats_expiration_time):
    return _HeapMemStats(stats_expiration_time)


def interval_to_timestamp(itv):
    unit = ["Y", "M", "D", "H", "N", "S"]
    multiple = [3600*24*30*12, 3600*24*30, 3600*24, 3600, 60, 1]
    unit_order, unit_no = {}, {}
    for i, item in enumerate(unit):
        unit_order[item] = len(unit) - i
    s_no = ""
    prv_order = len(unit) + 1
    for c in itv:
        if c.isdigit():
            s_no += c
        else:
            c = c.upper()
            if c not in unit_order or prv_order <= unit_order[c]:
                return None
            unit_no[c] = s_no
            prv_order = unit_order[c]
            s_no = ""
    tmstmp = 0
    if len(s_no) > 0 and "S" not in unit_no:
        unit_no["S"] = s_no
    for i, item in enumerate(unit):
        if item in unit_no:
            tmstmp += int(unit_no[item]) * multiple[i]
    return tmstmp


def convert_to_iso_format(value):
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
        # then try to convert directly
        try:
            iso = datetime.fromtimestamp(float(value)).isoformat()
        except ValueError:  # might be a non-number str
            logging.warning('OPTIONAL_STATS: unable to parse event time %s, '
                            'defaults to 0.', value)
            iso = datetime.fromtimestamp(0).isoformat()
        return iso

def convert_to_str(value):
    if isinstance(value, bytes):
        value = value.decode()
    return str(value)


def _parse_hh_mm_ss_ff(tstr):
    # Parses things of the form HH[:MM[:SS[.fff[fff]]]]
    len_str = len(tstr)

    time_comps = [0, 0, 0, 0]
    pos = 0
    for comp in range(0, 3):
        if (len_str - pos) < 2:
            raise ValueError('Incomplete time component')

        time_comps[comp] = int(tstr[pos:pos+2])

        pos += 2
        next_char = tstr[pos:pos+1]

        if not next_char or comp >= 2:
            break

        if next_char != ':':
            raise ValueError('Invalid time separator: %c' % next_char)

        pos += 1

    if pos < len_str:
        #pylint: disable=no-else-raise
        if tstr[pos] != '.':
            raise ValueError('Invalid microsecond component')
        else:
            pos += 1

            len_remainder = len_str - pos
            if len_remainder not in (3, 6):
                raise ValueError('Invalid microsecond component')

            time_comps[3] = int(tstr[pos:])
            if len_remainder == 3:
                time_comps[3] *= 1000

    return time_comps

def _parse_isoformat_time(tstr):
    # Format supported is HH[:MM[:SS[.fff[fff]]]][+HH:MM[:SS[.ffffff]]]
    len_str = len(tstr)
    if len_str < 2:
        raise ValueError('Isoformat time too short')

    # This is equivalent to re.search('[+-]', tstr), but faster
    tz_pos = (tstr.find('-') + 1 or tstr.find('+') + 1)
    timestr = tstr[:tz_pos-1] if tz_pos > 0 else tstr

    time_comps = _parse_hh_mm_ss_ff(timestr)

    tzi = None
    if tz_pos > 0:
        tzstr = tstr[tz_pos:]

        # Valid time zone strings are:
        # HH:MM               len: 5
        # HH:MM:SS            len: 8
        # HH:MM:SS.ffffff     len: 15

        if len(tzstr) not in (5, 8, 15):
            raise ValueError('Malformed time zone string')

        tz_comps = _parse_hh_mm_ss_ff(tzstr)
        if all(x == 0 for x in tz_comps):
            tzi = timezone.utc
        else:
            tzsign = -1 if tstr[tz_pos - 1] == '-' else 1

            td = datetime.timedelta(hours=tz_comps[0], minutes=tz_comps[1],
                           seconds=tz_comps[2], microseconds=tz_comps[3])

            tzi = timezone(tzsign * td)

    time_comps.append(tzi)

    return time_comps

# Helpers for parsing the result of isoformat()
def _parse_isoformat_date(dtstr):
    # It is assumed that this function will only be called with a
    # string of length exactly 10, and (though this is not used) ASCII-only
    year = int(dtstr[0:4])
    if dtstr[4] != '-':
        raise ValueError('Invalid date separator: %s' % dtstr[4])

    month = int(dtstr[5:7])

    if dtstr[7] != '-':
        raise ValueError('Invalid date separator')

    day = int(dtstr[8:10])

    return [year, month, day]


def datetime_from_isformat(date_string):
    """Construct a datetime from the output of datetime.isoformat().
        backported from Python3.7
    """
    if not isinstance(date_string, str):
        raise TypeError('fromisoformat: argument must be str')

    # Split this at the separator
    dstr = date_string[0:10]
    tstr = date_string[11:]

    try:
        date_components = _parse_isoformat_date(dstr)
    except ValueError:
        raise ValueError(f'Invalid isoformat string: {date_string!r}')

    if tstr:
        try:
            time_components = _parse_isoformat_time(tstr)
        except ValueError:
            raise ValueError(f'Invalid isoformat string: {date_string!r}')
    else:
        time_components = [0, 0, 0, 0, None]

    return datetime(*(date_components + time_components))

def time_diff(minuend, sub):
    """minuend and sub should be same time format and must be legal numeric.
    """
    ts_minuend = datetime_from_isformat(
        convert_to_iso_format(minuend)).timestamp()
    ts_sub = datetime_from_isformat(convert_to_iso_format(sub)).timestamp()
    return ts_minuend - ts_sub
