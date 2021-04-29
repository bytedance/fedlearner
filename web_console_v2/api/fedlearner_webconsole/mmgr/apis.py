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

import json
import logging
from http import HTTPStatus
from flask import request
from flask_restful import Resource
from fedlearner_webconsole.job.metrics import JobMetricsBuilder
from fedlearner_webconsole.job.models import Job, JobType
from fedlearner_webconsole.job.yaml_formatter import generate_job_run_yaml
from fedlearner_webconsole.mmgr.models import Model, ModelType, ModelState


class ModelManager:
    job_state_map = {
        'RUNNING': ModelState.RUNNING,
        'COMPLETED': ModelState.SUCCEEDED,
        'FAILED': ModelState.FAILED,
    }

    def on_job_update(self, job):
        model = Model.query.filter_by(job_name=job.name).one()
        # https://code.byted.org/data/fedlearner_web_console_v2/merge_requests/101
        state = job.get_result_state()
        if model.state != ModelState.RUNNING and state == 'RUNNING':
            model.version += 1
        model.state = self.job_state_map[state]
        model.commit()
        if model.state in [
                ModelState.FINISHED, ModelState.SUCCEEDED, ModelState.FAILED
        ]:
            try:
                metrics = JobMetricsBuilder(job).plot_metrics()
                model.metrics = json.dumps(metrics)
                model.commit()
            except Exception as e:
                logging.warning('Error building metrics: %s', repr(e))

    @staticmethod
    def get_checkpoint_path(job):
        try:
            yaml = generate_job_run_yaml(job)
            # ToDo : OUTPUT_BASE_DIR may not be accurate
            output_base_dir = yaml['OUTPUT_BASE_DIR']
        except Exception as e:
            logging.warning('Error building metrics: %s', repr(e))
            output_base_dir = ''
        return output_base_dir

    # after workflow, before k8s
    def create(self,
               parent_id,
               job,
               dataset=None,
               resource=None,
               callback=None):
        """
        Create a new model and insert into database

        Args:
            parent_id: the inherited model id, if no, set parent_id to None
            job: the associated job, job type must be NN/TREE job
            dataset: the used dataset
            resource: system resouces like cpu/memory
            callback: callback function, which can be used to sync with the
            opposite side
        """
        model = Model()
        model.name = job.name
        model.parent_id = parent_id
        model.job_name = job.name
        if job.job_type == JobType.NN_MODEL_TRANINING:
            model.type = ModelType.NN_MODEL
        elif job.job_type == JobType.NN_MODEL_EVALUATION:
            model.type = ModelType.NN_EVALUATION
            o = Model.query.filter_by(id=parent_id).one()
            model.version = o.version
        elif job.job_type == JobType.TREE_MODEL_TRAINING:
            model.type = ModelType.TREE_MODEL
        elif job.job_type == JobType.TREE_MODEL_EVALUATION:
            model.type = ModelType.TREE_EVALUATION
            o = Model.query.filter_by(id=parent_id).one()
            model.version = o.version
        else:
            raise Exception('Job mush be a NN or Tree job.')
        model.state = ModelState.COMMITTING
        model.params = json.dumps({
            'dataset': dataset,
            'resource': resource,
        })
        model.output_base_dir = self.get_checkpoint_path(job)
        model.state = ModelState.COMMITTING
        model.commit()
        if callback is not None:
            callback()
        model.state = ModelState.COMMITTED
        model.commit()
        return model

    def query(self, model_id, detail_level=0):
        """
        Query a model

        Args:
            model_id: model id
            detail_level: 0, return basic info; 1, query the es
        Returns:
            return model json
        """
        model = Model.query.filter_by(id=model_id).one()
        model_json = model.to_dict()
        model_json['detail_level'] = detail_level
        if detail_level == 0:
            return model_json
        try:
            job = Job.query.filter_by(name=model.job_name).one()
            metrics = JobMetricsBuilder(job).plot_metrics()
            model_json['metrics'] = json.dumps(metrics)
        except Exception as e:
            logging.warning('Error building metrics: %s', repr(e))
        return model_json

    def drop(self, model_id, callback=None):
        """
        Drop a model
        Change model_state to Dropped

        Args:
            model_id: model name
            callback: callback function
        """
        model = Model.query.filter_by(id=model_id).one()
        # flapp should be stopped by workflow, asynchronously
        if model.state == ModelState.RUNNING:
            raise Exception(
                f'cannot delete model when model.state is {model.state}')

        model.state = ModelState.DROPPING
        model.commit()
        if callback is not None:
            callback()
        model.state = ModelState.DROPPED
        model.commit()
        return model


class ModelApi(Resource):
    model_manager = ModelManager()

    def get(self, model_id):
        detail_level = request.args.get('detail_level', 0)
        model_json = self.model_manager.query(model_id, detail_level)
        return {'data': model_json}, HTTPStatus.OK

    def delete(self, model_id):
        model = self.model_manager.drop(model_id)
        return {'data': model.to_dict()}, HTTPStatus.OK


class ModelListApi(Resource):
    model_manager = ModelManager()

    def get(self):
        detail_level = request.args.get('detail_level', 0)
        model_list = [
            self.model_manager.query(m.id, detail_level)
            for m in Model.query.filter(
                Model.type.in_([ModelType.NN_MODEL, ModelType.TREE_MODEL
                               ])).all()
        ]
        return {'data': model_list}, HTTPStatus.OK


def initialize_mmgr_apis(api):
    api.add_resource(ModelListApi, '/models')
    api.add_resource(ModelApi, '/model/<string:model_id>')
