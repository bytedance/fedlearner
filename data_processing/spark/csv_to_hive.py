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

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lower


def run():
    spark = SparkSession \
        .builder \
        .enableHiveSupport() \
        .config('hive.exec.dynamic.partition', 'true') \
        .config('hive.exec.dynamic.partition.mode', 'nonstrict') \
        .getOrCreate()

    df = spark.read.option('header', 'false') \
        .csv('/home/byte_aml_tob/fedlearner_v2/njb/reduced.csv')
    df = df.select(lower(col(df.columns[0])).alias('phone_sha256'))
    df.write.mode('overwrite').insertInto('aml_tob.njb_intersection_sha256')
    spark.stop()


if __name__ == '__main__':
    run()
