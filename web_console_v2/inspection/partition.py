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
import argparse

from cityhash import CityHash64  # pylint: disable=no-name-in-module
from pyspark.conf import SparkConf
from pyspark.sql import SparkSession
from pyspark.sql.types import StringType
import fsspec

from util import FileFormat, build_spark_conf, is_file_matched


# pylint: disable=redefined-outer-name
def partition(spark: SparkSession, input_path: str, file_format: FileFormat, output_file_format: FileFormat,
              output_dir: str, part_num: int, part_key: str, write_raw_data: bool):
    logging.info(f'[Partition] loading df..., input files path: {input_path}')
    raw_path = os.path.join(output_dir, 'raw')
    id_path = os.path.join(output_dir, 'ids')
    if not is_file_matched(input_path):
        # this is a hack to allow empty intersection dataset
        # no file matched, just mkdir output_batch_path and skip converter
        fs: fsspec.AbstractFileSystem = fsspec.get_mapper(output_dir).fs
        if write_raw_data:
            fs.mkdir(raw_path)
        fs.mkdir(id_path)
        logging.warning(f'[partition]: input_dataset_path {input_path} matches 0 files, [SKIP]')
        return
    df = spark.read.format(file_format.value).load(input_path, header=True, inferSchema=True)
    if part_key not in df.columns:
        raise ValueError(f'[Partition] error: part_id {part_key} not in df columns')
    df = df.dropDuplicates([part_key])
    df = df.withColumn(part_key, df[part_key].cast(StringType()))
    df.printSchema()

    logging.info('[Partition] start partitioning')
    # spark operation steps explanations
    # keyBy : use specified column as the index key used in partition,
    # partitionBy(partition_num, func) :  pass index key to func, and use the func result mod partition_num,
    # map: remove the index key,
    # toDF: change to dataframe by origin df schema
    # partitionBy code ref:
    # https://github.com/apache/spark/blob/master/python/pyspark/rdd.py#L2114
    # https://github.com/apache/spark/blob/7d88f1c5c7f38c0f1a2bd5e3116c668d9cbd98b1/python/pyspark/rdd.py#L251
    # define a customized partition method to ensure partition consistency between two party
    # missing value when writing df as tfrecord if without sortWithinPartitions and the reason is unknown
    df = df.rdd.keyBy(lambda v: v[part_key]) \
        .partitionBy(part_num, CityHash64) \
        .map(lambda v: v[1]) \
        .toDF(schema=df.schema) \
        .sortWithinPartitions(part_key)
    if write_raw_data:
        logging.info(f'[Partition] writing to raw path: {raw_path}')
        df.write.format(output_file_format.value).option('compression', 'none').option('header',
                                                                                       'true').save(raw_path,
                                                                                                    mode='overwrite')
    id_df = df.select(part_key)
    id_df.write.format('csv').option('compression', 'none').option('header', 'true').save(id_path, mode='overwrite')


def get_args():
    parser = argparse.ArgumentParser(description='Partition the dataset')
    parser.add_argument('--input_path', type=str, help='input data path with wildcard')
    parser.add_argument('--file_format', type=FileFormat, choices=list(FileFormat), help='format of input data')
    parser.add_argument('--part_num', type=int, help='patition number')
    parser.add_argument('--part_key', type=str, help='patition key')
    parser.add_argument('--output_file_format', type=FileFormat, choices=list(FileFormat), help='format of output file')
    parser.add_argument('--output_dir', type=str, help='name of output batch')
    parser.add_argument('--write_raw_data', type=bool, default=True, help='whether to write partitioned raw data')
    return parser.parse_args()


if __name__ == '__main__':
    args = get_args()
    for arg, value in vars(args).items():
        logging.info(f'Arg: {arg}, value: {value}')
    conf: SparkConf = build_spark_conf()
    spark = SparkSession.builder.config(conf=conf).getOrCreate()
    partition(spark,
              input_path=args.input_path,
              file_format=args.file_format,
              output_file_format=args.output_file_format,
              output_dir=args.output_dir,
              part_num=args.part_num,
              part_key=args.part_key,
              write_raw_data=args.write_raw_data)
    spark.stop()
