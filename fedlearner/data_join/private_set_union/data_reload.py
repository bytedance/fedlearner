import argparse
import logging
import math

from pyspark.sql.functions import monotonically_increasing_id

from fedlearner.common.common import set_logger
from fedlearner.data_join.private_set_union.spark_utils import start_spark, Keys
from fedlearner.data_join.private_set_union.utils import E4


class SparkDataReload:
    def __init__(self,
                 config: dict,
                 jar_packages: str = None):
        self._spark = start_spark(app_name='PSU_DataReload',
                                  jar_packages=jar_packages)
        self._config = config

    def run(self, config: dict = None):
        config = config or self._config
        assert config
        id_dir = config[Keys.e4_dir]
        data_dir = config[Keys.data_dir]
        diff_dir = config[Keys.diff_dir]
        output_dir = config[Keys.output_path]
        partition_size = config.get(Keys.partition_size, None)
        partition_num = config.get(Keys.partition_num, 32)

        logging.info(f'Run Spark Data Reload with args: '
                     f'data_dir: {data_dir}, '
                     f'diff_dir: {diff_dir}, '
                     f'output_dir: {output_dir}, '
                     f'partition_size: {partition_size}, '
                     f'partition_num: {partition_num}')
        self._reload(id_dir, data_dir, diff_dir, output_dir,
                     partition_size, partition_num)

    def _reload(self,
                id_dir: str,
                data_dir: str,
                diff_dir: str,
                output_dir: str,
                partition_size: int = None,
                partition_num: int = 32) -> None:
        """
        Calculate the union and symmetric differences of two data sets. Left is
            where we calculate symmetric difference, Right is the opposite side.
        Args:
            data_dir: directory to right ids parquet files.
            diff_dir: directory to left ids parquet files.
            partition_size: size of one partition.
            partition_num: num of partition. If partition_size is provided, this
                will be ignored.
        """
        # id_df is the E4 id of each row, containing `_job_id` & `_index`
        id_df = self._spark.read \
            .option('recursiveFileLookup', 'true') \
            .option('pathGlobFilter', '*.parquet') \
            .parquet(id_dir)
        # data_df is the original data
        data_df = self._spark.read \
            .option('recursiveFileLookup', 'true') \
            .option('pathGlobFilter', '*.parquet') \
            .parquet(data_dir)
        assert id_df.count() == data_df.count()
        # diff_df is the set difference
        diff_df = self._spark.read \
            .option('recursiveFileLookup', 'true') \
            .option('pathGlobFilter', '*.parquet') \
            .parquet(diff_dir) \
            .select(E4)

        # ======== Sample Rows to Fake Data ========
        data_len = data_df.count()
        diff_len = diff_df.count()
        # sample 5% more data s.t. there are enough rows
        sample_rate = diff_len / data_len * 1.05
        # loop until there are enough rows
        while True:
            if sample_rate > 1.:
                sample_df = data_df.sample(True, sample_rate).limit(diff_len)
            else:
                sample_df = data_df.sample(False, sample_rate).limit(diff_len)
            if sample_df.count() == diff_len:
                break
            sample_rate *= 1.05
        sample_df = sample_df \
            .withColumn('_row_', monotonically_increasing_id())
        diff_df = diff_df \
            .withColumn('_row_', monotonically_increasing_id())
        sample_df = sample_df \
            .join(diff_df, ['_row_']) \
            .drop('_row_')

        # ======== Reload ========
        data_df = data_df \
            .join(id_df, ['_index', '_job_id'], 'left_outer') \
            .union(sample_df) \
            .drop('_index', '_job_id')

        if partition_size:
            # count() is fast in the event of parquet files
            count = data_df.count()
            partition_num = math.ceil(count / partition_size)

        # repartition, sort and save
        data_df \
            .repartition(partition_num, E4) \
            .sortWithinPartitions(E4) \
            .write \
            .option("compression", "gzip") \
            .mode('overwrite') \
            .parquet(output_dir)

    def stop(self):
        self._spark.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(f'--{Keys.e4_dir}', '-e', type=str)
    parser.add_argument(f'--{Keys.data_dir}', '-dt', type=str)
    parser.add_argument(f'--{Keys.diff_dir}', '-df', type=str)
    parser.add_argument(f'--{Keys.output_path}', '-o', type=str)
    parser.add_argument(f'--{Keys.partition_size}', '-ps', type=int)
    parser.add_argument(f'--{Keys.partition_num}', '-pn', type=int)
    parser.add_argument('--packages', type=str, default='')
    args = parser.parse_args()
    set_logger()

    packages = args.packages.split(",")
    cfg = {k: getattr(args, k, None) for k in (Keys.e4_dir,
                                               Keys.data_dir,
                                               Keys.diff_dir,
                                               Keys.output_path,
                                               Keys.partition_size,
                                               Keys.partition_num,
                                               Keys.encryption_key_type,
                                               Keys.encryption_key_path)}
    processor = SparkDataReload(cfg, packages)
    processor.run()
    processor.stop()
