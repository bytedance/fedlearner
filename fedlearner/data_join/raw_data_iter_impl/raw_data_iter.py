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
import logging
from collections import OrderedDict
import fedlearner.data_join.common as common
from fedlearner.common.db_client import DBClient
from fedlearner.data_join.raw_data_iter_impl.validator import Validator


class RawDataIter(object):
    class Item(object):
        def __init__(self):
            # please modify the set according to alphabetical order.
            # event_time is event_time_shallow
            self._features = OrderedDict()

        @property
        def record(self):
            return self._features

        @property
        def tf_record(self):
            raise NotImplementedError(
                    "tf_record not implement for basic Item"
                )

        @property
        def csv_record(self):
            raise NotImplementedError(
                    "csv_record not implement for basic Item"
                )

        def add_extra_fields(self, additional_records, cache=False):
            raise NotImplementedError(
                "add_extra_fields not implemented for basic Item"
            )

        @classmethod
        def make(cls, example_id, event_time, raw_id, fname=None, fvalue=None):
            raise NotImplementedError("make not implemented for basic Item")

        def __getattr__(self, item):
            if item not in self._features and common.ALLOWED_FIELDS[item].must:
                logging.warning("%s misses field %s:%s",
                                self.__class__.__name__,
                                item, common.ALLOWED_FIELDS[item])
            value = self._features.get(
                item, common.ALLOWED_FIELDS[item].default_value)
            if not isinstance(value, common.ALLOWED_FIELDS[item].type):
                value = common.ALLOWED_FIELDS[item].type(value)
            return value

        def __getitem__(self, item):
            return self._features[item]

        def __setitem__(self, item, value):
            self._features[item] = value

        def __contains__(self, item):
            return item in self._features

        # Because Item has implemented __getattr__, the two methods below are
        # necessary. These are the default __getstate__ and __setstate__.
        def __getstate__(self):
            return self.__dict__

        def __setstate__(self, state):
            self.__dict__ = state

    def __init__(self, options):
        self._fiter = None
        self._index_meta = None
        self._item = None
        self._index = None
        self._iter_failed = False
        self._options = options

        try:
            self._validator = Validator(options.validation_ratio)
        except AttributeError:
            self._validator = Validator()
        #_options will be None for example id visitor
        if self._options and self._options.raw_data_cache_type == "disk":
            #use leveldb to manager the disk storage by default
            self._cache_type = DBClient("leveldb", False)
        else:
            self._cache_type = None

    def reset_iter(self, index_meta=None, force=False):
        if index_meta != self._index_meta or self._iter_failed or force:
            self._fiter = None
            self._index_meta = None
            self._item = None
            self._index = None
            self._fiter, self._item = self._reset_iter(index_meta)
            self._index_meta = index_meta
            self._index = None if index_meta is None \
                    else index_meta.start_index
        self._iter_failed = False

    def seek_to_target(self, target_index):
        self._check_valid()
        if self._index_meta.start_index > target_index:
            raise IndexError(
                    "target index {} < start index {}".format(
                    target_index, self._index_meta.start_index)
                )
        try:
            if self._index == target_index:
                return
            if self._iter_failed or self._index > target_index:
                self.reset_iter(self._index_meta, True)
            if self._index < target_index:
                for index, _ in self:
                    if index == target_index:
                        return
        except Exception as e: # pylint: disable=broad-except
            logging.warning(
                    "%s failed to seek file %s to index %d, reason %s",
                    self.__class__.__name__,
                    self._index_meta.fpath, target_index, e
                )
            self._iter_failed = True
            raise

    @classmethod
    def name(cls):
        return 'raw_data_iter'

    def __iter__(self):
        return self

    def __next__(self):
        self._check_valid()
        if self._iter_failed:
            self.seek_to_target(self._index)
        try:
            self._item = self._next()
        except StopIteration:
            logging.debug("file %s is EOF", self._index_meta.fpath)
            raise
        except Exception as e: # pylint: disable=broad-except
            logging.warning(
                    "%s failed to next iter %s to %d, reason %s",
                    self.__class__.__name__,
                    self._index_meta.fpath, self._index + 1, e
                )
            self._iter_failed = True
            raise
        self._index += 1
        return self._index, self._item

    def next(self):
        return self.__next__()

    def get_index(self):
        self._check_valid()
        return self._index

    def get_item(self):
        self._check_valid()
        return self._item

    def _reset_iter(self, index_meta):
        raise NotImplementedError(
                "_reset_iter not implement for class %s" %
                RawDataIter.name()
            )

    def _next(self):
        assert self._fiter is not None, "_fiter must be not None in _next"
        return next(self._fiter)

    def _check_valid(self):
        assert self._fiter is not None
        assert self._index_meta is not None
        assert self._item is not None
        assert self._index is not None
