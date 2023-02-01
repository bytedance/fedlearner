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

import sys
import logging
import argparse
from typing import List

from pyspark.conf import SparkConf
from pyspark.sql import SparkSession
from pyspark.sql.dataframe import DataFrame
from error_code import AreaCode, ErrorType, JobException, write_termination_message

from util import FileFormat, normalize_file_path, build_spark_conf, load_by_file_format, is_file_matched

RAW_ID_COLUMN = 'raw_id'
DEFAULT_IGNORED_NUMERIC_COLUMNS = frozenset(['raw_id', 'example_id', 'event_time'])
NUMERIC_TYPES = frozenset(['bigint', 'int', 'smallint', 'tinyint', 'double', 'float'])

RAW_ID_CHECKER = 'RAW_ID_CHECKER'
NUMERIC_COLUMNS_CHECKER = 'NUMERIC_COLUMNS_CHECKER'


def check_raw_id(df: DataFrame):
    if RAW_ID_COLUMN not in df.columns:
        raise JobException(AreaCode.FORMAT_CHECKER, ErrorType.NO_KEY_COLUMN_ERROR,
                           f'[check_raw_id] failed to find {RAW_ID_COLUMN} in dataset')

    df_count = df.count()
    distinct_count = df.dropDuplicates([RAW_ID_COLUMN]).count()
    if df_count != distinct_count:
        raise JobException(AreaCode.FORMAT_CHECKER, ErrorType.DATA_FORMAT_ERROR,
                           f'[check_raw_id] find {df_count - distinct_count} duplicated items in raw_id')


def check_numeric_columns(df: DataFrame):
    illegal_columns = []
    for column_name, column_type in df.dtypes:
        if column_name in DEFAULT_IGNORED_NUMERIC_COLUMNS:
            continue
        if column_type not in NUMERIC_TYPES:
            illegal_column_msg = f'[column]: {column_name}, [type]: {column_type}'
            illegal_columns.append(illegal_column_msg)
    if len(illegal_columns) > 0:
        raise JobException(AreaCode.FORMAT_CHECKER, ErrorType.DATA_FORMAT_ERROR,
                           f'[check_numeric_columns] find {len(illegal_columns)} illegal columns: {illegal_columns}')


def check_format(df: DataFrame, checkers: List[str]):
    if RAW_ID_CHECKER in checkers:
        check_raw_id(df)
    if NUMERIC_COLUMNS_CHECKER in checkers:
        check_numeric_columns(df)


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='dataset checker task')
    subparsers = parser.add_subparsers(dest='command', help='sub-command help')

    # image parser
    image_parser = subparsers.add_parser('image', help='check image format dataset')

    # tabular parser
    tabular_parser = subparsers.add_parser('tabular', help='check tabular format dataset')

    tabular_parser.add_argument('--input_batch_path',
                                type=str,
                                required=True,
                                help='input batch path of the tabular dataset')
    tabular_parser.add_argument('--format',
                                type=FileFormat,
                                choices=list(FileFormat),
                                required=True,
                                help='file format')
    tabular_parser.add_argument('--checkers', type=str, required=True, help='checkers')

    # image parser
    none_structured_parser = subparsers.add_parser('none_structured', help='check none_structured format dataset')

    # all needed args for both image/tabular will be given, so we use known_args to ignore unnecessary args
    known_args, _ = parser.parse_known_args()
    return known_args


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        args = get_args()
    except SystemExit:
        write_termination_message(AreaCode.FORMAT_CHECKER, ErrorType.INPUT_PARAMS_ERROR,
                                  'input params error, check details in logs')
        raise
    logging.info(f'[format checker]:\n'
                 '----------------------\n'
                 'Input params:\n'
                 f'{args.__dict__}\n'
                 '----------------------\n')
    conf: SparkConf = build_spark_conf()
    spark = SparkSession.builder.config(conf=conf).getOrCreate()
    try:
        if args.command == 'image':
            # image data
            logging.info('[format checker]: image type has no checker now, [SKIP]')
        elif args.command == 'none_structured':
            # none_structured data
            logging.info('[format checker]: none_structured type has no checker now, [SKIP]')
        else:
            input_batch_path = normalize_file_path(args.input_batch_path)
            # tabular data
            if not is_file_matched(input_batch_path):
                logging.warning(f'input_dataset_path {input_batch_path} matches 0 files')
                sys.exit()
            try:
                dataframe = load_by_file_format(spark, input_batch_path, args.format)
            except Exception as e:  # pylint: disable=broad-except
                raise JobException(AreaCode.FORMAT_CHECKER, ErrorType.DATA_LOAD_ERROR,
                                   f'failed to read input data, err: {str(e)}') from e
            check_format(dataframe, args.checkers.split(','))
    except JobException as e:
        write_termination_message(e.area_code, e.error_type, e.message)
        raise
    finally:
        spark.stop()
