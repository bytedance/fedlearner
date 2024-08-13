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
from testing.common import NoWebServerTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto.two_pc_pb2 import TransactionData, StopTrustedJobData
from fedlearner_webconsole.tee.models import TrustedJob, TrustedJobStatus
from fedlearner_webconsole.job.models import Job, JobState, JobType
from fedlearner_webconsole.two_pc.trusted_job_stopper import TrustedJobStopper


class TrustedJobStopperTest(NoWebServerTestCase):

    def setUp(self) -> None:
        super().setUp()
        with db.session_scope() as session:
            trusted_job1 = TrustedJob(id=1, uuid='uuid1', job_id=1)
            job1 = Job(id=1,
                       name='job-name1',
                       job_type=JobType.CUSTOMIZED,
                       project_id=1,
                       workflow_id=0,
                       state=JobState.STARTED)
            trusted_job2 = TrustedJob(id=2, uuid='uuid2', job_id=2)
            job2 = Job(id=2,
                       name='job-name2',
                       job_type=JobType.CUSTOMIZED,
                       project_id=1,
                       workflow_id=0,
                       state=JobState.WAITING)
            session.add_all([trusted_job1, trusted_job2, job1, job2])
            session.commit()

    @staticmethod
    def get_transaction_data(uuid: str):
        return TransactionData(stop_trusted_job_data=StopTrustedJobData(uuid=uuid))

    def test_prepare(self):
        with db.session_scope() as session:
            # successful
            data = self.get_transaction_data(uuid='uuid1')
            stopper = TrustedJobStopper(session, '13', data)
            flag, msg = stopper.prepare()
            self.assertTrue(flag)
            # fail due to trusted job not found
            data = self.get_transaction_data(uuid='not-exist')
            stopper = TrustedJobStopper(session, '13', data)
            flag, msg = stopper.prepare()
            self.assertFalse(flag)
            # fail due to status not valid
            data = self.get_transaction_data(uuid='uuid2')
            stopper = TrustedJobStopper(session, '13', data)
            flag, msg = stopper.prepare()
            self.assertFalse(flag)

    def test_commit(self):
        with db.session_scope() as session:
            # successful
            data = self.get_transaction_data(uuid='uuid1')
            stopper = TrustedJobStopper(session, '13', data)
            stopper.commit()
            # status not valid
            data = self.get_transaction_data(uuid='uuid2')
            stopper = TrustedJobStopper(session, '13', data)
            stopper.commit()
            session.commit()
        with db.session_scope() as session:
            trusted_job1 = session.query(TrustedJob).get(1)
            self.assertEqual(trusted_job1.status, TrustedJobStatus.STOPPED)
            trusted_job2 = session.query(TrustedJob).get(2)
            self.assertEqual(trusted_job2.status, TrustedJobStatus.PENDING)


if __name__ == '__main__':
    unittest.main()
