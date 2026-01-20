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
import logging
import argparse

from pyspark.sql import SparkSession
from pyspark.sql.types import StringType
from pyspark.mllib.random import RandomRDDs
import pyspark.sql.functions as f

_RAW_ID = 'raw_id'
_DEFAULT_PARTITIONS = 16

DISTRIBUTION_FUNC_MAP = {
    'normal': RandomRDDs.normalVectorRDD,
    'uniform': RandomRDDs.uniformVectorRDD,
    'exponential': RandomRDDs.exponentialVectorRDD,
    'log': RandomRDDs.logNormalVectorRDD,
    'gamma': RandomRDDs.gammaVectorRDD
}


def make_data(output_dir_path: str,
              items_num: int,
              features_num: int,
              partitions_num: int = _DEFAULT_PARTITIONS,
              distribution: str = 'uniform'):
    logging.info('========start========')
    output_dir_path = output_dir_path.strip()
    spark = SparkSession.builder.getOrCreate()
    sc = spark.sparkContext
    if distribution in DISTRIBUTION_FUNC_MAP:
        feature_df = DISTRIBUTION_FUNC_MAP[distribution](sc, items_num, features_num,
                                                         partitions_num).map(lambda a: a.tolist()).toDF()
    else:
        logging.error(f'### no valid distribution: {distribution}')
        return
    df = feature_df.withColumn(_RAW_ID, f.md5(feature_df._1.cast(StringType())))
    df.write.format('csv').option('compression', 'none').option('header', 'true').save(path=output_dir_path,
                                                                                       mode='overwrite')
    spark.stop()
    logging.info('========done========')


def get_args():
    parser = argparse.ArgumentParser(description='convert bio dataset to coco format dataset.')
    parser.add_argument('--output_dir_path',
                        '-o',
                        required=True,
                        type=str,
                        dest='output_dir_path',
                        help='dir of output')
    parser.add_argument('--items', '-i', type=int, required=True, dest='items_num', help='number of items')
    parser.add_argument('--features', '-f', type=int, required=True, dest='features_num', help='number of features')
    parser.add_argument('--partitions_num', '-p', type=int, required=False, dest='partitions_num')
    parser.add_argument('--distribution',
                        '-d',
                        required=False,
                        type=str,
                        dest='distribution',
                        help='the distribution of the feature. could be: normal/uniform/exponential/log/gamma')
    return parser.parse_args()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    args = get_args()
    logging.info(f'\toutput dir: {args.output_dir_path}\n'
                 f'\titems_num is: {args.items_num}\n'
                 f'\tfeature_num is: {args.features_num}\n'
                 f'\tpartitions_num is: {args.partitions_num if args.partitions_num else _DEFAULT_PARTITIONS}\n'
                 f'\tdistribution is: {args.distribution}')
    make_data(args.output_dir_path, args.items_num, args.features_num, args.partitions_num)
