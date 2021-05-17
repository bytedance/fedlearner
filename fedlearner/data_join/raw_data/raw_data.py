import argparse
import logging
import json
import os

from pyspark import SparkFiles
from pyspark.sql import SparkSession
from pyspark.sql.types import *
from tensorflow.compat.v1 import gfile

from cityhash import CityHash32

from fedlearner.data_join.raw_data.common import *


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
        spark_builder.config('spark.jars.packages', spark_jars_packages)

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
        job_type = config[Constants.job_type_key]
        input_files = config[Constants.input_files_key].split(",")
        output_path = config[Constants.output_path_key]
        partition_num = config[Constants.output_partition_num_key]
        schema_file_path = config[Constants.schema_path_key]
        compression_type = config[Constants.compression_type_key]

        logging.info("Deal with new files %s", input_files)

        # get data schema
        data_schema = self._get_data_schema(schema_file_path, input_files[0])

        # read input data
        data_df = self._spark.read \
            .format("tfrecords") \
            .schema(data_schema) \
            .option("recordType", "Example") \
            .load(",".join(input_files))

        # deal with data
        output_df = self._partition_and_sort(data_df, job_type, partition_num)

        # output data
        write_options = {
            "recordType": "Example",
            "maxRecordsPerFile": 1 << 20,
        }
        if compression_type and compression_type.upper() == "GZIP":
            write_options["codec"] = 'org.apache.hadoop.io.compress.GzipCodec'
        output_df.write \
            .mode("overwrite") \
            .format("tfrecords") \
            .options(**write_options) \
            .save(output_path)

        logging.info("Export data to %s finished", output_path)

    def _to_data_block(self, config):
        input_files = config[Constants.input_files_key]
        output_path = config[Constants.output_path_key]
        data_block_threshold = config[Constants.data_block_threshold_key]
        compression_type = config[Constants.compression_type_key]
        write_options = None
        if compression_type and compression_type.upper() == "GZIP":
            write_options = {
                "mapred.output.compress": "true",
                "mapred.output.compression.codec":
                    "org.apache.hadoop.io.compress.GzipCodec",
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

    def _get_data_schema(self, schema_file_path, sample_file):
        try:
            with gfile.Open(schema_file_path, 'r') as f:
                saved_schema = json.load(f)
            schema = StructType.fromJson(saved_schema)
            return schema
        except Exception:
            logging.info("Schema file %s not exists, infer from %s",
                         schema_file_path, sample_file)
            # infer schema from one file
            data_df = self._spark.read \
                .format("tfrecords") \
                .option("recordType", "Example") \
                .load(sample_file)
            gfile.MakeDirs(os.path.dirname(schema_file_path))
            with gfile.Open(schema_file_path, 'w') as f:
                json.dump(data_df.schema.jsonValue(), f)
            return data_df.schema

    def _partition_and_sort(self, data_df, job_type, partition_num):
        partition_field = self._get_partition_field(job_type)
        partition_index = data_df.columns.index(partition_field)

        def partitioner_fn(x):
            return CityHash32(x)

        schema = data_df.schema

        data_df = data_df.rdd \
            .keyBy(lambda value: value[partition_index]) \
            .partitionBy(int(partition_num), partitionFunc=partitioner_fn) \
            .map(lambda x: x[1]) \
            .toDF(schema=schema)

        if job_type == JobType.Streaming:
            return data_df.sortWithinPartitions(DataKeyword.event_time,
                                                DataKeyword.example_id)
        return data_df.sortWithinPartitions(DataKeyword.example_id)  # PSI

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
