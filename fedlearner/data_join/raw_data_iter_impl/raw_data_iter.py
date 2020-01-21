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

    def __init__(self):
        self._fiter = None
        self._raw_data_rep = None
        self._item = None
        self._index = None

    def reset_iter(self, raw_data_rep=None):
        assert raw_data_rep.HasField('index')
        self._fiter = None
        self._raw_data_rep = None
        self._item = None
        self._index = None
        self._fiter, self._item = self._reset_iter(raw_data_rep)
        self._raw_data_rep = raw_data_rep
        if raw_data_rep is not None:
            self._index = raw_data_rep.index.start_index

    def seek_to_target(self, target_index):
        self._check_valid()
        if self._raw_data_rep.index.start_index > target_index:
            raise IndexError(
                    "target index {} < start index {}".format(
                    target_index, self._raw_data_rep.index.start_index)
                )
        if self._index > target_index:
            self.reset_iter(self._raw_data_rep)
        if self._index < target_index:
            for index, _ in self:
                if index == target_index:
                    return

    @classmethod
    def name(cls):
        return 'raw_data_iter'

    def __iter__(self):
        return self

    def __next__(self):
        self._check_valid()
        self._item = self._next()
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
        assert self._raw_data_rep is not None
        assert self._item is not None
        assert self._index is not None
