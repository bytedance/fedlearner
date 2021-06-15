# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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
import json
import logging
from fedlearner_webconsole.db import make_session_context
from fedlearner_webconsole.job.metrics import JobMetricsBuilder
from fedlearner_webconsole.job.models import Job, JobType, JobState, JobDefinition
from fedlearner_webconsole.job.yaml_formatter import generate_job_run_yaml
from fedlearner_webconsole.mmgr.models import Model, ModelType, ModelState
from fedlearner_webconsole.utils.k8s_cache import Event, EventType, ObjectType


class ModelService:

    def __init__(self, session):
        self._session = session

    job_type_map = {
        JobType.NN_MODEL_TRANINING: ModelType.NN_MODEL.value,
        JobType.NN_MODEL_EVALUATION: ModelType.NN_EVALUATION.value,
        JobType.TREE_MODEL_TRAINING: ModelType.TREE_MODEL.value,
        JobType.TREE_MODEL_EVALUATION: ModelType.TREE_EVALUATION.value
    }

    job_state_map = {
        JobState.STARTED: ModelState.RUNNING.value,
        JobState.COMPLETED: ModelState.SUCCEEDED.value,
        JobState.FAILED: ModelState.FAILED.value,
        JobState.STOPPED: ModelState.PAUSED.value,
        JobState.WAITING: ModelState.WAITING.value
    }

    @staticmethod
    def is_model_related_job(job):
        job_type = job.job_type
        if isinstance(job_type, int):
            job_type = JobType(job.job_type)
        return job_type in [
            JobType.NN_MODEL_TRANINING, JobType.NN_MODEL_EVALUATION,
            JobType.TREE_MODEL_TRAINING, JobType.TREE_MODEL_EVALUATION
        ]

    def k8s_watcher_hook(self, event: Event):
        logging.info('[ModelService][k8s_watcher_hook] %s %s: %s', event.obj_type, event.event_type, event.flapp_name)
        if event.obj_type == ObjectType.FLAPP and event.event_type in [
                EventType.MODIFIED, EventType.DELETED
        ]:
            job = self._session.query(Job).filter_by(
                name=event.flapp_name).one_or_none()
            if not job:
                return logging.warning('[ModelService][k8s_watcher_hook] job not found: %s', event.flapp_name)
            if self.is_model_related_job(job):
                self.on_job_update(job)

    def workflow_hook(self, job: Job):
        if self.is_model_related_job(job):
            self.create(job)

    def plot_metrics(self, model, job=None):
        try:
            return JobMetricsBuilder(job or model.job).plot_metrics()
        except Exception as e:
            return repr(e)

    def is_model_quiescence(self, state):
        return state in [
            ModelState.SUCCEEDED.value, ModelState.FAILED.value,
            ModelState.PAUSED.value
        ]

    def on_job_update(self, job: Job):
        logging.info('[ModelService][on_job_update] job name: %s', job.name)
        model = self._session.query(Model).filter_by(job_name=job.name).one()
        # see also `fedlearner_webconsole.job.models.Job.stop`
        if job.state in self.job_state_map:
            state = self.job_state_map[job.state]
        else:
            return logging.warning(
                '[ModelService][on_job_update] job state is %s', job.state)
        if model.state != ModelState.RUNNING.value and state == ModelState.RUNNING.value:
            logging.info(
                '[ModelService][on_job_update] updating model(%d).version from %s to %s',
                model.id, model.version, model.version + 1)
            model.version += 1
        logging.info(
            '[ModelService][on_job_update] updating model(%d).state from %s to %s',
            model.id, model.state, state)
        if self.is_model_quiescence(state):
            model.metrics = json.dumps(self.plot_metrics(model, job))
        model.state = state
        self._session.add(model)

    def create(self, job: Job, parent_job_name=None, group_id=0):
        logging.info('[ModelService][create] create model %s', job.name)
        model = Model()
        model.name = job.name  # TODO allow rename by end-user
        model.type = self.job_type_map[job.job_type]
        model.state = ModelState.COMMITTING.value
        model.job_name = job.name
        if parent_job_name:
            parent = self._session.query(Model).filter_by(
                job_name=parent_job_name).one_or_none()
            if not parent:
                return parent
            model.version = parent.version
            model.parent_id = parent.id
        model.params = json.dumps({})
        model.group_id = group_id
        model.state = ModelState.COMMITTED.value
        self._session.add(model)
        self._session.commit()
        return model

    # `detail_level` is a comma separated string list
    # contains `metrics` if `plot_metrics` result is
    def query(self, model_id, detail_level=''):
        model = self._session.query(Model).filter_by(id=model_id).one_or_none()
        if not model:
            return model
        detail_level = detail_level.split(',')
        model_json = model.to_dict()
        model_json['detail_level'] = detail_level
        if 'metrics' in detail_level:
            if self.is_model_quiescence(model) and model.metrics:
                model_json['metrics'] = json.loads(model.metrics)
            else: model_json['metrics'] = self.plot_metrics(model)
        return model_json

    def drop(self, model_id):
        model = self._session.query(Model).filter_by(id=model_id).one_or_none()
        if not model:
            return model
        if model.state not in [
                ModelState.SUCCEEDED.value, ModelState.FAILED.value
        ]:  # FIXME atomicity
            raise Exception(
                f'cannot delete model when model.state is {model.state}')
        # model.state = ModelState.DROPPING.value
        # TODO remove model files from NFS et al.
        model.state = ModelState.DROPPED.value
        self._session.add(model)
        self._session.commit()
        return model

    def get_checkpoint_path(self, job):
        return None
