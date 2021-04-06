# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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

from http import HTTPStatus
from flask import request
from flask_restful import Resource

from fedlearner_webconsole.mmgr.models import *


class ModelManager:
    def on_job_start(self):
        pass

    def on_job_running(self):
        # periodic
        pass

    def on_job_done(self):
        pass

    def new(self, model_id, parent_id, dataset, resource):
        model = Model()
        model.id = model_id
        model.parent_id = parent_id
        model.type = "MODEL"
        model.state = 'COMMITTING'
        model.commit()

        # TODO start k8s

        model.state = 'COMMITTED'
        model.commit()

    def query(self, detail_level, model_id):
        model = query_model(model_id)
        if not model: return model

        model.detail_level = detail_level
        return model

    def eval(self, evaluation_id, model_id, dataset, resource):
        model = Model()
        model.id = evaluation_id
        model.parent_id = model_id
        model.type = "EVALUATION"
        model.state = 'COMMITTING'
        model.commit()

        # TODO start k8s

        model.state = 'COMMITTED'
        model.commit()

    def drop(self, model_id):
        model = query_model(model_id)
        if not model: return model

        model.state = 'DROPPING'
        model.commit()

        # TODO stop k8s flapp
        # TODO remove NFS resources

        model.state = 'DROPPED'
        model.commit()

    def list(self):
        return query_models()


class ModelApi(Resource):
    model_manager = ModelManager()

    def get(self, model_id):
        detail_level = request.args.get('detail_level')
        o = self.model_manager.query(detail_level, model_id)
        return model_to_json(o), HTTPStatus.OK

    def delete(self, model_id):
        ModelManager().drop(model_id)
        return None, HTTPStatus.OK


class ModelListApi(Resource):
    model_manager = ModelManager()

    def get(self):
        detail_level = request.args.get('detail_level')
        return list(map(lambda o: self.query(detail_level, o.id), self.model_manager.list())), HTTPStatus.OK

    def query(self, detail_level, model_id):
        return model_to_json(self.model_manager.query(detail_level, model_id))


def initialize_mmgr_apis(api):
    api.add_resource(ModelListApi, '/models')
    api.add_resource(ModelApi, '/model/<string:model_id>')
