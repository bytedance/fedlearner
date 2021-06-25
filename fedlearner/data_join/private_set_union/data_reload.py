import argparse
import logging
import math
import os

import fedlearner.common.private_set_union_pb2 as psu_pb
from fedlearner.common.common import set_logger
from fedlearner.data_join.private_set_union import spark_utils as spu
from fedlearner.data_join.private_set_union.keys import get_keys
from fedlearner.data_join.private_set_union.utils import E3, E4, Paths


class _Keys:
    id_dir = 'id_dir'
    data_dir = 'data_dir'
    diff_dir = 'diff_dir'
    output_path = 'output_path'
    partition_size = 'partition_size'
    partition_num = 'partition_num'
    encryption_keys = 'encryption_key'


class PSUDataReloadJob:
    def __init__(self,
                 config_file: str = "config.json",
                 jar_packages: str = None):
        self._spark = spu.start_spark(app_name='PSU_DataUnion',
                                      jar_packages=jar_packages,
                                      files=[config_file])
        self._config = spu.get_config(os.path.basename(config_file))
        self._id_dir = self._config[_Keys.id_dir]
        self._data_dir = self._config[_Keys.data_dir]
        self._diff_dir = self._config[_Keys.diff_dir]
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

        logging.info(f'Run Spark Data Reload with args: '
                     f'data_dir: {self._data_dir}, '
                     f'diff_dir: {self._diff_dir}, '
                     f'output_dir: {self._output_dir}, '
                     f'partition_size: {self._partition_size}, '
                     f'partition_num: {self._partition_num}')
        self._reload(self._id_dir, self._data_dir, self._diff_dir,
                     self._partition_size, self._partition_num)

    def _reload(self,
                id_dir: str,
                data_dir: str,
                diff_dir: str,
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
        id_df = self._spark.read \
            .option('recursiveFileLookup', 'true') \
            .option('pathGlobFilter', '*.parquet') \
            .parquet(id_dir)
        data_df = self._spark.read \
            .option('recursiveFileLookup', 'true') \
            .option('pathGlobFilter', '*.parquet') \
            .parquet(data_dir)
        assert id_df.count() == data_df.count()
        diff_df = self._spark.read \
            .option('recursiveFileLookup', 'true') \
            .option('pathGlobFilter', '*.parquet') \
            .parquet(diff_dir) \
            .select(self._encrypt_udf(E3).alias(E3))

        data_df = data_df \
            .join(id_df, ['_index', '_job_id'], 'left_outer') \
            .join(diff_df, [E4], 'full')

        if partition_size:
            # count() is fast in the event of parquet files
            count = data_df.count()
            partition_num = math.ceil(count / partition_size)

        # repartition, sort and save
        output_dir = Paths.encode_union_output_path()
        data_df \
            .repartition(partition_num, E4) \
            .sortWithinPartitions(E4) \
            .write \
            .mode('overwrite') \
            .parquet(output_dir)

    def stop(self):
        self._spark.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', '-c', type=str, default="config.json")
    parser.add_argument('--packages', type=str, default="")
    args = parser.parse_args()
    set_logger()

    packages = args.packages.split(",")
    processor = PSUDataReloadJob(args.config, packages)
    processor.run()
    processor.stop()
