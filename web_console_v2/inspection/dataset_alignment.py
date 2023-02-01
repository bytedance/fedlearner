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
from typing import List, Dict
import json
import fsspec

from pyspark.rdd import RDD
from pyspark.sql import SparkSession
from pyspark.conf import SparkConf
from pyspark.sql.types import Row, StringType, StructType, StructField
from util import build_spark_conf, load_tfrecords, dataset_schema_path
from json_schema_checker import SchemaChecker

from error_code import AreaCode, ErrorType, JobException, write_termination_message

_DATASET_ALIGNMENT_LOG = 'dataset_alignment'


class DatasetAlignment(object):
    """
    ProcessedDataset struct
    |
    |--- batch ---- batch_name_1 --- real data files
    |            |
    |            |- batch_name_2 --- real data files
    |            |
    |            |- batch_name_3 --- real data files
    |
    |--- errors --- batch_name_1 --- error message files (.csv)
    |            |
    |            |- batch_name_2 --- error message files (.csv)
    |            |
    |            |- batch_name_3 --- error message files (.csv)
    |
    |--- _META
    """

    def __init__(self, spark: SparkSession, input_dataset_path: str, input_batch_path: str, wildcard: str,
                 output_batch_path: str, json_schema: str, output_dataset_path: str, output_error_path: str):
        self._spark = spark
        self._input_dataset_path = input_dataset_path
        self._input_batch_path = input_batch_path
        self._wildcard = wildcard
        self._output_batch_path = output_batch_path
        self._json_schema = json.loads(json_schema)
        self._output_dataset_path = output_dataset_path
        self._output_error_path = output_error_path

    def _dump_error_msgs(self, rdd_errors: RDD):
        deptSchema = StructType([
            StructField('field', StringType(), True),
            StructField('message', StringType(), True),
        ])
        df_error_msgs = self._spark.createDataFrame(rdd_errors, schema=deptSchema)
        logging.info(f'[{_DATASET_ALIGNMENT_LOG}]: start to dump error message')
        df_error_msgs.coalesce(1).write.format('json').save(self._output_error_path, mode='overwrite')
        logging.info(f'[{_DATASET_ALIGNMENT_LOG}]: dump error message finished')

    def run(self):
        try:
            checker = SchemaChecker(self._json_schema)
        except RuntimeError as e:
            raise JobException(AreaCode.ALIGNMENT, ErrorType.INPUT_PARAMS_ERROR, 'json_schema is illegal') from e

        files = os.path.join(self._input_batch_path, self._wildcard)
        try:
            df = load_tfrecords(spark=self._spark, files=files, dataset_path=self._input_dataset_path)
        except Exception as e:  # pylint: disable=broad-except
            raise JobException(AreaCode.ALIGNMENT, ErrorType.DATA_LOAD_ERROR,
                               f'failed to read input data, err: {str(e)}') from e
        # broadcast has better performence by keeping read-only variable cached on each machine,
        # rather than shipping a copy of it with tasks
        # Ref: https://spark.apache.org/docs/latest/api/python/reference/api/pyspark.Broadcast.html
        broadcast_vals = self._spark.sparkContext.broadcast({'checker': checker})

        def check_schema(row: Row) -> List[Dict[str, str]]:
            data = row.asDict()
            checker = broadcast_vals.value['checker']
            error_message = checker.check(data)
            return error_message

        # use flatMap to flat result from list[dict] to dict like {'filed': 'xxx', 'message': 'xxx'}
        rdd_errors = df.rdd.flatMap(check_schema)
        if rdd_errors.count() > 0:
            self._dump_error_msgs(rdd_errors)
            message = f'[{_DATASET_ALIGNMENT_LOG}]: schema check failed!'
            logging.error(message)
            raise JobException(AreaCode.ALIGNMENT, ErrorType.SCHEMA_CHECK_ERROR, message)
        logging.info(f'[{_DATASET_ALIGNMENT_LOG}]: schema check succeeded!')
        df.write.format('tfrecords').option('compression', 'none').save(self._output_batch_path, mode='overwrite')
        with fsspec.open(dataset_schema_path(self._output_dataset_path), mode='w') as f:
            json.dump(df.schema.jsonValue(), f)
        logging.info(f'[{_DATASET_ALIGNMENT_LOG}]: dataset alignment task is finished!')


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='dataset alignment task')

    parser.add_argument('--input_dataset_path', type=str, required=True, help='path of input dataset')
    parser.add_argument('--input_batch_path', type=str, required=True, help='path of input databatch')
    parser.add_argument('--json_schema', type=str, required=True, help='json schema in string type')
    parser.add_argument('--wildcard', type=str, required=True, help='wildcard')
    parser.add_argument('--output_dataset_path', type=str, required=True, help='path of output dataset')
    parser.add_argument('--output_batch_path', type=str, required=True, help='path of output databatch')
    parser.add_argument('--output_error_path', type=str, required=True, help='path of output error')

    return parser.parse_args()


def alignment_task():
    try:
        args = get_args()
    except SystemExit:
        write_termination_message(AreaCode.ALIGNMENT, ErrorType.INPUT_PARAMS_ERROR,
                                  'input params error, check details in logs')
        raise
    logging.info(f'[{_DATASET_ALIGNMENT_LOG}]:\n'
                 '----------------------\n'
                 'Input params:\n'
                 f'{args.__dict__}\n'
                 '----------------------\n')
    conf: SparkConf = build_spark_conf()
    spark = SparkSession.builder.config(conf=conf).getOrCreate()
    try:
        DatasetAlignment(spark, args.input_dataset_path, args.input_batch_path, args.wildcard, args.output_batch_path,
                         args.json_schema, args.output_dataset_path, args.output_error_path).run()
    except JobException as e:
        write_termination_message(e.area_code, e.error_type, e.message)
        raise
    finally:
        spark.stop()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    alignment_task()
