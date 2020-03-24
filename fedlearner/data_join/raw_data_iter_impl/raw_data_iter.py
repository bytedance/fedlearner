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

class RawDataIter(object):
    class Item(object):
        @property
        def example_id(self):
            raise NotImplementedError(
                    "example_id not implement for basic Item"
                )

        @property
        def event_time(self):
            raise NotImplementedError(
                    "event_time not implement for basic Item"
                )

        @property
        def record(self):
            raise NotImplementedError(
                    "record not implement for basic Item"
                )

    def __init__(self, options):
        self._fiter = None
        self._index_meta = None
        self._item = None
        self._index = None
        self._iter_failed = False
        self._options = options

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
                    "Failed to seek file %s to index %d, reason %s",
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
                    "Failed to next iter %s to %d, reason %s",
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

    def _reset_iter(self):
        raise NotImplementedError(
                "not implement for _reset_iter for class %s" %
                RawDataIter.name()
            )

    def _next(self):
        raise NotImplementedError(
                "not implement for next for class %s" %
                RawDataIter.name()
            )

    def _check_valid(self):
        assert self._fiter is not None
        assert self._index_meta is not None
        assert self._item is not None
        assert self._index is not None
