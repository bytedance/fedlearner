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

import logging
import argparse

from pyspark.sql import SparkSession
from pyspark.conf import SparkConf

from analyzer.analyzer_task import AnalyzerTask
from util import normalize_file_path, build_spark_conf
from error_code import AreaCode, ErrorType, JobException, write_termination_message


def get_args(args=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='analyzer scripts arguments')
    subparsers = parser.add_subparsers(dest='command', help='sub-command help')
    # image parser
    image_parser = subparsers.add_parser('image', help='analyzer image format dataset')
    image_parser.add_argument('--data_path', type=str, required=True, help='path of dataset')
    image_parser.add_argument('--file_wildcard', type=str, required=True, help='file wildcard')
    image_parser.add_argument('--buckets_num', '-n', type=int, required=False, help='the number of buckets for hist')
    image_parser.add_argument('--thumbnail_path', type=str, required=True, help='dir path to save the thumbnails')
    image_parser.add_argument('--batch_name', type=str, required=False, default='', help='batch_name of target batch')
    image_parser.add_argument('--skip', action='store_true', help='skip analyzer task')
    # tabular parser
    tabular_parser = subparsers.add_parser('tabular', help='analyzer tabular format dataset')
    tabular_parser.add_argument('--data_path', type=str, required=True, help='path of dataset')
    tabular_parser.add_argument('--file_wildcard', type=str, required=True, help='file wildcard')
    tabular_parser.add_argument('--buckets_num', '-n', type=int, required=False, help='the number of buckets for hist')
    tabular_parser.add_argument('--batch_name', type=str, required=False, default='', help='batch_name of target batch')
    tabular_parser.add_argument('--skip', action='store_true', help='skip analyzer task')
    # none_structured parser
    none_structured_parser = subparsers.add_parser('none_structured', help='analyzer none_structured format dataset')
    none_structured_parser.add_argument('--skip', action='store_true', help='skip analyzer task')
    # all needed args for both image/tabular will be given, so we use known_args to ignore unnecessary args
    args, _ = parser.parse_known_args(args)

    return args


def analyzer():
    try:
        args = get_args()
    except SystemExit:
        write_termination_message(AreaCode.ANALYZER, ErrorType.INPUT_PARAMS_ERROR,
                                  'input params error, check details in logs')
        raise
    logging.info(f'[analyzer]:\n'
                 '----------------------\n'
                 'Input params:\n'
                 f'{args.__dict__}\n'
                 '----------------------\n')
    if args.skip:
        logging.info('[analyzer]: skip analyzer job [SKIP]')
        return
    conf: SparkConf = build_spark_conf()
    spark = SparkSession.builder.config(conf=conf).getOrCreate()
    thumbnail_path_parameter = None
    if args.command == 'image':
        thumbnail_path_parameter = args.thumbnail_path
    try:
        if not args.batch_name:
            raise JobException(area_code=AreaCode.ANALYZER,
                               error_type=ErrorType.INPUT_PARAMS_ERROR,
                               message='failed to find batch_name')
        AnalyzerTask().run(spark=spark,
                           dataset_path=normalize_file_path(args.data_path),
                           wildcard=args.file_wildcard,
                           is_image=(args.command == 'image'),
                           batch_name=args.batch_name,
                           buckets_num=int(args.buckets_num) if args.buckets_num else None,
                           thumbnail_path=normalize_file_path(thumbnail_path_parameter))
    except JobException as e:
        write_termination_message(e.area_code, e.error_type, e.message)
        raise
    finally:
        spark.stop()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    analyzer()
