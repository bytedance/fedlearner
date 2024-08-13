# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8

import itertools
import tensorflow.compat.v1 as tf
from typing import List


def _parse_tfrecord(record) -> dict:
    example = tf.train.Example()
    example.ParseFromString(record)

    parsed = {}
    for key, value in example.features.feature.items():
        kind = value.WhichOneof('kind')
        if kind == 'float_list':
            parsed[key] = [float(num) for num in value.float_list.value]
        elif kind == 'int64_list':
            parsed[key] = [int(num) for num in value.int64_list.value]
        elif kind == 'bytes_list':
            parsed[key] = [byte.decode() for byte in value.bytes_list.value]
        else:
            raise ValueError('Invalid tfrecord format')

    return parsed


def _get_data(path: str, max_lines: int) -> List:
    reader = tf.io.tf_record_iterator(path)
    reader, _ = itertools.tee(reader)
    records = []
    counter = 0
    for line in reader:
        features = _parse_tfrecord(line)
        records.append(features)
        counter += 1
        if counter >= max_lines:
            break
    return records


def _convert_to_matrix_view(records: List[dict]) -> List:
    first_line = set()
    for features in records:
        first_line = first_line.union(features.keys())
    sort_first_line = list(first_line)
    sort_first_line.sort()
    matrix = [sort_first_line]
    for features in records:
        current_line = []
        for column in sort_first_line:
            if column in features:
                current_line.append(features[column])
            else:
                current_line.append('N/A')
        matrix.append(current_line)
    return matrix


def tf_record_reader(path: str, max_lines: int = 10, matrix_view: bool = False) -> List:
    """Read tfrecord from given path

    Args:
        path: the path of tfrecord file
        max_lines: the maximum number of lines read from file
        matrix_view: whether convert the data to csv-like matrix
    Returns:
        Dictionary or csv-like data
    """
    # read data from tfrecord
    records = _get_data(path, max_lines)
    if not matrix_view:
        return records
    # get sorted first row of the matrix
    matrix = _convert_to_matrix_view(records)
    return matrix
