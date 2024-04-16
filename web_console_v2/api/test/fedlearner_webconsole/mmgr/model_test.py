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

import unittest
from unittest.mock import MagicMock, patch

from testing.common import BaseTestCase
from fedlearner_webconsole.db import db, get_session
from fedlearner_webconsole.mmgr.models import Model
from fedlearner_webconsole.mmgr.models import ModelState
from fedlearner_webconsole.mmgr.service import ModelService
from fedlearner_webconsole.job.models import Job, JobType, JobState
from fedlearner_webconsole.utils.k8s_cache import Event, EventType, ObjectType


class ModelTest(BaseTestCase):
    @patch(
        'fedlearner_webconsole.mmgr.service.ModelService.get_checkpoint_path')
    def setUp(self, mock_get_checkpoint_path):
        super().setUp()
        self.model_service = ModelService(db.session)
        self.train_job = Job(name='train-job',
                             job_type=JobType.NN_MODEL_TRANINING,
                             workflow_id=1,
                             project_id=1)
        self.eval_job = Job(name='eval-job',
                            job_type=JobType.NN_MODEL_EVALUATION,
                            workflow_id=1,
                            project_id=1)
        mock_get_checkpoint_path.return_value = 'output'
        self.model_service.create(job=self.train_job, parent_job_name=None)
        model = db.session.query(Model).filter_by(
            job_name=self.train_job.name).one()
        self.model_service.create(job=self.eval_job,
                                  parent_job_name=model.job_name)
        db.session.add(self.train_job)
        db.session.add(self.eval_job)
        db.session.commit()

    @patch('fedlearner_webconsole.mmgr.service.ModelService.plot_metrics')
    def test_on_job_update(self, mock_plot_metrics: MagicMock):
        mock_plot_metrics.return_value = 'plot metrics return'

        # TODO: change get_session to db.session_scope
        with get_session(db.engine) as session:
            model = session.query(Model).filter_by(
                job_name=self.train_job.name).one()
            self.assertEqual(model.state, ModelState.COMMITTED.value)

            train_job = session.query(Job).filter_by(name='train-job').one()
            train_job.state = JobState.STARTED
            session.commit()

        # TODO: change get_session to db.session_scope
        with get_session(db.engine) as session:
            train_job = session.query(Job).filter_by(name='train-job').one()
            train_job.state = JobState.STARTED
            model = session.query(Model).filter_by(
                job_name=self.train_job.name).one()
            model_service = ModelService(session)

            model_service.on_job_update(train_job)
            self.assertEqual(model.state, ModelState.RUNNING.value)
            session.commit()

        # TODO: change get_session to db.session_scope
        with get_session(db.engine) as session:
            train_job = session.query(Job).filter_by(name='train-job').one()
            train_job.state = JobState.COMPLETED
            model = session.query(Model).filter_by(
                job_name=self.train_job.name).one()
            model_service = ModelService(session)

            model_service.on_job_update(train_job)
            self.assertEqual(model.state, ModelState.SUCCEEDED.value)
            session.commit()

        # TODO: change get_session to db.session_scope
        with get_session(db.engine) as session:
            train_job = session.query(Job).filter_by(name='train-job').one()
            train_job.state = JobState.FAILED
            model = session.query(Model).filter_by(
                job_name=self.train_job.name).one()
            model_service = ModelService(session)

            model_service.on_job_update(train_job)
            self.assertEqual(model.state, ModelState.FAILED.value)
            session.commit()

    def test_hook(self):
        train_job = Job(id=0,
                        state=JobState.STARTED,
                        name='nn-train',
                        job_type=JobType.NN_MODEL_TRANINING,
                        workflow_id=0,
                        project_id=0)
        db.session.add(train_job)
        db.session.commit()
        event = Event(flapp_name='nn-train',
                      event_type=EventType.ADDED,
                      obj_type=ObjectType.FLAPP,
                      obj_dict={})
        self.model_service.workflow_hook(train_job)
        model = Model.query.filter_by(job_name='nn-train').one()
        self.assertEqual(model.state, ModelState.COMMITTED.value)

        event.event_type = EventType.MODIFIED
        train_job.state = JobState.STARTED
        self.model_service.k8s_watcher_hook(event)
        self.assertEqual(model.state, ModelState.RUNNING.value)

        train_job.state = JobState.COMPLETED
        self.model_service.k8s_watcher_hook(event)
        self.assertEqual(model.state, ModelState.SUCCEEDED.value)

        train_job.state = JobState.STARTED
        self.model_service.k8s_watcher_hook(event)
        self.assertEqual(model.state, ModelState.RUNNING.value)
        self.assertEqual(model.version, 2)

        train_job.state = JobState.STOPPED
        self.model_service.k8s_watcher_hook(event)
        self.assertEqual(model.state, ModelState.PAUSED.value)
        db.session.rollback()

    def test_api(self):
        resp = self.get_helper('/api/v2/models/1')
        data = self.get_response_data(resp)
        self.assertEqual(data.get('id'), 1)

        resp = self.get_helper('/api/v2/models')
        model_list = self.get_response_data(resp)
        self.assertEqual(len(model_list), 1)

        model = Model.query.first()
        model.state = ModelState.FAILED.value
        db.session.add(model)
        db.session.commit()
        self.delete_helper('/api/v2/models/1')
        resp = self.get_helper('/api/v2/models/1')
        data = self.get_response_data(resp)
        self.assertEqual(data.get('state'), ModelState.DROPPED.value)

    def test_get_eval(self):
        model = Model.query.filter_by(job_name=self.train_job.name).one()
        self.assertEqual(len(model.get_eval_model()), 1)


if __name__ == '__main__':
    unittest.main()
