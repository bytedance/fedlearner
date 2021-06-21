# TODO(zhangzihui): Merge this file with spark raw data
import json
import os

from pyspark import SparkFiles
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf


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


def make_udf(keys):
    # use the second key to encrypt the set differences
    assert keys

    @udf
    def _udf(item: [str, bytes]):
        item = keys.encode(keys.encrypt_2(keys.decode(item)))
        return item

    return _udf
