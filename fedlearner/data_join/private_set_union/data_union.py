import argparse
import logging
import math

from pyspark.sql.functions import col, udf

import fedlearner.common.private_set_union_pb2 as psu_pb
from fedlearner.common.common import set_logger
from fedlearner.data_join.private_set_union.keys import get_keys
from fedlearner.data_join.private_set_union.spark_utils import start_spark, Keys
from fedlearner.data_join.private_set_union.utils import E2, E3


class SparkDataUnion:
    def __init__(self,
                 config: dict,
                 jar_packages: str = None):
        self._spark = start_spark(app_name='PSU_DataUnion',
                                  jar_packages=jar_packages)
        self._config = config

    @staticmethod
    def _make_udf(keys):
        # use the second key to encrypt the set differences
        assert keys

        @udf
        def _udf(item: [str, bytes]):
            item = keys.encode(keys.encrypt_2(keys.decode(item)))
            return item

        return _udf

    def run(self, config: dict = None):
        config = config or self._config
        assert config
        right_dir = config[Keys.right_dir]
        left_dir = config[Keys.left_dir]
        l_out = config[Keys.l_diff_output_dir]
        r_out = config[Keys.r_diff_output_dir]
        partition_size = config.get(Keys.partition_size, None)
        partition_num = config.get(Keys.partition_num, 32)

        key_type = config[Keys.encryption_key_type]
        key_path = config[Keys.encryption_key_path]
        key_info = psu_pb.KeyInfo(type=getattr(psu_pb, key_type),
                                  path=key_path)
        keys = get_keys(key_info)
        encrypt_udf = self._make_udf(keys)

        logging.info(f'Run Spark Data Union with args: '
                     f'right_dir: {right_dir}, '
                     f'left_dir: {left_dir}, '
                     f'left_output_dir: {l_out}, '
                     f'right_output_dir: {r_out}, '
                     f'key_type: {key_type}, '
                     f'key_path: {key_path}, '
                     f'partition_size: {partition_size}, '
                     f'partition_num: {partition_num}')
        self._union(right_dir, left_dir, encrypt_udf, l_out, r_out,
                    partition_size, partition_num)

    def _union(self,
               right_dir: str,
               left_dir: str,
               encrypt_udf,
               l_output_dir: str,
               r_output_dir: str,
               partition_size: int = None,
               partition_num: int = 32) -> None:
        """
        Calculate the union and symmetric differences of two data sets. Left is
            where we calculate symmetric difference, Right is the opposite side.
        Args:
            right_dir: directory to right ids parquet files.
            left_dir: directory to left ids parquet files.
            partition_size: size of one partition.
            partition_num: num of partition. If partition_size is provided, this
                will be ignored.
        """
        right_df = self._spark.read \
            .option('recursiveFileLookup', 'true') \
            .option('pathGlobFilter', '*.parquet') \
            .parquet(right_dir) \
            .select(E2) \
            .alias('r')  # aliasing to avoid column name collision
        left_df = self._spark.read \
            .option('recursiveFileLookup', 'true') \
            .option('pathGlobFilter', '*.parquet') \
            .parquet(left_dir) \
            .select(E2) \
            .alias('l')

        r_col = f'r.{E2}'  # <alias>.<col>
        l_col = f'l.{E2}'

        # set union
        diff = right_df \
            .join(left_df, col(r_col) == col(l_col), how='full')

        # filter out differences relative to each set
        #   and then use peer's encrypted ids, respectively
        # LEFT - RIGHT with encryption, these are ids that right doesn't have
        right_diff = diff \
            .filter(col(r_col).isNull()) \
            .select(encrypt_udf(l_col).alias(E3))
        # PEER - LOCAL WITHOUT encryption, these are ids that left doesn't have
        left_diff = diff \
            .filter(col(l_col).isNull()) \
            .select(col(r_col).alias(E2))

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
            .repartition(r_partition_num, E3) \
            .write \
            .option('compression', 'gzip') \
            .mode('overwrite') \
            .parquet(r_output_dir)
        left_diff \
            .repartition(l_partition_num, E2) \
            .write \
            .option('compression', 'gzip') \
            .mode('overwrite') \
            .parquet(l_output_dir)

    def stop(self):
        self._spark.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(f'--{Keys.left_dir}', '-l', type=str)
    parser.add_argument(f'--{Keys.right_dir}', '-r', type=str)
    parser.add_argument(f'--{Keys.l_diff_output_dir}', '-lo', type=str)
    parser.add_argument(f'--{Keys.r_diff_output_dir}', '-ro', type=str)
    parser.add_argument(f'--{Keys.partition_size}', '-ps', type=int)
    parser.add_argument(f'--{Keys.partition_num}', '-pn', type=int)
    parser.add_argument(f'--{Keys.encryption_key_type}', '-kt', type=str)
    parser.add_argument(f'--{Keys.encryption_key_path}', '-kp', type=str)
    parser.add_argument('--packages', type=str, default='')
    args = parser.parse_args()
    set_logger()

    packages = args.packages.split(",")
    cfg = {k: getattr(args, k, None) for k in (Keys.left_dir,
                                               Keys.right_dir,
                                               Keys.l_diff_output_dir,
                                               Keys.r_diff_output_dir,
                                               Keys.partition_size,
                                               Keys.partition_num,
                                               Keys.encryption_key_type,
                                               Keys.encryption_key_path)}
    processor = SparkDataUnion(cfg, packages)
    processor.run()
    processor.stop()
