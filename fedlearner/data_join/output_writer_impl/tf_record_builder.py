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

import tensorflow.compat.v1 as tf

from fedlearner.data_join.output_writer_impl.output_writer import OutputWriter

class TfRecordBuilder(OutputWriter):
    def __init__(self, options, fpath):
        super(TfRecordBuilder, self).__init__(options, fpath)
        writer_options = tf.io.TFRecordOptions(
                compression_type=options.compressed_type
            )
        self._writer = tf.io.TFRecordWriter(fpath, writer_options)

    def write_item(self, item):
        self._writer.write(item.tf_record)

    def close(self):
        self._writer.close()

    @classmethod
    def name(cls):
        return 'TF_RECORD'
