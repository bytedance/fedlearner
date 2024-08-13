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
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from fedlearner_webconsole.k8s.models import Pod, PodState, ContainerState
from fedlearner_webconsole.proto.job_pb2 import CrdMetaData, JobPb, JobErrorMessage
from fedlearner_webconsole.proto.workflow_definition_pb2 import JobDefinition
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.job.models import Job, JobType, JobState
from fedlearner_webconsole.workflow.models import Workflow  # pylint: disable=unused-import
from testing.no_web_server_test_case import NoWebServerTestCase


class ModelTest(NoWebServerTestCase):

    def test_is_training_job(self):
        job = Job()
        job.job_type = JobType.NN_MODEL_TRANINING
        self.assertTrue(job.is_training_job())
        job.job_type = JobType.TREE_MODEL_TRAINING
        self.assertTrue(job.is_training_job())
        job.job_type = JobType.TREE_MODEL_EVALUATION
        self.assertFalse(job.is_training_job())

    def test_get_job_crdmeta(self):
        job = Job()
        job.set_crd_meta(CrdMetaData(api_version='a/b'))
        self.assertEqual(job.get_crd_meta(), CrdMetaData(api_version='a/b'))

    def test_to_proto(self):
        created_at = datetime(2021, 10, 1, 8, 8, 8, tzinfo=timezone.utc)
        job = Job(id=1,
                  name='test',
                  job_type=JobType.DATA_JOIN,
                  state=JobState.COMPLETED,
                  workflow_id=1,
                  project_id=1,
                  created_at=created_at,
                  updated_at=created_at)
        expected_job_proto = JobPb(id=1,
                                   name='test',
                                   job_type=JobDefinition.DATA_JOIN,
                                   state='COMPLETED',
                                   workflow_id=1,
                                   project_id=1,
                                   crd_meta=CrdMetaData(),
                                   created_at=to_timestamp(created_at),
                                   updated_at=to_timestamp(created_at),
                                   error_message=JobErrorMessage())
        self.assertEqual(job.to_proto(), expected_job_proto)

    @patch('fedlearner_webconsole.job.models.Job.get_k8s_app')
    def test_get_error_message_with_pods(self, mock_get_k8s_app):
        fake_pods = [
            Pod(name='pod0',
                container_states=[ContainerState(state='terminated', message='00031003')],
                state=PodState.FAILED),
            Pod(name='pod1', container_states=[ContainerState(state='terminated')], state=PodState.FAILED),
            Pod(name='pod2',
                container_states=[ContainerState(state='terminated', message='Completed')],
                state=PodState.SUCCEEDED)
        ]
        mock_get_k8s_app.return_value = MagicMock(pods=fake_pods)
        job = Job(error_message='test', state=JobState.FAILED)
        self.assertEqual(job.get_error_message_with_pods(),
                         JobErrorMessage(app='test', pods={'pod0': 'terminated:00031003'}))
        job.error_message = None
        self.assertEqual(job.get_error_message_with_pods(), JobErrorMessage(pods={'pod0': 'terminated:00031003'}))
        mock_get_k8s_app.return_value = MagicMock(pods=[])
        self.assertEqual(job.get_error_message_with_pods(), JobErrorMessage())


if __name__ == '__main__':
    unittest.main()
