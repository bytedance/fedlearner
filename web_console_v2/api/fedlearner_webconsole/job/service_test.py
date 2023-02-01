# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

from fedlearner_webconsole.proto.job_pb2 import PodPb

from fedlearner_webconsole.proto import workflow_definition_pb2
from fedlearner_webconsole.db import db
from fedlearner_webconsole.utils.pp_datetime import to_timestamp
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.job.models import Job, JobDependency, JobType, JobState
from fedlearner_webconsole.job.service import JobService
from fedlearner_webconsole.k8s.models import FlApp
from testing.no_web_server_test_case import NoWebServerTestCase


class JobServiceTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        workflow_0 = Workflow(id=0, name='test-workflow-0', project_id=0)
        workflow_1 = Workflow(id=1, name='test-workflow-1', project_id=0)

        config = workflow_definition_pb2.JobDefinition(name='test-job').SerializeToString()
        job_0 = Job(id=0,
                    name='raw_data_0',
                    job_type=JobType.RAW_DATA,
                    state=JobState.STARTED,
                    workflow_id=0,
                    project_id=0,
                    config=config)
        job_1 = Job(id=1,
                    name='raw_data_1',
                    job_type=JobType.RAW_DATA,
                    state=JobState.COMPLETED,
                    workflow_id=0,
                    project_id=0,
                    config=config)
        job_2 = Job(id=2,
                    name='data_join_0',
                    job_type=JobType.DATA_JOIN,
                    state=JobState.WAITING,
                    workflow_id=0,
                    project_id=0,
                    config=config)
        job_3 = Job(id=3,
                    name='data_join_1',
                    job_type=JobType.DATA_JOIN,
                    state=JobState.COMPLETED,
                    workflow_id=1,
                    project_id=0,
                    config=config)
        job_4 = Job(id=4,
                    name='train_job_0',
                    job_type=JobType.NN_MODEL_TRANINING,
                    state=JobState.WAITING,
                    workflow_id=1,
                    project_id=0,
                    config=config)

        job_dep_0 = JobDependency(src_job_id=job_0.id, dst_job_id=job_2.id, dep_index=0)
        job_dep_1 = JobDependency(src_job_id=job_1.id, dst_job_id=job_2.id, dep_index=1)
        job_dep_2 = JobDependency(src_job_id=job_3.id, dst_job_id=job_4.id, dep_index=0)

        with db.session_scope() as session:
            session.add_all([workflow_0, workflow_1])
            session.add_all([job_0, job_1, job_2, job_3, job_4])
            session.add_all([job_dep_0, job_dep_1, job_dep_2])
            session.commit()

    def test_is_ready(self):
        with db.session_scope() as session:
            job_0 = session.query(Job).get(0)
            job_2 = session.query(Job).get(2)
            job_4 = session.query(Job).get(4)
            job_service = JobService(session)
            self.assertTrue(job_service.is_ready(job_0))
            self.assertFalse(job_service.is_ready(job_2))
            self.assertTrue(job_service.is_ready(job_4))

    @patch('fedlearner_webconsole.job.models.Job.get_k8s_app')
    def test_update_running_state(self, mock_crd):
        with db.session_scope() as session:
            job_0 = session.query(Job).get(0)
            job_2 = session.query(Job).get(2)
            job_service = JobService(session)
            job_service.update_running_state(job_0.name)
            self.assertEqual(job_0.state, JobState.COMPLETED)
            self.assertTrue(job_service.is_ready(job_2))
            job_0.state = JobState.STARTED
            mock_crd.return_value = MagicMock(is_completed=False, is_failed=True, error_message=None)
            job_service.update_running_state(job_0.name)
            self.assertEqual(job_0.state, JobState.FAILED)
            session.commit()

    def test_get_pods(self):
        creation_timestamp = datetime.utcnow()
        fake_pods = \
            {
                'pods': {
                    'items': [
                        {
                            'status': {
                                'phase': 'Running',
                                'pod_ip': '172.0.0.1',
                            },
                            'metadata': {
                                'labels': {'fl-replica-type': 'master'},
                                'name': 'name1',
                                'creation_timestamp': creation_timestamp,
                            },
                            'spec': {
                                'containers': [
                                    {
                                        'name': 'fake_pod',
                                        'resources': {
                                            'limits': {
                                                'cpu': '4000m',
                                                'memory': '4Gi',
                                            },
                                            'requests': {
                                                'cpu': '4000m',
                                                'memory': '4Gi',
                                            }
                                        }
                                    }
                                ]
                            }
                        },
                        {
                            'status': {
                                'phase': 'Pending',
                                'pod_ip': '172.0.0.1',
                            },
                            'metadata': {
                                'labels': {'fl-replica-type': 'master'},
                                'name': 'name3',
                                'creation_timestamp': creation_timestamp,
                            },
                            'spec': {
                                'containers': [
                                    {
                                        'name': 'fake_pod',
                                        'resources': {
                                            'limits': {
                                                'cpu': '4000m',
                                                'memory': '4Gi',
                                            },
                                            'requests': {
                                                'cpu': '4000m',
                                                'memory': '4Gi',
                                            }
                                        }
                                    }
                                ]
                            }
                        },
                        {
                            'status': {
                                'phase': 'Succeeded',
                                'pod_ip': '172.0.0.2',
                            },
                            'metadata': {
                                'labels': {'fl-replica-type': 'worker'},
                                'name': 'name2',
                                'creation_timestamp': creation_timestamp,
                            },
                            'spec': {
                                'containers': [
                                    {
                                        'name': 'fake_pod',
                                        'resources': {
                                            'limits': {
                                                'cpu': '4000m',
                                                'memory': '4Gi',
                                            },
                                            'requests': {
                                                'cpu': '4000m',
                                                'memory': '4Gi',
                                            }
                                        }
                                    }
                                ]
                            }
                        }, {
                            'status': {
                                'phase': 'Running',
                                'pod_ip': '172.0.0.2',
                            },
                            'metadata': {
                                'labels': {'fl-replica-type': 'worker'},
                                'name': 'running_one',
                                'creation_timestamp': creation_timestamp,
                            },
                            'spec': {
                                'containers': [
                                    {
                                        'name': 'fake_pod',
                                        'resources': {
                                            'limits': {
                                                'cpu': '4000m',
                                                'memory': '4Gi',
                                            },
                                            'requests': {
                                                'cpu': '4000m',
                                                'memory': '4Gi',
                                            }
                                        }
                                    }
                                ]
                            }
                        },
                    ]
                },
                'app': {
                    'status': {
                        'appState': 'FLStateComplete',
                        'flReplicaStatus': {
                            'Master': {
                                'active': {
                                },
                                'failed': {},
                                'succeeded': {
                                    'name1': {}
                                }
                            },
                            'Worker': {
                                'active': {
                                    'running_one': {}
                                },
                                'failed': {},
                                'succeeded': {
                                    'name2': {}
                                }
                            }
                        }
                    }
                }
            }

        expected_pods = [
            PodPb(
                name='name1',
                pod_type='MASTER',
                state='SUCCEEDED_AND_FREED',
                pod_ip='172.0.0.1',
                message='',
                creation_timestamp=to_timestamp(creation_timestamp),
            ),
            PodPb(creation_timestamp=to_timestamp(creation_timestamp),
                  message='',
                  name='name3',
                  pod_ip='172.0.0.1',
                  pod_type='MASTER',
                  state='PENDING'),
            PodPb(
                name='name2',
                pod_type='WORKER',
                state='SUCCEEDED',
                pod_ip='172.0.0.2',
                message='',
                creation_timestamp=to_timestamp(creation_timestamp),
            ),
            PodPb(
                name='running_one',
                pod_type='WORKER',
                state='RUNNING',
                pod_ip='172.0.0.2',
                message='',
                creation_timestamp=to_timestamp(creation_timestamp),
            )
        ]
        fake_job = MagicMock()
        fake_job.is_sparkapp = MagicMock(return_value=False)
        fake_job.get_k8s_app = MagicMock(return_value=FlApp.from_json(fake_pods))
        pods = JobService.get_pods(fake_job)
        self.assertEqual(pods, expected_pods)

    def test_get_job_yaml(self):
        fake_job = MagicMock()
        fake_job.state = JobState.STOPPED
        fake_job.snapshot = 'test'
        self.assertEqual(JobService.get_job_yaml(fake_job), 'test')
        fake_job.state = JobState.STARTED
        test_time = datetime.now()
        fake_job.build_crd_service = MagicMock(return_value=MagicMock(get_k8s_app_cache=MagicMock(
            return_value={'a': test_time})))
        self.assertEqual(JobService.get_job_yaml(fake_job), f'{{"a": "{test_time.isoformat()}"}}')


if __name__ == '__main__':
    unittest.main()
