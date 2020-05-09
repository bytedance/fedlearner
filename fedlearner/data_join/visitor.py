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

import bisect
import logging
import os
import threading

class IndexMeta(object):
    def __init__(self, process_index, start_index, fpath):
        self.process_index = process_index
        self.start_index = start_index
        self.fpath = fpath

    def __lt__(self, other):
        return self.start_index < other.start_index

    def __eq__(self, other):
        if not isinstance(other, IndexMeta):
            return False
        return self.process_index == other.process_index and \
                self.start_index == other.start_index and \
                self.fpath == other.fpath

class IndexMetaManager(object):
    def __init__(self, preload_metas):
        self._lock = threading.Lock()
        preload_metas = sorted(preload_metas,
                               key=lambda meta: meta.start_index)
        for index, index_meta in enumerate(preload_metas):
            if index != index_meta.process_index:
                logging.fatal("%s has error process index. expected %d",
                              index_meta.fpath, index)
                os._exit(-1) # pylint: disable=protected-access
        self._index_metas = preload_metas

    def get_index_metas(self):
        with self._lock:
            return self._index_metas

    def check_index_meta_by_process_index(self, process_index):
        raise NotImplementedError("Base IndexMetaManager not implement "\
                                  "check_index_meta_by_process_index")

    def get_index_meta_by_index(self, process_index, start_index):
        with self._lock:
            if process_index < 0 or process_index > len(self._index_metas):
                raise IndexError("{} is out if range".format(process_index))
            if process_index == 0:
                if start_index != 0:
                    raise IndexError("index should be 0 for index meta "\
                                     "of process index 0")
            else:
                prev_meta = self._index_metas[process_index-1]
                if prev_meta.start_index >= start_index:
                    raise ValueError("start_index should be incremental")
            if process_index == len(self._index_metas):
                index_meta = self._new_index_meta(process_index, start_index)
                if index_meta is None:
                    return None
                self._index_metas.append(index_meta)
            return self._index_metas[process_index]

    def _new_index_meta(self, process_index, start_index):
        raise NotImplementedError(
                "Base IndexMetaManager not implement _new_index_meta"
            )

class Visitor(object):
    def __init__(self, name, index_meta_manager):
        self._name = name
        self._index_mata_manager = index_meta_manager
        self._iter = None
        self._finished = False
        self._visited_max_index = None
        self._end_index = None
        self._process_index = None
        self._index_metas = []
        for index_meta in self._index_mata_manager.get_index_metas():
            self._append_index_meta(index_meta)

    def name(self):
        return self._name

    def seek(self, target_index):
        if self._finished:
            if self._visited_max_index is None or \
                    target_index > self._visited_max_index:
                raise StopIteration()
            if target_index == self._visited_max_index:
                assert self._iter is not None
                assert target_index == self._iter.get_index()
                return target_index, self._iter.get_item()
        if self._end_index is not None and \
                self._end_index < target_index:
            raise StopIteration()
        self._finished = False
        return self._seek_internal(target_index)

    def finished(self):
        return self._finished

    def reset(self):
        if self._iter is not None:
            del self._iter
        self._finished = False
        self._iter = None
        self._process_index = None

    def started(self):
        return self._iter is not None

    def active_visitor(self):
        raise NotImplementedError(
                "not implement active_visitor in base visitor"
            )

    def is_visitor_stale(self):
        return self._index_mata_manager.check_index_meta_by_process_index(
                len(self._index_metas)
            )

    def get_index(self):
        if self._iter is None:
            return 0
        return self._iter.get_index()

    def get_item(self):
        if self._iter is None:
            raise RuntimeError("visitor is not valid")
        return self._iter.get_item()

    def _seek_internal(self, target_index):
        if self._iter is not None and self._iter.get_index() == target_index:
            self._update_visited_max_index()
            return target_index, self._iter.get_item()
        tmp_index_meta = IndexMeta(0, target_index, '')
        process_index = bisect.bisect_left(self._index_metas, tmp_index_meta)
        if len(self._index_metas) > 0 and \
                (len(self._index_metas) == process_index or
                    self._index_metas[process_index].start_index >
                        target_index):
            process_index -= 1
            if process_index < 0:
                raise IndexError(
                        "target_index {} is too samll".format(target_index)
                    )
        start_index = 0
        if process_index < len(self._index_metas):
            start_index = self._index_metas[process_index].start_index
        return self._forward_to_target(process_index, start_index, target_index)

    def __iter__(self):
        return self

    def __next__(self):
        return self._next_internal()

    def next(self):
        return self._next_internal()

    def _next_internal(self):
        if self._finished:
            raise StopIteration()
        try:
            if self._iter is None:
                raise StopIteration()
            index, item = next(self._iter)
            self._update_visited_max_index()
            return index, item
        except StopIteration:
            process_index = 0 if self._process_index is None else \
                    self._process_index + 1
            next_index = 0 if self._iter is None else \
                    self._iter.get_index() + 1
            if self._end_index is not None and next_index > self._end_index:
                self._finished = True
                raise StopIteration()
            return self._forward_to_target(
                    process_index, next_index, next_index
                )

    def _forward_to_target(self, process_index, start_index, target_index):
        index_meta = None
        if process_index < len(self._index_metas):
            index_meta = self._index_metas[process_index]
        else:
            assert process_index == len(self._index_metas), \
                "the next required process index should consecutive, "\
                "{}(process_index) == {}(len(self._index_metas))".format(
                        process_index, len(self._index_metas)
                    )
            index_meta = self._index_mata_manager.get_index_meta_by_index(
                    process_index, start_index
                )
            if index_meta is None:
                self._finished = True
                raise StopIteration('need more index meta')
            self._append_index_meta(index_meta)
        assert index_meta.process_index == process_index, \
            "{}(index meta process index) != {}(process index)".format(
                    index_meta.process_index, process_index
                )
        assert index_meta.start_index == start_index, \
            "{}(index meta start index) != {}(start index)".format(
                    index_meta.start_index, start_index
                )
        self._reset_iter_by_index_meta(index_meta)
        self._process_index = process_index
        self._iter.seek_to_target(target_index)
        self._update_visited_max_index()
        current_index = self._iter.get_index()
        if current_index < target_index:
            return self._forward_to_target(process_index + 1,
                                           current_index + 1,
                                           target_index)
        assert current_index == target_index, \
            "the seeked index should equel to target index. "\
            "{}(seek index) != {}(target index)".format(current_index,
                                                        target_index)
        return current_index, self._iter.get_item()

    def _append_index_meta(self, index_meta):
        if len(self._index_metas) > 0:
            prev_meta = self._index_metas[-1]
            if prev_meta.start_index >= index_meta.start_index:
                logging.fatal("index between index meta is not incremental")
                os._exit(-1) # pylint: disable=protected-access
        elif index_meta.start_index != 0:
            logging.fatal("the start index of first meta should be 0")
            os._exit(-1) # pylint: disable=protected-access
        self._index_metas.append(index_meta)

    def _update_visited_max_index(self):
        if self._iter is None:
            return
        if self._visited_max_index is None or \
                self._iter.get_index() > self._visited_max_index:
            self._visited_max_index = self._iter.get_index()

    def _reset_iter_by_index_meta(self, index_meta):
        assert index_meta is not None, "the input index meta should not None"
        _iter = self._iter
        if _iter is None:
            _iter = self._new_iter()
        _iter.reset_iter(index_meta)
        self._iter = _iter

    def _new_iter(self):
        raise NotImplementedError("_new_iter not implement in base visitor")

    def _set_end_index(self, end_index):
        self._end_index = end_index
