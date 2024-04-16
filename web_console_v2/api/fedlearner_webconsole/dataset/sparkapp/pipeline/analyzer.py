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
import sys
import json
import logging

import fsspec
import pandas

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, sum
from util import dataset_features_path, dataset_meta_path, dataset_hist_path


def analyze(dataset_path: str, wildcard: str):
    # for example:
    # dataset_path: /data/fl_v2_fish_fooding/dataset/20210527_221741_pipeline/
    # wildcard: rds/**
    spark = SparkSession.builder.getOrCreate()
    files = os.path.join(dataset_path, wildcard)
    logging.info(f'### loading df..., input files path: {files}')
    df = spark.read.format('tfrecords').load(files)
    # df_stats
    df_missing = df.select(*(sum(col(c).isNull().cast('int')).alias(c)
                             for c in df.columns)).withColumn(
                                 'summary', lit('missing_count'))
    df_stats = df.describe().unionByName(df_missing)
    df_stats = df_stats.toPandas().set_index('summary').transpose()
    features_path = dataset_features_path(dataset_path)
    logging.info(f'### writing features, features path is {features_path}')
    content = json.dumps(df_stats.to_dict(orient='index'))
    with fsspec.open(features_path, mode='w') as f:
        f.write(content)
    # meta
    meta = {}
    # dtypes
    logging.info('### loading dtypes...')
    dtypes = {}
    for d in df.dtypes:
        k, v = d  # (feature, type)
        dtypes[k] = v
    meta['dtypes'] = dtypes
    # sample count
    logging.info('### loading count...')
    meta['count'] = df.count()
    # sample
    logging.info('### loading sample...')
    meta['sample'] = df.head(20)
    # meta
    meta_path = dataset_meta_path(dataset_path)
    logging.info(f'### writing meta, path is {meta_path}')
    with fsspec.open(meta_path, mode='w') as f:
        f.write(json.dumps(meta))
    # feature histogram
    logging.info('### loading hist...')
    hist = {}
    for c in df.columns:
        # TODO: histogram is too slow and needs optimization
        x, y = df.select(c).rdd.flatMap(lambda x: x).histogram(10)
        hist[c] = {'x': x, 'y': y}
    hist_path = dataset_hist_path(dataset_path)
    logging.info(f'### writing hist, path is {hist_path}')
    with fsspec.open(hist_path, mode='w') as f:
        f.write(json.dumps(hist))

    spark.stop()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) != 3:
        logging.error(
            f'spark-submit {sys.argv[0]} [dataset_path] [file_wildcard]')
        sys.exit(-1)

    dataset_path, wildcard = sys.argv[1], sys.argv[2]
    analyze(dataset_path, wildcard)
