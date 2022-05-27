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
try:
    import tensorflow.compat.v1 as tf
except ImportError:
    import tensorflow.compat.v1 as tf
from . import fl_logging


class SummaryHook(object):
    summary_path = None
    save_steps = 1000
    worker_rank = 0
    role = 'leader'

    @classmethod
    def get_hook(cls):
        if not cls.summary_path:
            fl_logging.info('Tensorboard is not started')
            return None
        tf.io.gfile.makedirs(cls.summary_path)
        datetime_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        dir_name = '{}-{}-{}'.format(datetime_str, cls.role, cls.worker_rank)
        output_dir = os.path.join(cls.summary_path, dir_name)
        fl_logging.info('Summary output directory is %s', output_dir)
        scaffold = tf.train.Scaffold(summary_op=tf.summary.merge_all())
        hook = tf.train.SummarySaverHook(save_steps=int(cls.save_steps),
                                         output_dir=output_dir,
                                         scaffold=scaffold)
        return hook
