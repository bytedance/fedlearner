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
import datetime
import logging
import tensorflow.compat.v1 as tf


class SummaryHook(object):
    @classmethod
    def get_hook(cls, role):
        summary_path = os.environ.get('SUMMARY_PATH', None)
        summary_save_steps = os.environ.get('SUMMARY_SAVE_STEPS', 10)
        if not summary_path:
            logging.info('Tensorboard is not started')
            return None
        os.makedirs(summary_path, exist_ok=True)
        datetime_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        dir_name = '{}-{}'.format(datetime_str, role)
        output_dir = os.path.join(summary_path, dir_name)
        logging.info('Summary output directory is %s', output_dir)
        scaffold = tf.train.Scaffold(summary_op=tf.summary.merge_all())
        hook = tf.train.SummarySaverHook(save_steps=summary_save_steps,
                                         output_dir=output_dir,
                                         scaffold=scaffold)
        return hook
