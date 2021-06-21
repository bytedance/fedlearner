import argparse
import logging
import math
import os

from pyspark.sql.functions import col

import fedlearner.common.private_set_union_pb2 as psu_pb
from fedlearner.common.common import set_logger
from fedlearner.data_join.private_set_union import spark_utils as spu
from fedlearner.data_join.private_set_union.keys import get_keys
from fedlearner.data_join.private_set_union.utils import Paths, E2, E3


class _Keys:
    right_dir = 'right_dir'
    left_dir = 'left_dir'
    output_path = 'output_path'
    partition_size = 'partition_size'
    partition_num = 'partition_num'
    union_key = E2
    encryption_keys = 'encryption_key'


class ParquetDataUnionJob:
    def __init__(self,
                 config_file: str = "config.json",
                 jar_packages: str = None):
        self._spark = spu.start_spark(app_name='PSU_DataUnion',
                                      jar_packages=jar_packages,
                                      files=[config_file])
        self._config = spu.get_config(os.path.basename(config_file))
        self._right_dir = self._config[_Keys.right_dir]
        self._left_dir = self._config[_Keys.left_dir]
        self._output_dir = self._config[_Keys.output_path]
        self._partition_size = self._config.get(_Keys.partition_size, None)
        self._partition_num = self._config.get(_Keys.partition_num, 32)
        keys = self._config[_Keys.encryption_keys]
        key_info = psu_pb.KeyInfo()
        key_info.ParseFromString(keys)
        self._keys = get_keys(key_info)
        self._encrypt_udf = spu.make_udf(self._keys)

    def run(self, config: dict = None):
        config = config or self._config
        assert config

        logging.info(f'Run Spark Data Union with args: '
                     f'right_dir: {self._right_dir}, '
                     f'left_dir: {self._left_dir}, '
                     f'output_dir: {self._output_dir}, '
                     f'partition_size: {self._partition_size}, '
                     f'partition_num: {self._partition_num}')
        self._union(self._right_dir, self._left_dir, self._output_dir,
                    self._partition_size, self._partition_num)

    def _union(self,
               right_dir: str,
               left_dir: str,
               output_dir: str,
               partition_size: int = None,
               partition_num: int = 32) -> None:
        """
        Calculate the union and symmetric differences of two data sets. Left is
            where we calculate symmetric difference, Right is the opposite side.
        Args:
            right_dir: directory to right ids parquet files.
            left_dir: directory to left ids parquet files.
            output_dir: output directory to dump set differences.
            partition_size: size of one partition.
            partition_num: num of partition. If partition_size is provided, this
                will be ignored.
        """
        right_df = self._spark.read \
            .option('recursiveFileLookup', 'true') \
            .option('pathGlobFilter', '*.parquet') \
            .parquet(right_dir) \
            .select(_Keys.union_key) \
            .alias('r')  # aliasing to avoid column name collision
        left_df = self._spark.read \
            .option('recursiveFileLookup', 'true') \
            .option('pathGlobFilter', '*.parquet') \
            .parquet(left_dir) \
            .select(_Keys.union_key) \
            .alias('l')

        r_col = f'r.{_Keys.union_key}'  # <alias>.<col>
        l_col = f'l.{_Keys.union_key}'

        # set union
        diff = right_df \
            .join(left_df, col(r_col) == col(l_col), how='full')

        # filter out differences relative to each set,
        #   and then use the opposite side's encrypted ids, respectively
        # LEFT - RIGHT with encryption, these are ids that right doesn't have
        right_diff = diff \
            .filter(col(r_col) is None) \
            .select(self._encrypt_udf(l_col).alias(E3))
        # PEER - LOCAL WITHOUT encryption, these are ids that left doesn't have
        left_diff = diff \
            .filter(col(l_col) is None) \
            .select(col(r_col).alias(E2))

        r_output_dir, l_output_dir = Paths.encode_union_output_paths(output_dir)
        # if specify partition size, calculate the num of partitions
        if partition_size:
            # count() is fast in the event of parquet files
            r_count = right_diff.count()
            l_count = left_diff.count()
            r_partition_num = math.ceil(r_count / partition_size)
            l_partition_num = math.ceil(l_count / partition_size)
        else:
            r_partition_num = l_partition_num = partition_num

        # repartition and save
        right_diff \
            .repartition(r_partition_num, _Keys.union_key) \
            .write \
            .mode('overwrite') \
            .parquet(r_output_dir)
        left_diff \
            .repartition(l_partition_num, _Keys.union_key) \
            .write \
            .mode('overwrite') \
            .parquet(l_output_dir)

    def stop(self):
        self._spark.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', '-c', type=str, default="config.json")
    parser.add_argument('--packages', type=str, default="")
    args = parser.parse_args()
    set_logger()

    packages = args.packages.split(",")
    processor = ParquetDataUnionJob(args.config, packages)
    processor.run()
    processor.stop()
