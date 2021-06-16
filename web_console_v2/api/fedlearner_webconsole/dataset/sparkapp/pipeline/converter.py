# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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

import sys
import os
import logging

from pyspark.sql import SparkSession
from util import dataset_rds_path


def convert(dataset_path: str, wildcard: str):
    # for example:
    # dataset_path: /data/fl_v2_fish_fooding/dataset/20210527_221741_pipeline/
    # wildcard: batch/**/*.csv
    files = os.path.join(dataset_path, wildcard)
    logging.info(f'### input files path: {files}')
    spark = SparkSession.builder.getOrCreate()
    if wildcard.endswith('*.csv'):
        df = spark.read.format('csv').option('header', 'true').option(
            'inferSchema', 'true').load(files)
    elif wildcard.endswith('*.rd') or wildcard.endswith('*.tfrecords'):
        df = spark.read.format('tfrecords').load(files)
    else:
        logging.error(f'### no valid file wildcard, wildcard: {wildcard}')
        return

    df.printSchema()
    save_path = dataset_rds_path(dataset_path)
    logging.info(f'### saving to {save_path}, in tfrecords')
    df.write.format('tfrecords').save(save_path, mode='overwrite')
    spark.stop()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) != 3:
        logging.error(
            f'spark-submit {sys.argv[0]} [dataset_path] [file_wildcard]')
        sys.exit(-1)

    dataset_path, wildcard = sys.argv[1], sys.argv[2]
    convert(dataset_path, wildcard)
