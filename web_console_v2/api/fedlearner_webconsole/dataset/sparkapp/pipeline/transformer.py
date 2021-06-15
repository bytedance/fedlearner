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
import os
import json
import sys
import logging

from pyspark.sql import SparkSession
from util import dataset_transformer_path


def transform(dataset_path: str, wildcard: str, conf: str):
    # for example:
    # dataset_path: /data/fl_v2_fish_fooding/dataset/20210527_221741_pipeline/
    # wildcard: rds/** or data_block/**/*.data
    # conf: {"f00001": 0.0, "f00002": 1.0}
    spark = SparkSession.builder.getOrCreate()
    files = os.path.join(dataset_path, wildcard)
    conf_dict = json.loads(conf)
    logging.info(f'### input files path: {files}, config: {conf_dict}')
    df = spark.read.format('tfrecords').load(files)
    filled_df = df.fillna(conf_dict)
    save_path = dataset_transformer_path(dataset_path)
    logging.info(f'### saving to {save_path}')
    filled_df.write.format('tfrecords').save(save_path, mode='overwrite')
    spark.stop()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) != 4:
        logging.error(
            f'spark-submit {sys.argv[0]} [dataset_path] [wildcard] [config]')
        sys.exit(-1)

    dataset_path, wildcard, conf = sys.argv[1], sys.argv[2], sys.argv[3]
    transform(dataset_path, wildcard, conf)
