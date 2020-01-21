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
from contextlib import contextmanager

import tensorflow.compat.v1 as tf

DataBlockSuffix = '.data'
DataBlockMetaSuffix = '.meta'
ExampleIdSuffix = '.done'

@contextmanager
def make_tf_record_iter(fpath):
    record_iter = None
    try:
        record_iter = tf.io.tf_record_iterator(fpath)
        yield record_iter
    except Exception as e: # pylint: disable=broad-except
        logging.warning(
                "Failed make tf_record_iterator for %s, reason %s",
                fpath, e
            )
    del record_iter
