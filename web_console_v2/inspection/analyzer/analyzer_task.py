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

import os
import json
import logging
from typing import Optional
import fsspec
import cv2
import numpy as np
from numpy import array
from copy import deepcopy

from pyspark import SparkContext
from pyspark.sql import SparkSession
from pyspark.sql import functions as spark_func
from pyspark.sql.dataframe import DataFrame
from pyspark.sql.column import _to_java_column, _to_seq, Column
from dataset_directory import DatasetDirectory

from util import load_tfrecords, is_file_matched
from error_code import AreaCode, ErrorType, JobException

_DEFAULT_BUCKETS_NUM = 10
_DEFAULT_SAMPLES_NUM = 20
_MAX_SIZE = (256, 256)
_THUMBNAIL_EXTENSION = '.png'
_METRICS_UNSUPPORT_COLUMN_TYPE = [
    'binary',
]
_HIST_UNSUPPORT_COLUMN_TYPE = ['string', 'binary']


def _is_metrics_support_type(column_type: str):
    return column_type not in _METRICS_UNSUPPORT_COLUMN_TYPE and not column_type.startswith('array')


def _is_hist_support_type(column_type: str):
    return column_type not in _HIST_UNSUPPORT_COLUMN_TYPE and not column_type.startswith('array')


def _hist_func(feat_col: Column, min_num: float, max_num: float, bins_num: int, interval: float, sc: SparkContext):
    hist = sc._jvm.com.bytedance.aml.enterprise.sparkudaf.Hist.getFunc()  # pylint: disable=protected-access
    return Column(
        hist.apply(
            _to_seq(sc, [
                feat_col,
                spark_func.lit(min_num),
                spark_func.lit(max_num),
                spark_func.lit(bins_num),
                spark_func.lit(interval)
            ], _to_java_column)))


def _decode_binary_to_array(data: bytearray, h: int, w: int, c: int) -> array:
    return np.reshape(data, (h, w, c))


def _get_thumbnail(img: array, height: int, width: int) -> array:
    size = (min(height, _MAX_SIZE[0]), min(width, _MAX_SIZE[1]))
    return cv2.resize(img, size, interpolation=cv2.INTER_AREA)


# TODO(liuhehan): seperate this analyzer task to meta_task and preview_task
class AnalyzerTask(object):

    def _extract_feature_metrics(self, df: DataFrame, dtypes_dict: dict) -> dict:
        df_missing = df.select(*(spark_func.sum(spark_func.col(c).isNull().cast('int')).alias(c)
                                 for c in df.columns
                                 if _is_metrics_support_type(dtypes_dict[c]))).withColumn(
                                     'summary', spark_func.lit('missing_count'))
        df_stats = df.describe().unionByName(df_missing)
        df_stats = df_stats.toPandas().set_index('summary').transpose()
        return df_stats.to_dict(orient='index')

    def _extract_metadata(self, df: DataFrame, is_image: bool) -> dict:
        """
        meta = {
            label_count: [dict]
            count: int
            dtypes: [{'key': feature_name, 'value': feature_type},..],
            sample: [row],
        }
        """
        meta = {}
        # dtypes
        logging.info('### loading dtypes...')
        dtypes = []
        for d in df.dtypes:
            k, v = d  # (feature, type)
            dtypes.append({'key': k, 'value': v})
        # TODO(wangzeju): refactor the key names
        meta['dtypes'] = deepcopy(dtypes)
        # remove binary in image metadata, add label-count
        if is_image:
            meta['dtypes'] = [item for item in meta['dtypes'] if item['key'] != 'data']
            # TODO(wangzeju): hard code to count for each category
            # need to support more data/label formats on more columns.
            if 'label' in df.columns:
                label_count_rows = df.groupBy('label').count().collect()
                label_count = [row.asDict() for row in label_count_rows]
                meta['label_count'] = label_count
        # sample count
        logging.info('### loading count...')
        meta['count'] = df.count()
        # sample and thumbnail
        logging.info('### loading sample...')
        rows = df.head(_DEFAULT_SAMPLES_NUM)
        samples = []
        for row in rows:
            sample = [row[col_map['key']] for col_map in meta['dtypes']]
            samples.append(sample)
        meta['sample'] = samples
        return meta

    def _extract_thumbnail(self, df: DataFrame, thumbnail_path: str):
        samples = df.head(_DEFAULT_SAMPLES_NUM)
        for row in samples:
            item = row.asDict()
            h, w, c = item['height'], item['width'], item['nChannels']
            file_name, raw_data = item['file_name'], item['data']
            img_array = _decode_binary_to_array(raw_data, h, w, c)
            logging.info(f'### process with {file_name}')
            img = _get_thumbnail(img_array, h, w)
            logging.info(f'### {file_name} shape is:{img.shape}')
            # get thumbnail file_name in _THUMBNAIL_EXTENSION
            thumbnail_file_name = file_name.split('.')[0] + _THUMBNAIL_EXTENSION
            img_path = os.path.join(thumbnail_path, thumbnail_file_name)
            success, encoded_image = cv2.imencode(_THUMBNAIL_EXTENSION, img)
            bytes_content = encoded_image.tobytes()
            logging.info(f'### will write bytes_content to {img_path}')
            with fsspec.open(img_path, mode='wb') as f:
                f.write(bytes_content)

    def _extract_feature_hist(self, spark: SparkSession, df: DataFrame, dtypes_dict: dict, buckets_num: int) -> dict:
        # feature histogram
        logging.info('### loading hist...')
        hist = {}
        feat_col_list = [(col_idx, col_name)
                         for col_idx, col_name in enumerate(df.columns)
                         if _is_hist_support_type(dtypes_dict[col_name])]
        if feat_col_list:
            # When there is a NaN value, spark's max function will get a NaN result
            # so it needs to be filled with the default value of zero
            filled_df = df.na.fill(0)
            min_col_list = [
                spark_func.min(spark_func.col(col_name)).alias(f'{col_name}-min')
                for (col_idx, col_name) in feat_col_list
            ]
            max_col_list = [
                spark_func.max(spark_func.col(col_name)).alias(f'{col_name}-max')
                for (col_idx, col_name) in feat_col_list
            ]
            minmax_df = filled_df.select(*(min_col_list + max_col_list))
            minmax_row = minmax_df.collect()[0]
            hist_args_map = {}
            for col_idx, col_name in feat_col_list:
                min_num = minmax_row[f'{col_name}-min']
                max_num = minmax_row[f'{col_name}-max']
                hist_args = (spark_func.col(col_name), min_num, max_num, buckets_num, (max_num - min_num) / buckets_num,
                             spark.sparkContext)
                hist_args_map[col_name] = hist_args
            logging.info(f'### will get the hist statistics for feat cols: {feat_col_list}')
            hist_result = df.select(
                *[_hist_func(*hist_args_map[col_name]).alias(col_name) for (_, col_name) in feat_col_list]).collect()
            for (_, col_name), col_result in zip(feat_col_list, hist_result[0]):
                hist[col_name] = {'x': col_result['bins'], 'y': col_result['counts']}
        return hist

    def run(self, spark: SparkSession, dataset_path: str, wildcard: str, is_image: bool, batch_name: str,
            buckets_num: Optional[int], thumbnail_path: Optional[str]):
        """extract metadata, features' metrics, hists and thumbnail for image format

        Args:
            spark: spark session
            dataset_path: path of dataset.
            wildcard: the wildcard to match all tfrecords
            is_image: whether it is an image type
            batch_name: name of target batch which need analyze
            buckets_num: the number of bucket to extract feature hist
            thumbnail_path: dir path to save the thumbnails

        Raises:
            JobException: read data by pyspark failed
        """
        if buckets_num is None:
            buckets_num = _DEFAULT_BUCKETS_NUM
        dataset_directory = DatasetDirectory(dataset_path=dataset_path)
        files = dataset_directory.batch_path(batch_name=batch_name)
        meta_path = dataset_directory.batch_meta_file(batch_name=batch_name)
        if not is_file_matched(files):
            # this is a hack to allow empty intersection dataset
            # no file matched, just skip analyzer
            logging.warning(f'input_dataset_path {files} matches 0 file, skip analyzer task')
            return
        # load data
        try:
            df = load_tfrecords(spark, files, dataset_path)
        except Exception as e:  # pylint: disable=broad-except
            raise JobException(AreaCode.ANALYZER, ErrorType.DATA_LOAD_ERROR,
                               f'failed to read input data, err: {str(e)}') from e
        if df.count() == 0:
            # this is a hack to allow empty intersection dataset
            # all files are empty, just skip analyzer
            logging.warning(f'get 0 data item in {files}, skip analyzer task')
            return
        dtypes_dict = dict(df.dtypes)
        # extract pipeline
        meta = self._extract_metadata(df, is_image)
        meta['features'] = self._extract_feature_metrics(df, dtypes_dict)
        if is_image:
            self._extract_thumbnail(df, thumbnail_path)
        meta['hist'] = self._extract_feature_hist(spark, df, dtypes_dict, buckets_num)
        # save metadata to file
        logging.info(f'### writing meta, path is {meta_path}')
        with fsspec.open(meta_path, mode='w') as f:
            f.write(json.dumps(meta))
