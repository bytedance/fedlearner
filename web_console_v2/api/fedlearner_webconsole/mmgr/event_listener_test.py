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

import unittest
from unittest.mock import patch, MagicMock
from testing.common import NoWebServerTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.mmgr.models import Model, ModelJob, ModelJobType
from fedlearner_webconsole.mmgr.event_listener import _is_model_event, ModelEventListener
from fedlearner_webconsole.job.models import Job, JobType, JobState
from fedlearner_webconsole.k8s.k8s_cache import Event, EventType, ObjectType


class UtilsTest(NoWebServerTestCase):

    def test_is_event_relevant(self):
        self.assertFalse(
            _is_model_event(Event(app_name='test', event_type=EventType.ADDED, obj_type=ObjectType.FLAPP, obj_dict={})))
        self.assertFalse(
            _is_model_event(Event(app_name='test', event_type=EventType.MODIFIED, obj_type=ObjectType.POD,
                                  obj_dict={})))
        self.assertTrue(
            _is_model_event(
                Event(app_name='test', event_type=EventType.MODIFIED, obj_type=ObjectType.FLAPP, obj_dict={})))


class ListenerTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            workflow = Workflow(id=1, name='test-workflow')
            job = Job(name='test-job',
                      project_id=1,
                      job_type=JobType.NN_MODEL_TRANINING,
                      state=JobState.COMPLETED,
                      workflow_id=1)
            session.add_all([workflow, job])
            session.commit()

    @staticmethod
    def _get_job(session) -> Job:
        return session.query(Job).filter_by(name='test-job').first()

    @staticmethod
    def _get_event() -> Event:
        return Event(app_name='test-job', event_type=EventType.MODIFIED, obj_type=ObjectType.FLAPP, obj_dict={})

    @patch('fedlearner_webconsole.mmgr.service.ModelService.create_model_from_model_job')
    def test_model_update(self, mock_create_model: MagicMock):
        event = self._get_event()
        with db.session_scope() as session:
            job = self._get_job(session)
            job.state = JobState.STOPPED
            session.commit()
        ModelEventListener().update(event)
        # not called since job state is stopped
        mock_create_model.assert_not_called()
        with db.session_scope() as session:
            job = self._get_job(session)
            job.state = JobState.COMPLETED
            session.commit()
        ModelEventListener().update(event)
        # not called since model job is not found
        mock_create_model.assert_not_called()

        with db.session_scope() as session:
            model_job = ModelJob(id=1, job_name=job.name, job_id=job.id, model_job_type=ModelJobType.TRAINING)
            model = Model(id=1, model_job_id=1)
            session.add_all([model_job, model])
            session.commit()
        ModelEventListener().update(event)
        # create model
        mock_create_model.assert_called()
        with db.session_scope() as session:
            model_job = session.query(ModelJob).get(1)
            self.assertEqual(model_job.model_id, 1)
        mock_create_model.reset_mock()

        with db.session_scope() as session:
            session.add(Model(name=job.name, job_id=job.id))
            session.commit()
        ModelEventListener().update(event)
        # not called due to model is already created
        mock_create_model.assert_not_called()


if __name__ == '__main__':
    unittest.main()
