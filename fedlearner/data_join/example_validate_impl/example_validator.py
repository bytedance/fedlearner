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

from fedlearner.data_join.common import InvalidEventTime, InvalidExampleId
from fedlearner.data_join.raw_data_iter_impl.tf_record_iter import TfExampleItem

class ExampleValidator(object):
    def __init__(self, check_event_time=True):
        self._check_event_time = check_event_time

    @classmethod
    def name(cls):
        return 'EXAMPLE_VALIDATOR'

    def validate_example(self, tf_example_item):
        assert isinstance(tf_example_item, TfExampleItem), \
            "tf_example_item should be a instance of TfExampleItem"

        if tf_example_item.example is None:
            return False, "Failed to parse tf.Example from {}"\
                    .format(tf_example_item.record)
        if tf_example_item.example_id == InvalidExampleId:
            return False, "Failed to parse example id parse from {}"\
                    .format(tf_example_item.record)
        if self._check_event_time and \
                tf_example_item.event_time == InvalidEventTime:
            return False, "Failed to parse event_time of example_id {} "\
                    "parse from {}".format(tf_example_item.example_id,
                                           tf_example_item.record)
        return True, ''
