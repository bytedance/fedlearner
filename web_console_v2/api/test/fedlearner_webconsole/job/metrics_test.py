# Copyright 2021 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
import time
import unittest
from http import HTTPStatus

from testing.common import BaseTestCase, TestAppProcess

from fedlearner_webconsole.proto import workflow_definition_pb2
from fedlearner_webconsole.db import db
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.job.models import Job, JobType
from fedlearner_webconsole.job.metrics import JobMetricsBuilder


class JobMetricsBuilderTest(BaseTestCase):
    class Config(BaseTestCase.Config):
        ES_HOST = ''
        ES_PORT = 80

    class FollowerConfig(Config):
        GRPC_LISTEN_PORT = 4990

    def test_data_join_metrics(self):
        job = Job(
            name='multi-indices-test27',
            job_type=JobType.DATA_JOIN)
        import json
        print(json.dumps(JobMetricsBuilder(job).plot_metrics()))

    def test_nn_metrics(self):
        job = Job(
            name='automl-2782410011',
            job_type=JobType.NN_MODEL_TRAINING)
        print(JobMetricsBuilder(job).plot_metrics())

    def test_peer_metrics(self):
        proc = TestAppProcess(
            JobMetricsBuilderTest,
            'follower_test_peer_metrics',
            JobMetricsBuilderTest.FollowerConfig)
        proc.start()
        self.leader_test_peer_metrics()
        proc.terminate()

    def leader_test_peer_metrics(self):
        self.setup_project(
            'leader',
            JobMetricsBuilderTest.FollowerConfig.GRPC_LISTEN_PORT)
        workflow = Workflow(
            name='test-workflow',
            project_id=1)
        db.session.add(workflow)
        db.session.commit()

        while True:
            resp = self.get_helper(
                '/api/v2/workflows/1/peer_workflows'
                '/0/jobs/test-job/metrics')
            if resp.status_code == HTTPStatus.OK:
                break
            time.sleep(1)
    
    def follower_test_peer_metrics(self):
        self.setup_project(
            'follower',
            JobMetricsBuilderTest.Config.GRPC_LISTEN_PORT)
        workflow = Workflow(
            name='test-workflow',
            project_id=1,
            metric_is_public=True)
        workflow.set_job_ids([1])
        db.session.add(workflow)
        job = Job(
            name='automl-2782410011',
            job_type=JobType.NN_MODEL_TRAINING,
            workflow_id=1,
            project_id=1,
            config=workflow_definition_pb2.JobDefinition(
                name='test-job'
            ).SerializeToString())
        db.session.add(job)
        db.session.commit()

        while True:
            time.sleep(1)


if __name__ == '__main__':
    # no es in test env skip this test
    # unittest.main()
    pass
