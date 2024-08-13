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
from tensorflow.io import gfile
# pylint: disable=unused-import
import tensorflow_io

from fedlearner_webconsole.db import db


def _remove(path: str):
    if not gfile.exists(path):
        return
    if gfile.isdir(path):
        gfile.rmtree(path)
        return
    gfile.remove(path)


def _copy_file(src: str, dst: str):
    _remove(dst)
    if not gfile.isdir(src):
        gfile.copy(src, dst)
        return
    gfile.makedirs(dst)
    sub_srcs = gfile.glob(os.path.join(src, '*'))
    for sub_src in sub_srcs:
        _copy_file(sub_src, os.path.join(dst, os.path.basename(sub_src)))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    engine = db.engine
    datasets = engine.execute(
        'SELECT id, name, path FROM datasets_v2 WHERE meta_info = \'{"state": "ANALYZED"}\'').fetchall()
    logging.info(f'[migration] get all available datasets, total num is {len(datasets)}')
    for dataset in datasets:
        data_batchs = engine.execute(f'SELECT path FROM data_batches_v2 WHERE dataset_id = {dataset[0]}').fetchall()
        if len(data_batchs) != 1:
            logging.warning(f'[migration] dataset {dataset[1]} has more than one data_batch, skip!')
            continue
        data_batch_path, = data_batchs[0]

        rds_path = os.path.join(dataset[2], 'rds')
        if not gfile.isdir(rds_path):
            logging.warning(f'[migration] dataset {dataset[1]} has no rds folder, skip!')
            continue
        logging.info(f'[migration] start to migrate dataset {dataset[1]}, dataset path: {dataset[2]}')
        _copy_file(rds_path, data_batch_path)
        _remove(rds_path)
        logging.info(f'[migration] migrate dataset {dataset[1]}, dataset path: {dataset[2]} successfully')
