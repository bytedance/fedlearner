import argparse
import logging
import json
import os

from cityhash import CityHash32  # pylint: disable=no-name-in-module
from pyspark import SparkFiles
from pyspark.sql import SparkSession, Row
from pyspark.sql.types import *

import tensorflow.compat.v1 as tf

from fedlearner.data_join_v2.raw_data.common import Constants, DataKeyword, \
    JobType, OutputType, RawDataSchema


def set_logger():
    logging.getLogger().setLevel(logging.INFO)
    logging.basicConfig(format="%(asctime)s %(filename)s:%(lineno)s "
                               "%(levelname)s - %(message)s")


def start_spark(app_name='my_spark_app',
                jar_packages=None,
                files=None, spark_config=None):

    # get Spark session factory
    spark_builder = \
        SparkSession.builder.appName(app_name)

    # create Spark JAR packages string
    if jar_packages:
        spark_jars_packages = ','.join(list(jar_packages))
        spark_builder.config('spark.jars', spark_jars_packages)

    if files:
        spark_files = ','.join(list(files))
        spark_builder.config('spark.files', spark_files)

    if spark_config:
        # add other config params
        for key, val in spark_config.items():
            spark_builder.config(key, val)

    # create session and retrieve Spark logger object
    return spark_builder.getOrCreate()


def get_config(config_filename):
    # get config file if sent to cluster with --files
    spark_files_dir = SparkFiles.getRootDirectory()
    path_to_config_file = os.path.join(spark_files_dir, config_filename)
    if os.path.exists(path_to_config_file):
        with open(path_to_config_file, 'r') as config_file:
            config_dict = json.load(config_file)
    else:
        config_dict = None
    return config_dict


class RawData:
    def __init__(self, config_file=None, jar_packages=None):
        # start Spark application and get Spark session, logger and config
        config_files = [config_file] if config_file else None
        self._config = None

        self._spark = start_spark(
            app_name='RawData',
            jar_packages=jar_packages,
            files=config_files)
        if config_file:
            self._config = get_config(os.path.basename(config_file))

    def run(self, config=None):
        set_logger()
        if not config:
            config = self._config
        output_type = config[Constants.output_type_key]

        if output_type == OutputType.DataBlock:
            self._to_data_block(config)
        else:
            self._to_raw_data(config)

    def _to_raw_data(self, config):
        job_id = config[Constants.job_id_key]
        job_type = config[Constants.job_type_key]
        input_files = config[Constants.input_files_key]
        output_path = config[Constants.output_path_key]
        partition_num = config[Constants.output_partition_num_key]

        partition_field = self._get_partition_field(job_type)

        data_rdd = self._spark.sparkContext.newAPIHadoopFile(
            input_files,
            "org.tensorflow.hadoop.io.TFRecordFileInputFormat",
            keyClass="org.apache.hadoop.io.BytesWritable",
            valueClass="org.apache.hadoop.io.NullWritable")

        data_rdd = data_rdd.zipWithIndex()

        example_rdd = data_rdd.mapPartitions(
            lambda x: RawData._map_func(
                x, job_id,
                RawDataSchema.wanted_fields(),
                DataKeyword.partition_key,
                DataKeyword.event_time,
                partition_field,
                partition_num))

        output_df = example_rdd.toDF(self._raw_data_schema())

        write_options = {
            'compression': 'gzip'
        }
        output_df.write \
            .mode("append") \
            .partitionBy(DataKeyword.partition_key) \
            .options(**write_options) \
            .parquet(output_path)

        logging.info("Export data to %s finished", output_path)

    @staticmethod
    def _map_func(iterator, job_id, wanted_fields,
                  partition_key, event_time_field,
                  partition_field, num_partitions):
        def _get_value(v):
            if v.int64_list.value:
                result = v.int64_list.value
            elif v.float_list.value:
                result = v.float_list.value
            else:
                return v.bytes_list.value[0].decode('utf-8')

            if len(result) > 1:  # represent multi-item tensors as python lists
                return list(result)
            elif len(result) == 1:  # extract scalars from single-item tensors
                return result[0]
            else:  # represent empty tensors as python None
                return None

        for record in iterator:
            example = tf.train.Example()
            example.ParseFromString(bytes(record[0][0]))
            data = [job_id, record[1], record[0][0]]
            for field_name, default_value in wanted_fields.items():
                if field_name in example.features.feature:
                    data.append(_get_value(
                        example.features.feature[field_name]))
                else:
                    data.append(default_value)
            if event_time_field in example.features.feature:
                event_time = _get_value(
                    example.features.feature[event_time_field])
                data.append(str(event_time)[:10])
            elif partition_field not in example.features.feature:
                logging.fatal("Partition field %s not exist", partition_key)
            else:
                partition_value = _get_value(
                    example.features.feature[partition_field])
                data.append(
                    str(CityHash32(partition_value) % num_partitions))
            yield data

    @staticmethod
    def _raw_data_schema():
        output_fields = []
        for field in RawDataSchema.schema():
            if field[1].type == int:
                field_type = LongType()
            elif field[1].type == str:
                field_type = StringType()
            else:  # bytes
                field_type = BinaryType()
            output_fields.append(StructField(
                field[0], field_type, field[1].required
            ))
        return StructType(output_fields)

    def _to_data_block(self, config):
        input_files = config[Constants.input_files_key]
        output_path = config[Constants.output_path_key]
        data_block_threshold = config[Constants.data_block_threshold_key]
        compression_type = config[Constants.compression_type_key]
        if compression_type and compression_type.upper() == "GZIP":
            write_options = {
                "mapred.output.compress": "true",
                "mapred.output.compression.codec":
                    "org.apache.hadoop.io.compress.GzipCodec",
            }
        else:
            write_options = {
                "mapred.output.compress": "false",
            }

        logging.info("Deal with new files %s with write option %s",
                     input_files, write_options)

        data_rdd = self._spark.sparkContext.newAPIHadoopFile(
            input_files,
            "org.tensorflow.hadoop.io.TFRecordFileInputFormat",
            keyClass="org.apache.hadoop.io.BytesWritable",
            valueClass="org.apache.hadoop.io.NullWritable")
        if data_block_threshold > 0:
            num_partition = int((data_rdd.count() + data_block_threshold - 1) /
                                data_block_threshold)

            data_rdd = data_rdd.zipWithIndex()

            data_rdd = data_rdd \
                .keyBy(lambda value: value[1]) \
                .partitionBy(num_partition, partitionFunc=lambda k: k) \
                .map(lambda x: x[1][0])

        data_rdd.saveAsNewAPIHadoopFile(
            output_path,
            "org.tensorflow.hadoop.io.TFRecordFileOutputFormat",
            keyClass="org.apache.hadoop.io.BytesWritable",
            valueClass="org.apache.hadoop.io.NullWritable",
            conf=write_options)

        logging.info("Export data to %s finished", output_path)

    @staticmethod
    def _get_partition_field(job_type):
        if job_type == JobType.PSI:
            return DataKeyword.raw_id
        return DataKeyword.example_id

    def stop(self):
        self._spark.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', '-c', type=str, default="config.json")
    parser.add_argument('--packages', type=str, default="")
    args = parser.parse_args()
    set_logger()
    logging.info(args)

    packages = args.packages.split(",")
    processor = RawData(args.config, packages)
    processor.run()
    processor.stop()
