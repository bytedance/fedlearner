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
from testing.common import BaseTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.job.models import JobState, Job, JobType
from fedlearner_webconsole.scheduler.scheduler import _get_waiting_jobs


class SchedulerFuncTestCase(BaseTestCase):
    def test_get_waiting_jobs(self):
        db.session.add(Job(name='testtes', state=JobState.STOPPED,
                           job_type=JobType.DATA_JOIN,
                           workflow_id=1,
                           project_id=1))
        db.session.add(Job(name='testtest', state=JobState.WAITING,
                           job_type=JobType.DATA_JOIN,
                           workflow_id=1,
                           project_id=1))
        db.session.commit()
        self.assertEqual(_get_waiting_jobs(), [2])


if __name__ == '__main__':
    unittest.main()
