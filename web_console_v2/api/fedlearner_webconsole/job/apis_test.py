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
from unittest.mock import patch

from fedlearner_webconsole.db import db
from fedlearner_webconsole.job.models import Job, JobType, JobState
from fedlearner_webconsole.proto.job_pb2 import PodPb
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from testing.common import BaseTestCase


class JobApiTest(BaseTestCase):

    class Config(BaseTestCase.Config):
        START_SCHEDULER = False

    @patch('fedlearner_webconsole.job.apis.JobService.get_pods')
    def test_get_job(self, mock_get_pods):
        mock_get_pods.return_value = [PodPb(name='test', pod_type='a')]
        created_at = datetime(2021, 10, 1, 8, 8, 8, tzinfo=timezone.utc)
        with db.session_scope() as session:
            job = Job(id=1,
                      name='test',
                      job_type=JobType.DATA_JOIN,
                      state=JobState.COMPLETED,
                      workflow_id=1,
                      project_id=1,
                      created_at=created_at,
                      updated_at=created_at)
            session.add(job)
            session.commit()
        resp = self.get_helper('/api/v2/jobs/1')
        data = self.get_response_data(resp)
        self.assertEqual(
            data, {
                'complete_at': 0,
                'start_at': 0,
                'crd_kind': '',
                'crd_meta': {
                    'api_version': ''
                },
                'created_at': to_timestamp(created_at),
                'id': 1,
                'is_disabled': False,
                'job_type': 'DATA_JOIN',
                'name': 'test',
                'pods': [{
                    'creation_timestamp': 0,
                    'message': '',
                    'name': 'test',
                    'pod_ip': '',
                    'pod_type': 'a',
                    'state': ''
                }],
                'project_id': 1,
                'snapshot': '',
                'state': 'COMPLETED',
                'updated_at': to_timestamp(created_at),
                'workflow_id': 1,
                'error_message': {
                    'app': '',
                    'pods': {}
                }
            })


if __name__ == '__main__':
    unittest.main()
