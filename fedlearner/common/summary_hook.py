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
import subprocess
from threading import Thread
import tensorflow.compat.v1 as tf


class SummaryHook(object):
    SUMMARY_PATH = '/tmp/tfb_log'
    SUMMARY_SAVE_STEPS = 10
    TENSORBOARD_PORT = 6006
    TENSORBOARD_PATH = '/usr/local/bin/tensorboard'

    @classmethod
    def get_hook(cls, role):
        if not os.path.exists(cls.TENSORBOARD_PATH):
            logging.info('Tensorboard %s is not existed', cls.TENSORBOARD_PATH)
            return None
        os.makedirs(cls.SUMMARY_PATH, exist_ok=True)
        datetime_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        dir_name = '{}-{}'.format(datetime_str, role)
        output_dir = os.path.join(cls.SUMMARY_PATH, dir_name)
        logging.info('Summary output directory is %s', output_dir)
        scaffold = tf.train.Scaffold(summary_op=tf.summary.merge_all())
        hook = tf.train.SummarySaverHook(save_steps=cls.SUMMARY_SAVE_STEPS,
                                                 output_dir=output_dir,
                                                 scaffold=scaffold)
        Thread(target=cls.create_tensorboard, args=(cls.SUMMARY_PATH,)).start()
        return hook

    @classmethod
    def create_tensorboard(cls, log_dir):
        subprocess.Popen([cls.TENSORBOARD_PATH, '--logdir', log_dir,
                          '--port', '{}'.format(cls.TENSORBOARD_PORT)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
