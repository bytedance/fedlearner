# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import logging
import tensorflow as tf
from model import run, get_dataset
from fedlearner.fedavg import train_from_keras_model

fl_name = 'follower'

mode = os.getenv('MODE', 'train')
epoch_num = int(os.getenv('EPOCH_NUM', 1))
data_path = os.getenv('DATA_PATH')
output_base_dir = os.getenv('OUTPUT_BASE_DIR')
steps_per_sync = int(os.getenv('FL_STEPS_PER_SYNC', 10))
LOAD_MODEL_FROM = os.getenv('LOAD_MODEL_FROM')

if __name__ == '__main__':
    print('-------------------------------')
    print('mode : ', mode)
    print('data_path : ', data_path)
    print('output_base_dir : ', output_base_dir)
    print('load model from : ', LOAD_MODEL_FROM)
    print('-------------------------------')
    logging.basicConfig(level=logging.INFO)
    logging.info('mode: %s', mode)
    ds = get_dataset(data_path)
    run(fl_name, mode, ds, epoch_num, steps_per_sync)
