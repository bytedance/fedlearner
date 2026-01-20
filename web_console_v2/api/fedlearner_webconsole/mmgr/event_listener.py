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

import logging

from fedlearner_webconsole.db import db
from fedlearner_webconsole.utils.metrics import emit_store
from fedlearner_webconsole.k8s.k8s_cache import Event, EventType, ObjectType
from fedlearner_webconsole.job.models import Job, JobState
from fedlearner_webconsole.mmgr.models import Model, ModelJob, ModelJobType
from fedlearner_webconsole.mmgr.service import ModelService
from fedlearner_webconsole.k8s.event_listener import EventListener


def _is_model_event(event: Event) -> bool:
    return event.obj_type in [ObjectType.FLAPP, ObjectType.FEDAPP
                             ] and event.event_type in [EventType.MODIFIED, EventType.DELETED]


class ModelEventListener(EventListener):

    def update(self, event: Event):
        if not _is_model_event(event):
            return
        job_name = event.app_name
        with db.session_scope() as session:
            job: Job = session.query(Job).filter_by(name=job_name).first()
            logging.debug('[ModelEventListener] job: %s, type: %s, state: %s', job.name, job.job_type, job.state)
            if job is None:
                emit_store('job_not_found', 1)
                logging.warning('[ModelEventListener] job %s is not found', job_name)
                return
            if not job.is_training_job():
                logging.debug(f'[ModelEventListener] stop creating model due to job {job.name} is not training')
                return
            if not job.state == JobState.COMPLETED:
                logging.debug(f'[ModelEventListener] stop creating model due to job {job.name} is not completed')
                return
            model = session.query(Model).filter_by(job_id=job.id).first()
            if model is not None:
                logging.debug(
                    f'[ModelEventListener] stop creating model due to model is already created for job {job.name}')
                return
            model_job: ModelJob = session.query(ModelJob).filter_by(job_name=job.name).first()
            if model_job is None:
                logging.info(f'[ModelEventListener] stop creating model due to {job.name} is not a model job')
                return
            if model_job.model_job_type not in [ModelJobType.TRAINING, ModelJobType.EVALUATION]:
                logging.info(f'[ModelEventListener] stop creating model due to model job {model_job.name} '
                             'is not training or evaluation')
                return
            service = ModelService(session)
            service.create_model_from_model_job(model_job=model_job)
            logging.info(f'[ModelEventListener] model for job {job.name} is created')
            session.commit()
        with db.session_scope() as session:
            model_job = session.query(ModelJob).filter_by(job_name=job.name).first()
            model = session.query(Model).filter_by(model_job_id=model_job.id).first()
            if model is not None:
                model_job.model_id = model.id
            session.add(model_job)
            session.commit()
