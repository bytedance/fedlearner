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

import logging
import argparse

from gmssl.sm4 import CryptSM4, SM4_ENCRYPT
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType
from pyspark.conf import SparkConf
from util import build_spark_conf

# initial verctor for cbc encrypt
INITIAL_VECTOR = '00000000000000000000000000000000'


def sm4_encrypt(input_path: str, output_path: str, key_str: str):
    key = bytes.fromhex(key_str)
    iv = bytes.fromhex(INITIAL_VECTOR)
    crypt_sm4 = CryptSM4()
    crypt_sm4.set_key(key, SM4_ENCRYPT)

    conf: SparkConf = build_spark_conf()
    spark = SparkSession.builder.config(conf=conf).getOrCreate()
    broadcast_vals = spark.sparkContext.broadcast({'crypt_sm4': crypt_sm4, 'iv': iv})

    @udf(StringType())
    def sm4(value_string: str) -> str:
        crypt_sm4 = broadcast_vals.value['crypt_sm4']
        iv = broadcast_vals.value['iv']
        encrypt_value = crypt_sm4.crypt_cbc(iv, value_string.encode('utf-8'))
        return encrypt_value.hex()

    df = spark.read.format('csv').load(input_path)
    df = df.withColumnRenamed('_c0', 'raw_id')
    df = df.withColumn('raw_id', sm4(df['raw_id']))
    df.write.format('csv').option('compression', 'none').option('header', 'true').save(path=output_path,
                                                                                       mode='overwrite')


def get_args():
    parser = argparse.ArgumentParser(description='esm4 ncrypt')
    parser.add_argument('--input', type=str, help='path of intput sha256')
    parser.add_argument('--output', type=str, help='path of output sm4')
    return parser.parse_args()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    args = get_args()
    logging.info('Input Params:\n'
                 '--------------------------------\n'
                 f'\tinput: {args.input}\n'
                 f'\toutput: {args.output}\n'
                 '--------------------------------')
    # key for cbc encrypt
    enc_string = '64EC7C763AB7BF64E2D75FF83A319910'

    sm4_encrypt(args.input.strip(), args.output.strip(), enc_string)
