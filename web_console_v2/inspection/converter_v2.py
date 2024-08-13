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

import enum
import logging
import json
import argparse
import fsspec
import os

from pyspark.conf import SparkConf
from pyspark.sql import SparkSession
from pyspark.sql import functions as spark_func
from pyspark.sql.types import StringType, ArrayType, StructType
from pyspark.sql.dataframe import DataFrame
from dataset_directory import DatasetDirectory

from util import FileFormat, normalize_file_path, dataset_schema_path, build_spark_conf, is_file_matched, \
    load_by_file_format, EXAMPLE_ID
from error_code import AreaCode, ErrorType, JobException, write_termination_message

DEFAULT_MANIFEST_PATH = 'manifest.json'
DEFAULT_IMAGES_PATH = 'images'
RAW_ID = 'raw_id'


class ImportType(enum.Enum):
    COPY = 'COPY'
    NO_COPY = 'NO_COPY'


@spark_func.udf(StringType())
def get_file_basename(origin_name: str) -> str:
    return os.path.basename(origin_name)


def flatten(schema, prefix=None):
    fields = []
    for field in schema.fields:
        name = prefix + '.' + field.name if prefix else field.name
        dtype = field.dataType
        if isinstance(dtype, ArrayType):
            dtype = dtype.elementType

        if isinstance(dtype, StructType):
            fields += flatten(dtype, prefix=name)
        else:
            fields.append(name)

    return fields


def convert_timestamp_cols_type_to_string(df: DataFrame) -> DataFrame:
    dtypes_dict = dict(df.dtypes)
    ts_col_list = [col_name for col_name in df.columns if dtypes_dict[col_name] == 'timestamp']
    logging.info(f'will convert the timestamp type columns to string type:{ts_col_list}')
    for col_name in ts_col_list:
        df = df.withColumn(col_name, spark_func.col(col_name).cast('string'))
    return df


def convert_image(spark: SparkSession, output_dataset_path: str, output_batch_path: str, input_batch_path: str,
                  manifest_name: str, images_dir_name: str):
    """convert source data to tfrecords format and save to output_batch_path.

    Args:
        spark: spark session
        output_dataset_path: path of output dataset.
        output_batch_path: path of output data_batch in this dataset.
        input_batch_path: input batch path of the image dataset directory.
        manifest_name: relative path of manifest file in zip archive.
        images_dir_name: relative path of images directory in zip archive

    Raises:
        JobException: read/write data by pyspark failed

    manifest json schema:
    {
        images:[
            {
                name: str
                file_name: str
                created_at: str
                annotation:{
                    label: str
                }
            },
            ...
        ]
    }

    saved tfrecord schema:
    +----------+-----+------+---------+-----+------+------+-----------+------+
    |file_name |width|height|nChannels|mode |data  |name  |created_at |label |
    +----------+-----+------+---------+-----+------+------+-----------+------+
    |string    |int  |int   |int      |int  |binary|string|string     |string|
    +----------+-----+------+---------+-----+------+------+-----------+------+
    """
    images_path = os.path.join(input_batch_path, images_dir_name)
    logging.info(f'### will load the images dir into dataframe:{images_path}')
    # spark.read.format('image') schema:
    # origin: StringType (represents the file path of the image)
    # height: IntegerType (height of the image)
    # width: IntegerType (width of the image)
    # nChannels: IntegerType (number of image channels)
    # mode: IntegerType (OpenCV-compatible type)
    # data: BinaryType (Image bytes in OpenCV-compatible order: row-wise BGR in most cases)
    # document ref: https://spark.apache.org/docs/latest/ml-datasource.html
    try:
        images_df = spark.read.format('image').load(images_path).select('image.origin', 'image.width', 'image.height',
                                                                        'image.nChannels', 'image.mode', 'image.data')
    except Exception as e:  # pylint: disable=broad-except
        raise JobException(AreaCode.CONVERTER, ErrorType.DATA_LOAD_ERROR,
                           f'failed to read input data, err: {str(e)}') from e
    images_df = images_df.withColumn('file_name', get_file_basename(spark_func.col('origin'))).drop('origin')
    manifest_path = os.path.join(input_batch_path, manifest_name)
    logging.info(f'### will load the manifest json file into dataframe:{manifest_path}')
    manifest_df = spark.read.json(manifest_path, multiLine=True)
    manifest_df.printSchema()
    manifest_df = manifest_df.select(spark_func.explode('images')).toDF('images').select(
        'images.name', 'images.file_name', 'images.created_at', 'images.annotation')
    manifest_df = manifest_df.select(flatten(manifest_df.schema))
    logging.info('### will join the images_df with the manifest_df on file_name column')
    df = images_df.join(manifest_df, 'file_name', 'inner')
    df = convert_timestamp_cols_type_to_string(df)
    logging.info(f'### saving to {output_batch_path}, in tfrecords')
    try:
        df.write.format('tfrecords').option('compression', 'none').save(output_batch_path, mode='overwrite')
    except Exception as e:  # pylint: disable=broad-except
        raise JobException(AreaCode.CONVERTER, ErrorType.DATA_WRITE_ERROR,
                           f'failed to write data, err: {str(e)}') from e
    with fsspec.open(dataset_schema_path(output_dataset_path), mode='w') as f:
        json.dump(df.schema.jsonValue(), f)


def convert_tabular(spark: SparkSession, output_dataset_path: str, output_batch_path: str, input_batch_path: str,
                    file_format: FileFormat):
    """convert source data to tfrecords format and save to output_batch_path.

    Args:
        spark: spark session
        output_dataset_path: path of output dataset.
        output_batch_path: path of output data_batch in this dataset.
        input_batch_path: input batch path of the tabular dataset.
        file_format: FileFormat['csv', 'tfrecords']

    Raises:
        JobException: read/write data by pyspark failed
    """
    if not is_file_matched(input_batch_path):
        # this is a hack to allow empty intersection dataset
        # no file matched, just mkdir output_batch_path and skip converter
        fsspec.get_mapper(output_batch_path).fs.mkdir(output_batch_path)
        logging.warning(f'input_dataset_path {input_batch_path} matches 0 files, skip converter task')
        return
    try:
        df = load_by_file_format(spark, input_batch_path, file_format)
    except Exception as e:  # pylint: disable=broad-except
        raise JobException(AreaCode.CONVERTER, ErrorType.DATA_LOAD_ERROR,
                           f'failed to read input data, err: {str(e)}') from e
    # force raw_id to string type as raw_id will be convert to bytes type in raw_data job
    # bigint type may cause memoryError
    if RAW_ID in df.columns:
        df = df.withColumn(RAW_ID, df[RAW_ID].cast(StringType()))
    # force example_id to string type as example_id will be read as stringType in training
    if EXAMPLE_ID in df.columns:
        df = df.withColumn(EXAMPLE_ID, df[EXAMPLE_ID].cast(StringType()))
    logging.info(f'### saving to {output_batch_path}, in tfrecords')
    try:
        df.write.format('tfrecords').option('compression', 'none').save(output_batch_path, mode='overwrite')
    except Exception as e:  # pylint: disable=broad-except
        raise JobException(AreaCode.CONVERTER, ErrorType.DATA_WRITE_ERROR,
                           f'failed to write data, err: {str(e)}') from e
    with fsspec.open(dataset_schema_path(output_dataset_path), mode='w') as f:
        json.dump(df.schema.jsonValue(), f)


def convert_no_copy(output_dataset_path: str, output_batch_path: str, input_batch_path: str):
    """save source data path to file source_batch_path in output_batch_path.

    Args:
        output_dataset_path: path of output dataset.
        output_batch_path: path of output data_batch in this dataset.
        input_batch_path: input batch path of the tabular dataset.

    """
    batch_name = os.path.basename(output_batch_path)
    with fsspec.open(DatasetDirectory(output_dataset_path).source_batch_path_file(batch_name), mode='w') as f:
        f.write(input_batch_path)


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='converter scripts arguments')
    subparsers = parser.add_subparsers(dest='command', help='sub-command help')
    # image parser
    image_parser = subparsers.add_parser('image', help='converter image format dataset')
    image_parser.add_argument('--output_dataset_path', required=True, type=str, help='path of the output dataset')
    image_parser.add_argument('--output_batch_path',
                              required=True,
                              type=str,
                              help='path of output data_batch in this dataset')
    image_parser.add_argument('--input_batch_path',
                              required=True,
                              type=str,
                              help='input batch path of the image dataset')
    image_parser.add_argument('--manifest_name',
                              type=str,
                              required=False,
                              default=DEFAULT_MANIFEST_PATH,
                              help='manifest file name in image dataset directory')
    image_parser.add_argument('--images_dir_name',
                              type=str,
                              required=False,
                              default=DEFAULT_IMAGES_PATH,
                              help='images directory name in image dataset directory')
    image_parser.add_argument('--import_type',
                              type=str,
                              choices=[import_type.value for import_type in ImportType],
                              required=False,
                              default=ImportType.COPY.value,
                              help='import type')
    # tabular parser
    tabular_parser = subparsers.add_parser('tabular', help='converter tabular format dataset')
    tabular_parser.add_argument('--output_dataset_path', type=str, required=True, help='path of output dataset')
    tabular_parser.add_argument('--output_batch_path',
                                type=str,
                                required=True,
                                help='path of output data_batch in this dataset')
    tabular_parser.add_argument('--input_batch_path',
                                type=str,
                                required=True,
                                help='input batch path of the tabular dataset')
    tabular_parser.add_argument('--format',
                                type=FileFormat,
                                choices=list(FileFormat),
                                required=True,
                                help='file format')
    tabular_parser.add_argument('--import_type',
                                type=str,
                                choices=[import_type.value for import_type in ImportType],
                                required=False,
                                default=ImportType.COPY.value,
                                help='import type')
    # none_structured parser
    none_structured_parser = subparsers.add_parser('none_structured', help='converter none_structured format dataset')
    none_structured_parser.add_argument('--output_dataset_path', type=str, required=True, help='path of output dataset')
    none_structured_parser.add_argument('--output_batch_path',
                                        type=str,
                                        required=True,
                                        help='path of output data_batch in this dataset')
    none_structured_parser.add_argument('--input_batch_path',
                                        type=str,
                                        required=True,
                                        help='input batch path of the none_structured dataset')
    none_structured_parser.add_argument('--import_type',
                                        type=str,
                                        choices=[import_type.value for import_type in ImportType],
                                        required=False,
                                        default=ImportType.COPY.value,
                                        help='import type')
    # all needed args for both image/tabular/none_structured will be given,
    # so we use known_args to ignore unnecessary args
    args, _ = parser.parse_known_args()

    return args


def converter_task():
    try:
        args = get_args()
    except SystemExit:
        write_termination_message(AreaCode.CONVERTER, ErrorType.INPUT_PARAMS_ERROR,
                                  'input params error, check details in logs')
        raise
    logging.info(f'[converter]:\n'
                 '----------------------\n'
                 'Input params:\n'
                 f'{args.__dict__}\n'
                 '----------------------\n')
    conf: SparkConf = build_spark_conf()
    spark = SparkSession.builder.config(conf=conf).getOrCreate()
    output_dataset_path = normalize_file_path(args.output_dataset_path)
    output_batch_path = normalize_file_path(args.output_batch_path)
    input_batch_path = normalize_file_path(args.input_batch_path)
    try:
        if args.import_type == ImportType.NO_COPY.value:
            convert_no_copy(output_dataset_path=output_dataset_path,
                            output_batch_path=output_batch_path,
                            input_batch_path=input_batch_path)
        else:
            if args.command == 'none_structured':
                raise JobException(AreaCode.CONVERTER, ErrorType.INPUT_PARAMS_ERROR,
                                   'none_structured dataset only supports no_copy import')
            if args.command == 'image':
                # image data
                logging.info('will convert image format dataset')
                convert_image(spark=spark,
                              output_dataset_path=output_dataset_path,
                              output_batch_path=output_batch_path,
                              input_batch_path=input_batch_path,
                              manifest_name=args.manifest_name,
                              images_dir_name=args.images_dir_name)
            else:
                # tabular data
                logging.info('will convert tabular format dataset')
                convert_tabular(spark=spark,
                                output_dataset_path=output_dataset_path,
                                output_batch_path=output_batch_path,
                                input_batch_path=input_batch_path,
                                file_format=args.format)
    except JobException as e:
        write_termination_message(e.area_code, e.error_type, e.message)
        raise
    finally:
        spark.stop()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    converter_task()
