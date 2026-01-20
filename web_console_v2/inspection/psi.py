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

# pylint: skip-file
import os
import logging
from enum import Enum

import rsa
import fsspec
from cityhash import CityHash64
from gmpy2 import powmod
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import StringType
from pyspark.sql.functions import udf

from util import getenv, FileFormat


class PSI(object):

    def __init__(self,
                 input_dir: str,
                 wildcard: str,
                 file_format: FileFormat,
                 output_dir: str,
                 part_num: int,
                 part_key: str,
                 rsa_key_path: str,
                 rsa_key_bits: int = 2048):
        """
        Args:
            input_dir: origin raw data
            wildcard: use wildcard rules to match multiple files
            file_format: specific read file format
            output_dir: signed data save path
            part_num: partition need to set
            part_key: partition used key column
            rsa_key_path: the private key path, may not exist, if not exist, create one
            rsa_key_bits: if need to generate a key, use the argument to specific key bits
        """
        self._input_dir = input_dir
        self._wildcard = wildcard
        self._file_format = file_format
        self._output_dir = output_dir
        self._part_num = part_num
        self._part_key = part_key
        self._rsa_key_path = rsa_key_path
        self._rsa_key_bits = rsa_key_bits

        self._rsa = None

    def run(self, spark: SparkSession):
        self._load_rsa_key()
        self._partition_and_sign(spark)

    def _partition_and_sign(self, spark: SparkSession):
        files = os.path.join(self._input_dir, self._wildcard)
        logging.info(f'### loading df..., input files path: {files}')
        df = spark.read.format(self._file_format).load(files, header=True, inferSchema=True)
        if self._part_key not in df.columns:
            raise ValueError(f'### error: part_id {self._part_key} not in df columns')
        df = df.dropDuplicates([self._part_key])
        df = df.withColumn(self._part_key, df[self._part_key].cast(StringType()))
        df.printSchema()

        logging.info(f'### partition and sorting')
        part_idx = df.columns.index(self._part_key)

        sorted_df = df.rdd.keyBy(lambda v: v[part_idx]) \
            .partitionBy(self._part_num, self.partition_fn) \
            .map(lambda v: v[1]) \
            .toDF(schema=df.schema).sortWithinPartitions(self._part_key)
        raw_path = os.path.join(self._output_dir, 'raw')
        logging.info(f'### writing to raw path: {raw_path}')
        self.write_df(sorted_df, raw_path)
        d, n = self._rsa.d, self._rsa.n

        @udf()
        def sign(v: str):
            s = powmod(self.partition_fn(v), d, n).digits()
            # hash and hex to save space
            return hex(self.partition_fn(s))[2:]

        logging.info(f'### signing')
        part_df = sorted_df.select(self._part_key)
        sign_df = part_df.withColumn('signed', sign(part_df[self._part_key]))
        sign_path = os.path.join(self._output_dir, 'signed')
        logging.info(f'### writing to sign path: {sign_path}')
        self.write_df(sign_df, sign_path)

    def _load_rsa_key(self):
        fs = fsspec.filesystem('hdfs')
        if not fs.exists(self._rsa_key_path):
            logging.info('[Signer] key does not exist, generate one')
            _, private_key = rsa.newkeys(self._rsa_key_bits)
            with fs.open(self._rsa_key_path, 'wb') as f:
                f.write(private_key.save_pkcs1(format='PEM'))

        with fs.open(self._rsa_key_path) as f:
            logging.info('[Signer] Reading private key.')
            self._rsa = rsa.PrivateKey.load_pkcs1(f.read())

    @staticmethod
    def partition_fn(v: str) -> int:
        return CityHash64(v)

    @staticmethod
    def write_df(data: 'DataFrame', path: str, fmt: str = 'csv'):
        data.write.format(fmt).option('compression', 'none').option('header', 'true').save(path, mode='overwrite')


def main():
    input_dir = getenv('INPUT_DIR')
    wildcard = getenv('WILDCARD', '*')
    file_format = FileFormat(os.getenv('FILE_FORMAT', 'tfrecords').lower())
    output_dir = getenv('OUTPUT_DIR')
    part_num = int(getenv('PART_NUM', '8'))
    part_key = getenv('PART_KEY', 'raw_id')
    rsa_key_path = getenv('RSA_KEY_PATH')
    rsa_key_bits = int(getenv('RSA_KEY_BITS'))

    logging.info(f'preparing psi, input_dir: {input_dir}, wildcard: {wildcard} output_dir: {output_dir}, '
                 f'part_num: {part_num}, part_key: {part_key}, rsa_key_path: {rsa_key_path}, '
                 f'rsa_key_bits: {rsa_key_bits}')

    spark = SparkSession.builder.getOrCreate()
    PSI(input_dir=input_dir,
        wildcard=wildcard,
        file_format=file_format,
        output_dir=output_dir,
        part_num=part_num,
        part_key=part_key,
        rsa_key_path=rsa_key_path,
        rsa_key_bits=rsa_key_bits).run(spark)
    spark.stop()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
