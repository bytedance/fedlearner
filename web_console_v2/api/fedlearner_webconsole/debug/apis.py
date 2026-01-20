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
import datetime
import json

import tensorflow as tf
import yaml
from flask_restful import Resource, Api, request, reqparse

from fedlearner_webconsole.composer.composer_service import ComposerService
from fedlearner_webconsole.composer.models import SchedulerRunner, \
    SchedulerItem
from fedlearner_webconsole.utils.tfrecords_reader import tf_record_reader
from fedlearner_webconsole.exceptions import InvalidArgumentException
from fedlearner_webconsole.k8s.k8s_cache import k8s_cache
from fedlearner_webconsole.k8s.k8s_client import k8s_client
from fedlearner_webconsole.db import db


class DebugComposerApi(Resource):

    def get(self, name):
        cron_config = request.args.get('cron_config')
        finish = request.args.get('finish', 0)
        with db.session_scope() as session:
            service = ComposerService(session)
            if int(finish) == 1:
                service.finish(name)
            session.commit()
            return {'data': {'name': name}}


class DebugSparkAppApi(Resource):

    def post(self, name: str):
        data = yaml.load(f"""
apiVersion: "sparkoperator.k8s.io/v1beta2"
kind: SparkApplication
metadata:
  name: {name}
  namespace: default
spec:
  type: Python
  pythonVersion: "3"
  mode: cluster
  image: "registry.cn-beijing.aliyuncs.com/fedlearner/spark-tfrecord:latest"
  imagePullPolicy: Always
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: pvc-fedlearner-default
  mainApplicationFile: local:///data/sparkapp_test/tyt_test/schema_check.py
  arguments:
    - /data/sparkapp_test/tyt_test/test.csv
    - /data/sparkapp_test/tyt_test/schema.json
  sparkVersion: "3.0.0"
  restartPolicy:
    type: OnFailure
    onFailureRetries: 3
    onFailureRetryInterval: 10
    onSubmissionFailureRetries: 5
    onSubmissionFailureRetryInterval: 20
  driver:
    cores: 1
    coreLimit: "1200m"
    memory: "512m"
    labels:
      version: 3.0.0
    serviceAccount: spark
    volumeMounts:
        - name: data
          mountPath: /data
  executor:
    cores: 1
    instances: 1
    memory: "512m"
    labels:
      version: 3.0.0
    volumeMounts:
        - name: data
          mountPath: /data
""",
                         Loader=None)
        data = k8s_client.create_sparkapplication(data)
        return {'data': data}


class DebugK8sCacheApi(Resource):

    def get(self):

        def default(o):
            if isinstance(o, (datetime.date, datetime.datetime)):
                return o.isoformat()
            return str(o)

        return {'data': json.dumps(k8s_cache.inspect(), default=default)}


class DebugTfRecordApi(Resource):

    def get(self):
        path = request.args.get('path', None)

        if path is None or not tf.io.gfile.exists(path):
            raise InvalidArgumentException('path is not found')

        lines = request.args.get('lines', 25, int)
        tf_matrix = tf_record_reader(path, lines, matrix_view=True)

        return {'data': tf_matrix}


class DebugSchedulerItemsApi(Resource):

    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('status', type=int, location='args', required=False, choices=[0, 1])
        parser.add_argument('id', type=int, location='args', required=False)
        data = parser.parse_args()
        with db.session_scope() as session:
            items = session.query(SchedulerItem)
            if data['status'] is not None:
                items = items.filter_by(status=data['status'])
            if data['id'] is not None:
                runners = session.query(SchedulerRunner).filter_by(item_id=data['id']).order_by(
                    SchedulerRunner.updated_at.desc()).limit(10).all()
                return {'data': [runner.to_dict() for runner in runners]}
            items = items.order_by(SchedulerItem.created_at.desc()).all()
            return {'data': [item.to_dict() for item in items]}


class DebugSchedulerRunnersApi(Resource):

    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('status', type=int, location='args', required=False, choices=[0, 1, 2, 3])
        data = parser.parse_args()
        with db.session_scope() as session:
            runners = session.query(SchedulerRunner)
            if data['status'] is not None:
                runners = runners.filter_by(status=data['status'])
            runners = runners.order_by(SchedulerRunner.updated_at.desc()).all()
            return {'data': [runner.to_dict() for runner in runners]}


def initialize_debug_apis(api: Api):
    api.add_resource(DebugComposerApi, '/debug/composer/<string:name>')
    api.add_resource(DebugSparkAppApi, '/debug/sparkapp/<string:name>')
    api.add_resource(DebugK8sCacheApi, '/debug/k8scache/')
    api.add_resource(DebugTfRecordApi, '/debug/tfrecord')
    api.add_resource(DebugSchedulerItemsApi, '/debug/scheduler_items')
    api.add_resource(DebugSchedulerRunnersApi, '/debug/scheduler_runners')
