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

# pylint: disable=redefined-outer-name
import json
import fsspec
import logging
import argparse
from cityhash import CityHash64  # pylint: disable=no-name-in-module

from pyspark.conf import SparkConf
from pyspark.sql import SparkSession
from pyspark.sql.types import StringType

from dataset_directory import DatasetDirectory
from util import build_spark_conf, FileFormat, EXAMPLE_ID, is_file_matched


# TODO(hangweiqiang): implement partition-wise join in parallel
def feature_extraction(spark: SparkSession, original_data_path: str, joined_data_path: str, part_num: int,
                       part_key: str, file_format: FileFormat, output_file_format: FileFormat, output_batch_name: str,
                       output_dataset_path: str):
    dataset_dir = DatasetDirectory(output_dataset_path)
    output_batch_path = dataset_dir.batch_path(output_batch_name)
    if not is_file_matched(joined_data_path):
        # this is a hack to allow empty intersection dataset
        # no file matched, just mkdir output_batch_path and skip converter
        fs: fsspec.AbstractFileSystem = fsspec.get_mapper(output_batch_path).fs
        fs.mkdir(output_batch_path)
        logging.warning(f'[feature_extraction]: joined_dataset_path {joined_data_path} matches 0 files, [SKIP]')
        return
    joined_df = spark.read.format(FileFormat.CSV.value).option('header', 'true').load(joined_data_path).toDF(part_key)
    original_df = spark.read.format(file_format.value).option('header', 'true').load(original_data_path)
    df = joined_df.join(original_df, on=part_key)
    # use customized partition method to guarantee consistency of sample between parties
    # TODO(liuhehan): unify partitioning method of output batch
    sorted_df = df.rdd.keyBy(lambda v: v[part_key]) \
        .partitionBy(part_num, CityHash64) \
        .map(lambda v: v[1]) \
        .toDF(schema=df.schema) \
        .sortWithinPartitions(part_key)
    sorted_df = sorted_df.withColumn(part_key, sorted_df[part_key].cast(StringType()))
    # a hack to generate example_id column if not exist as training need example id
    if EXAMPLE_ID not in sorted_df.columns:
        sorted_df = sorted_df.withColumn(EXAMPLE_ID, sorted_df[part_key])
    sorted_df.write.format(output_file_format.value).option('compression',
                                                            'none').option('header', 'true').save(output_batch_path,
                                                                                                  mode='overwrite')
    with fsspec.open(dataset_dir.schema_file, mode='w') as f:
        json.dump(sorted_df.schema.jsonValue(), f)
    spark.stop()


def get_args():
    parser = argparse.ArgumentParser(description='extract feature from dataset')
    parser.add_argument('--original_data_path', type=str, help='original data path')
    parser.add_argument('--joined_data_path', type=str, help='path of joined id')
    parser.add_argument('--part_key', type=str, help='partition key')
    parser.add_argument('--part_num', type=int, help='patition number')
    parser.add_argument('--file_format', type=FileFormat, choices=list(FileFormat), help='format of original file')
    parser.add_argument('--output_file_format', type=FileFormat, choices=list(FileFormat), help='format of output file')
    parser.add_argument('--output_batch_name', type=str, help='name of output batch')
    parser.add_argument('--output_dataset_path', type=str, help='path of output dataset')
    return parser.parse_args()


if __name__ == '__main__':
    args = get_args()
    for arg, value in vars(args).items():
        logging.info(f'Arg: {arg}, value: {value}')
    conf: SparkConf = build_spark_conf()
    spark = SparkSession.builder.config(conf=conf).getOrCreate()
    feature_extraction(spark=spark,
                       original_data_path=args.original_data_path,
                       joined_data_path=args.joined_data_path,
                       part_key=args.part_key,
                       part_num=args.part_num,
                       file_format=args.file_format,
                       output_file_format=args.output_file_format,
                       output_batch_name=args.output_batch_name,
                       output_dataset_path=args.output_dataset_path)
