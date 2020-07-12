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
import tensorflow.compat.v1 as tf
from threading import Thread


class SummaryHook(object):
    SUMMARY_PATH = '/tmp/tfb_log'
    SUMMARY_SAVE_STEPS = 10
    TENSORBOARD_PORT = 6006
    TENSORBOARD_PATH = '/usr/local/bin/tensorboard'

    @staticmethod
    def get_hook(role):
        if not os.path.exists(SummaryHook.TENSORBOARD_PATH):
            logging.info('Tensorboard path {} is not existed'.format(SummaryHook.TENSORBOARD_PATH))
            return None
        os.makedirs(SummaryHook.SUMMARY_PATH, exist_ok=True)
        dir_name = '{}-{}'.format(datetime.datetime.now().strftime("%Y%m%d-%H%M%S"), role)
        output_dir = os.path.join(SummaryHook.SUMMARY_PATH, dir_name)
        logging.info('Summary output directory is {}'.format(output_dir))
        scaffold = tf.train.Scaffold(summary_op=tf.summary.merge_all())
        summary_hook = tf.train.SummarySaverHook(save_steps=SummaryHook.SUMMARY_SAVE_STEPS,
                                                 output_dir=output_dir,
                                                 scaffold=scaffold)
        Thread(target=SummaryHook.create_tensorboard, args=(SummaryHook.SUMMARY_PATH,)).start()
        return summary_hook

    @staticmethod
    def create_tensorboard(log_dir):
        subprocess.Popen([SummaryHook.TENSORBOARD_PATH,
                          '--logdir', log_dir,
                          '--port', '{}'.format(SummaryHook.TENSORBOARD_PORT)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
