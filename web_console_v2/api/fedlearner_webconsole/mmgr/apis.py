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
import shutil

from fedlearner_webconsole.mmgr.models import *


class ModelManager:
    def on_job_start(self, job):
        model = Model.query.filter_by(job_id=job.name).one()
        if model.state != 'COMMITTED': raise Exception(f'model.state is {model.state}')
        model.state = 'RUNNING'
        model.commit()

    def on_job_running(self, job):
        model = Model.query.filter_by(job_id=job.name).one()
        if model.state != 'RUNNING': raise Exception(f'model.state is {model.state}')
        model.state = 'RUNNING'
        model.commit()

    def on_job_done(self, job):
        model = Model.query.filter_by(job_id=job.name).one()
        if model.state != 'RUNNING': raise Exception(f'model.state is {model.state}')
        model.state = 'FAILED/SUCCEEDED'
        model.commit()

    def train(self, model_id, parent_id, job_id, model_type, dataset, resource, func):
        model = Model()
        model.id = model_id
        model.parent_id = parent_id
        model.job_id = job_id
        model.type = 'MODEL'
        model.state = 'COMMITTING'
        model.params = json.dumps({
            'model_type': model_type,  # NN/Tree
            'dataset': dataset,
            'resource': resource,
        })
        model.commit()

        func()

        model.state = 'COMMITTED'
        model.commit()

    def query(self, detail_level, model_id):
        model = Model.query.filter_by(id=model_id).one()
        # job = Job.query.filter_by(name=model.job_id).one()

        model.detail_level = detail_level
        return model

    def eval(self, evaluation_id, model_id, job_id, dataset, resource, func):
        model = Model.query.filter_by(id=model_id).one()

        evaluation = Model()
        evaluation.id = evaluation_id
        evaluation.parent_id = model.id
        evaluation.job_id = job_id
        evaluation.type = 'EVALUATION'
        evaluation.state = 'COMMITTING'
        evaluation.params = json.dumps({
            'dataset': dataset,
            'resource': resource,
        })
        evaluation.commit()

        func()

        evaluation.state = 'COMMITTED'
        evaluation.commit()

    def drop(self, model_id):
        model = Model.query.filter_by(id=model_id).one()
        # flapp should be stopped by workflow, asynchronously
        if model.state not in ['FAILED', 'SUCCEEDED']: raise Exception(f'model.state is {model.state}')

        model.state = 'DROPPING'
        model.commit()

        shutil.rmtree(f'/data/output/{model.id}', True)

        model.state = 'DROPPED'
        model.commit()


class ModelApi(Resource):
    model_manager = ModelManager()

    def get(self, model_id):
        detail_level = request.args.get('detail_level')
        o = self.model_manager.query(detail_level, model_id)
        return model_to_json(o), HTTPStatus.OK

    def delete(self, model_id):
        self.model_manager.drop(model_id)
        return None, HTTPStatus.OK


class ModelListApi(Resource):
    model_manager = ModelManager()

    def get(self):
        detail_level = request.args.get('detail_level')
        return list(map(lambda o: self.query(detail_level, o.id), Model.query.all())), HTTPStatus.OK

    def query(self, detail_level, model_id):
        return model_to_json(self.model_manager.query(detail_level, model_id))


def initialize_mmgr_apis(api):
    api.add_resource(ModelListApi, '/models')
    api.add_resource(ModelApi, '/model/<string:model_id>')
