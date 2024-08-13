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
import fsspec

from pyspark.sql import SparkSession
from pyspark.conf import SparkConf
from dataset_directory import DatasetDirectory
from error_code import AreaCode, ErrorType, JobException, write_termination_message
from util import FileFormat, build_spark_conf, load_by_file_format


def export_dataset_for_structured_type(input_path: str, export_path: str, file_format: FileFormat):
    try:
        conf: SparkConf = build_spark_conf()
        spark = SparkSession.builder.config(conf=conf).getOrCreate()
        try:
            df = load_by_file_format(spark=spark, input_batch_path=input_path, file_format=file_format)
        except Exception as e:  # pylint: disable=broad-except
            raise JobException(AreaCode.EXPORT_DATASET, ErrorType.DATA_LOAD_ERROR,
                               f'failed to read input data, err: {str(e)}') from e
        try:
            df.write.format('csv').option('compression', 'none').option('header', 'true').save(path=export_path,
                                                                                               mode='overwrite')
        except Exception as e:  # pylint: disable=broad-except
            raise JobException(AreaCode.EXPORT_DATASET, ErrorType.DATA_WRITE_ERROR,
                               f'failed to write data, err: {str(e)}') from e
    finally:
        spark.stop()


def export_dataset_for_unknown_type(input_path: str, export_path: str):
    fs: fsspec.spec.AbstractFileSystem = fsspec.get_mapper(export_path).fs
    if fs.exists(export_path):
        fs.rm(export_path, recursive=True)
    fs.copy(input_path, export_path, recursive=True)


def get_args(args=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='export dataset')
    parser.add_argument('--data_path', type=str, help='path of intput')
    parser.add_argument('--export_path', type=str, help='path of output')
    parser.add_argument('--batch_name', type=str, required=False, help='batch need to export')
    parser.add_argument('--file_format',
                        type=FileFormat,
                        choices=list(FileFormat),
                        default=FileFormat.TFRECORDS,
                        required=False,
                        help='file format')
    # TODO(liuhehan): delete file_wildcard input after export job support batch
    parser.add_argument('--file_wildcard', type=str, required=False, help='input file wildcard')

    return parser.parse_args(args)


def export_dataset():
    try:
        args = get_args()
    except SystemExit:
        write_termination_message(AreaCode.EXPORT_DATASET, ErrorType.INPUT_PARAMS_ERROR,
                                  'input params error, check details in logs')
        raise
    logging.info(f'[export_dataset]:\n'
                 '----------------------\n'
                 'Input params:\n'
                 f'{args.__dict__}\n'
                 '----------------------\n')

    if args.batch_name:
        input_path = DatasetDirectory(dataset_path=args.data_path).batch_path(batch_name=args.batch_name)
    else:
        # TODO(liuhehan): delete after export job support batch
        input_path = os.path.join(args.data_path, args.file_wildcard)
    try:
        if args.file_format == FileFormat.UNKNOWN:
            export_dataset_for_unknown_type(input_path=input_path, export_path=args.export_path)
        else:
            export_dataset_for_structured_type(input_path=input_path,
                                               export_path=args.export_path,
                                               file_format=args.file_format)
    except JobException as e:
        write_termination_message(e.area_code, e.error_type, e.message)
        raise


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    export_dataset()
