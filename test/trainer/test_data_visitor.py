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

import unittest
from datetime import datetime, timedelta
from fedlearner.trainer.data_visitor import _DataVisitor, _RawDataBlock,\
    RawDataBlockDealer, ShuffleType

class TestLeaderDataVisitor(unittest.TestCase):
    def setUp(self):
        self._datablocks = [
            _RawDataBlock(
                "id_"+str(i), "path/to/"+str(i), 0, 0, ''
            )
            for i in range(10)
        ]

    def test_next(self):
        epoch_num = 5
        visitor = _DataVisitor(
            self._datablocks, epoch_num)
        try:
            i = 0
            c = 0
            while True:
                datablock = next(visitor)
                assert datablock.id == self._datablocks[i].id
                c += 1
                i = (i + 1) % len(self._datablocks)
        except StopIteration:
            assert c == len(self._datablocks) * epoch_num
            pass
        
    def test_shuffle_next(self):
        epoch_num = 5
        visitor = _DataVisitor(
            self._datablocks, epoch_num, shuffle_type=ShuffleType.ALL)
        try:
            i = 0
            c = 0
            idlist = [v.id for v in self._datablocks]
            same = True
            while True:
                datablock = next(visitor)
                same &= datablock.id == idlist[i]
                idlist.append(datablock.id)
                i = i + 1
                if i % len(self._datablocks) == 0:
                    assert not same
                    same = True
                c += 1
        except StopIteration:
            assert c == len(self._datablocks) * epoch_num
            pass

    def test_dump_restore(self):
        epoch_num = 5
        output = {}
        for i in range(epoch_num):
            output[i+1] = set()
        visitor = _DataVisitor(
            self._datablocks, epoch_num, shuffle_type=ShuffleType.ALL)
        for i in range(len(self._datablocks)*3 + 2):
            b = next(visitor)
            output[b.epoch].add(b.id)
        buff = visitor.dump()
        data = visitor._try_parse_v2(buff)
        print(data)

        visitor2 = _DataVisitor(
            self._datablocks, epoch_num)
        visitor2.restore(buff)
        try:
            while True:
                b = next(visitor2)
                output[b.epoch].add(b.id)
        except StopIteration:
            pass

        for i in range(epoch_num):
            for j, id in enumerate(sorted(output[i+1])):
                assert self._datablocks[j].id == id


class TestDataBlockDealer(unittest.TestCase):
    def setUp(self):
        start_time = datetime.strptime('20210101', '%Y%m%d')
        hour_delta = timedelta(hours=1)
        self._datablocks = []
        for i in range(100):
            end_time = start_time + hour_delta
            self._datablocks.append(_RawDataBlock(
                "id_" + str(i), "path/to/" + str(i),
                start_time.strftime('%Y%m%d%H%M%S'),
                end_time.strftime('%Y%m%d%H%M%S'),
                ''
            ))
            start_time += hour_delta

    def test_shuffle_in_day(self):
        dealer = RawDataBlockDealer(self._datablocks)
        dealer.shuffle_in_day()

    def test_shuffle(self):
        dealer = RawDataBlockDealer(self._datablocks)
        dealer.shuffle()


if __name__ == '__main__':
        unittest.main()
