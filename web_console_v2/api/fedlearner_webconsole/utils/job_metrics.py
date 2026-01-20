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
import os
import logging
import tensorflow.compat.v1 as tf
from typing import Dict
from google.protobuf import text_format
from fedlearner_webconsole.job.models import Job
from fedlearner_webconsole.proto.tree_model_pb2 import BoostingTreeEnsambleProto
from fedlearner_webconsole.utils.file_manager import file_manager


def get_feature_importance(job: Job) -> Dict[str, float]:
    storage_root_dir = job.project.get_storage_root_path(None)
    if storage_root_dir is None:
        return {}
    job_name = job.name
    path = os.path.join(storage_root_dir, 'job_output', job_name, 'exported_models')
    if not file_manager.exists(path):
        return {}
    fin = tf.io.gfile.GFile(path, 'r')
    model = BoostingTreeEnsambleProto()
    try:
        text_format.Parse(fin.read(), model, allow_unknown_field=True)
    except Exception as e:  # pylint: disable=broad-except
        logging.warning('parsing tree proto with error %s', str(e))
        return {}
    fscore = model.feature_importance
    feature_names = list(model.feature_names)
    cat_feature_names = list(model.cat_feature_names)
    feature_names.extend(cat_feature_names)
    if len(feature_names) == 0:
        feature_names = [f'f{i}' for i in range(len(fscore))]
    feature_importance = {}
    for i, name in enumerate(feature_names):
        feature_importance[name] = fscore[i]
    for j in range(len(feature_names), len(fscore)):
        feature_importance[f'peer_f{j}'] = fscore[j]
    return feature_importance
