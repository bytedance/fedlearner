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
from datetime import datetime
from google.protobuf import text_format
from testing.no_web_server_test_case import NoWebServerTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.tee.models import TrustedJobGroup, TrustedJob, TrustedJobStatus, \
    GroupCreateStatus, TrustedJobType, TicketAuthStatus
from fedlearner_webconsole.proto.tee_pb2 import TrustedJobGroupPb, TrustedJobGroupRef, TrustedJobPb, TrustedJobRef, \
    Resource, ParticipantDataset, ParticipantDatasetList, TrustedNotification
from fedlearner_webconsole.proto.project_pb2 import ParticipantsInfo, ParticipantInfo
from fedlearner_webconsole.utils.base_model.review_ticket_model import TicketStatus
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.job.models import JobState, Job, JobType


class TrustedJobGroupTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            participant = Participant(id=1, name='p1', domain_name='test.domain.name')
            group = TrustedJobGroup(
                id=1,
                name='trusted job group test',
                latest_version=1,
                comment='This is comment for test.',
                project_id=2,
                created_at=datetime(2022, 6, 15, 0, 0, 0),
                updated_at=datetime(2022, 6, 15, 0, 0, 0),
                creator_username='admin',
                coordinator_id=1,
                analyzer_id=1,
                ticket_uuid='ticket-uuid',
                ticket_status=TicketStatus.APPROVED,
                status=GroupCreateStatus.SUCCEEDED,
                auth_status=AuthStatus.AUTHORIZED,
                unauth_participant_ids='1,2',
                algorithm_uuid='algorithm-uuid3',
                resource='cpu: 2\nmemory: 2\nreplicas: 1\n',
                dataset_id=4,
                participant_datasets="""
                    items {
                        participant_id: 1
                        uuid: "uuid1"
                        name: "name1"
                    }
                    items {
                        participant_id: 2
                        uuid: "uuid2"
                        name: "name2"
                    }
                """,
            )
            session.add_all([group, participant])
            session.commit()

    def test_to_proto(self):
        with db.session_scope() as session:
            group: TrustedJobGroup = session.query(TrustedJobGroup).get(1)
            pb = TrustedJobGroupPb(id=1,
                                   name='trusted job group test',
                                   latest_version=1,
                                   comment='This is comment for test.',
                                   project_id=2,
                                   created_at=1655251200,
                                   updated_at=1655251200,
                                   creator_username='admin',
                                   coordinator_id=1,
                                   analyzer_id=1,
                                   ticket_uuid='ticket-uuid',
                                   ticket_status='APPROVED',
                                   status='SUCCEEDED',
                                   auth_status='AUTHORIZED',
                                   latest_job_status='NEW',
                                   ticket_auth_status='AUTH_PENDING',
                                   unauth_participant_ids=[1, 2],
                                   algorithm_id=0,
                                   algorithm_uuid='algorithm-uuid3',
                                   resource=Resource(cpu=2, memory=2, replicas=1),
                                   dataset_id=4,
                                   participant_datasets=ParticipantDatasetList(items=[
                                       ParticipantDataset(participant_id=1, uuid='uuid1', name='name1'),
                                       ParticipantDataset(participant_id=2, uuid='uuid2', name='name2'),
                                   ]))
            self.assertEqual(pb, group.to_proto())

    def test_to_ref(self):
        with db.session_scope() as session:
            group: TrustedJobGroup = session.query(TrustedJobGroup).get(1)
            ref = TrustedJobGroupRef(
                id=1,
                name='trusted job group test',
                created_at=1655251200,
                is_creator=False,
                creator_id=1,
                ticket_status='APPROVED',
                status='SUCCEEDED',
                auth_status='AUTHORIZED',
                latest_job_status='NEW',
                ticket_auth_status='AUTH_PENDING',
                unauth_participant_ids=[1, 2],
                is_configured=True,
            )
            self.assertEqual(ref, group.to_ref())

    def test_get_latest_job_status(self):
        with db.session_scope() as session:
            group: TrustedJobGroup = session.query(TrustedJobGroup).get(1)
            job_status = group.get_latest_job_status()
            self.assertEqual(TrustedJobStatus.NEW, job_status)
        with db.session_scope() as session:
            new_job = TrustedJob(id=1, version=1, trusted_job_group_id=1, status=TrustedJobStatus.RUNNING)
            session.add(new_job)
            session.commit()
        with db.session_scope() as session:
            group: TrustedJobGroup = session.query(TrustedJobGroup).get(1)
            job_status = group.get_latest_job_status()
            self.assertEqual(TrustedJobStatus.RUNNING, job_status)

    def test_get_ticket_auth_status(self):
        with db.session_scope() as session:
            group: TrustedJobGroup = session.query(TrustedJobGroup).get(1)
            # AUTH_PENDING
            self.assertEqual(group.get_ticket_auth_status(), TicketAuthStatus.AUTH_PENDING)
            # AUTHORIZED
            group.unauth_participant_ids = None
            self.assertEqual(group.get_ticket_auth_status(), TicketAuthStatus.AUTHORIZED)
            # CREATED_FAILED
            group.status = GroupCreateStatus.FAILED
            self.assertEqual(group.get_ticket_auth_status(), TicketAuthStatus.CREATE_FAILED)
            # CREATED_PENDING
            group.status = GroupCreateStatus.PENDING
            self.assertEqual(group.get_ticket_auth_status(), TicketAuthStatus.CREATE_PENDING)
            # TICKET_DECLINED
            group.ticket_status = TicketStatus.DECLINED
            self.assertEqual(group.get_ticket_auth_status(), TicketAuthStatus.TICKET_DECLINED)
            # TICKET_PENDING
            group.ticket_status = TicketStatus.PENDING
            self.assertEqual(group.get_ticket_auth_status(), TicketAuthStatus.TICKET_PENDING)

    def test_get_resource(self):
        with db.session_scope() as session:
            group: TrustedJobGroup = session.query(TrustedJobGroup).get(1)
            self.assertEqual(Resource(cpu=2, memory=2, replicas=1), group.get_resource())
            group.resource = None
            self.assertIsNone(group.get_resource())

    def test_set_resource(self):
        with db.session_scope() as session:
            group: TrustedJobGroup = session.query(TrustedJobGroup).get(1)
            group.set_resource(Resource(cpu=4, memory=4, replicas=1))
            self.assertEqual('cpu: 4\nmemory: 4\nreplicas: 1\n', group.resource)
            group.set_resource()
            self.assertEqual('', group.resource)

    def test_get_participant_datasets(self):
        with db.session_scope() as session:
            group: TrustedJobGroup = session.query(TrustedJobGroup).get(1)
            expected = ParticipantDatasetList(items=[
                ParticipantDataset(participant_id=1, uuid='uuid1', name='name1'),
                ParticipantDataset(participant_id=2, uuid='uuid2', name='name2'),
            ])
            self.assertEqual(expected, group.get_participant_datasets())
            group.participant_datasets = None
            self.assertIsNone(group.get_participant_datasets())

    def test_set_participant_datasets(self):
        with db.session_scope() as session:
            group: TrustedJobGroup = session.query(TrustedJobGroup).get(1)
            pds = ParticipantDatasetList(items=[ParticipantDataset(participant_id=1, uuid='uuid1', name='name1')])
            group.set_participant_datasets(pds)
            self.assertEqual('items {\n  participant_id: 1\n  uuid: "uuid1"\n  name: "name1"\n}\n',
                             group.participant_datasets)

    def test_get_unauth_participant_ids(self):
        with db.session_scope() as session:
            group: TrustedJobGroup = session.query(TrustedJobGroup).get(1)
            group.unauth_participant_ids = '2'
            self.assertEqual([2], group.get_unauth_participant_ids())
            group.unauth_participant_ids = '2,3,4'
            self.assertEqual([2, 3, 4], group.get_unauth_participant_ids())
            group.unauth_participant_ids = None
            self.assertEqual([], group.get_unauth_participant_ids())

    def test_set_unauth_participant_ids(self):
        with db.session_scope() as session:
            group: TrustedJobGroup = session.query(TrustedJobGroup).get(1)
            group.set_unauth_participant_ids([])
            self.assertIsNone(group.unauth_participant_ids)
            group.set_unauth_participant_ids([1, 2, 3])
            self.assertEqual('1,2,3', group.unauth_participant_ids)

    def test_is_deletable(self):
        with db.session_scope() as session:
            trusted_job1 = TrustedJob(id=1, trusted_job_group_id=1, status=TrustedJobStatus.STOPPED)
            trusted_job2 = TrustedJob(id=2, trusted_job_group_id=1, status=TrustedJobStatus.FAILED)
            session.add_all([trusted_job1, trusted_job2])
            session.commit()
        with db.session_scope() as session:
            group: TrustedJobGroup = session.query(TrustedJobGroup).get(1)
            self.assertTrue(group.is_deletable())
        # not deletable
        with db.session_scope() as session:
            session.query(TrustedJob).filter_by(id=1).update({'status': TrustedJobStatus.RUNNING})
            session.commit()
        with db.session_scope() as session:
            group: TrustedJobGroup = session.query(TrustedJobGroup).get(1)
            self.assertFalse(group.is_deletable())

    def test_to_notification(self):
        with db.session_scope() as session:
            group: TrustedJobGroup = session.query(TrustedJobGroup).get(1)
            notif = group.to_notification()
            self.assertEqual(notif.type, TrustedNotification.TRUSTED_JOB_GROUP_CREATE)
            self.assertEqual(notif.id, 1)
            self.assertEqual(notif.name, 'trusted job group test')
            self.assertEqual(notif.created_at, 1655251200)
            self.assertEqual(notif.coordinator_id, 1)


class TrustedJobTest(NoWebServerTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            participant = Participant(id=1, name='p1', domain_name='test.domain.name')
            group = TrustedJobGroup(id=1, name='trusted job group name', project_id=2, coordinator_id=1)
            self.participants_info = ParticipantsInfo(participants_map={
                'self': ParticipantInfo(auth_status='AUTHORIZED'),
                'part1': ParticipantInfo(auth_status='WITHDRAW'),
            })
            trusted_job = TrustedJob(
                id=1,
                type=TrustedJobType.ANALYZE,
                name='V1',
                job_id=1,
                uuid='uuid test',
                version=1,
                comment='This is comment for test.',
                project_id=2,
                trusted_job_group_id=1,
                coordinator_id=1,
                auth_status=AuthStatus.AUTHORIZED,
                ticket_status=TicketStatus.APPROVED,
                participants_info=text_format.MessageToString(self.participants_info),
                created_at=datetime(2022, 6, 14, 0, 0, 0),
                updated_at=datetime(2022, 6, 14, 0, 0, 1),
                started_at=datetime(2022, 6, 15, 0, 0, 0),
                finished_at=datetime(2022, 6, 15, 0, 0, 1),
                status=TrustedJobStatus.PENDING,
                algorithm_uuid='algorithm-uuid3',
                resource='cpu: 2\nmemory: 2\nreplicas: 1\n',
                export_dataset_id=2,
            )
            job = Job(id=1,
                      name='trusted-job-1-1-1-uuid',
                      state=JobState.NEW,
                      job_type=JobType.CUSTOMIZED,
                      workflow_id=0,
                      project_id=1)
            session.add_all([group, trusted_job, job, participant])
            session.commit()

    def test_to_proto(self):
        with db.session_scope() as session:
            trusted_job: TrustedJob = session.query(TrustedJob).get(1)
            pb = TrustedJobPb(
                id=1,
                type='ANALYZE',
                name='V1',
                job_id=1,
                uuid='uuid test',
                version=1,
                comment='This is comment for test.',
                project_id=2,
                trusted_job_group_id=1,
                coordinator_id=1,
                ticket_status='APPROVED',
                auth_status='AUTHORIZED',
                participants_info=self.participants_info,
                ticket_auth_status='AUTH_PENDING',
                created_at=1655164800,
                updated_at=1655164801,
                started_at=1655251200,
                finished_at=1655251201,
                status='PENDING',
                algorithm_id=0,
                algorithm_uuid='algorithm-uuid3',
                resource=Resource(cpu=2, memory=2, replicas=1),
                export_dataset_id=2,
            )
            self.assertEqual(pb, trusted_job.to_proto())

    def test_to_ref(self):
        with db.session_scope() as session:
            trusted_job: TrustedJob = session.query(TrustedJob).get(1)
            ref = TrustedJobRef(
                id=1,
                type='ANALYZE',
                name='V1',
                coordinator_id=1,
                job_id=1,
                comment='This is comment for test.',
                started_at=1655251200,
                finished_at=1655251201,
                status='PENDING',
                participants_info=self.participants_info,
                ticket_auth_status='AUTH_PENDING',
            )
            self.assertEqual(ref, trusted_job.to_ref())

    def test_get_resource(self):
        with db.session_scope() as session:
            trusted_job: TrustedJob = session.query(TrustedJob).get(1)
            self.assertEqual(Resource(cpu=2, memory=2, replicas=1), trusted_job.get_resource())
            trusted_job.resource = None
            self.assertIsNone(trusted_job.get_resource())

    def test_set_resource(self):
        with db.session_scope() as session:
            trusted_job: TrustedJob = session.query(TrustedJob).get(1)
            trusted_job.set_resource(Resource(cpu=4, memory=4, replicas=1))
            self.assertEqual('cpu: 4\nmemory: 4\nreplicas: 1\n', trusted_job.resource)
            trusted_job.set_resource()
            self.assertEqual('', trusted_job.resource)

    def test_update_status(self):
        with db.session_scope() as session:
            trusted_job: TrustedJob = session.query(TrustedJob).get(1)
            job: Job = session.query(Job).get(1)
            # case 1
            trusted_job.update_status()
            self.assertEqual(TrustedJobStatus.PENDING, trusted_job.status)
            # case 2
            job.state = JobState.FAILED
            trusted_job.update_status()
            self.assertEqual(TrustedJobStatus.FAILED, trusted_job.status)
            # case 3
            trusted_job.status = TrustedJobStatus.RUNNING
            job.state = JobState.COMPLETED
            trusted_job.update_status()
            self.assertEqual(TrustedJobStatus.SUCCEEDED, trusted_job.status)
            # case 4
            job.state = JobState.WAITING
            trusted_job.update_status()
            self.assertEqual(TrustedJobStatus.SUCCEEDED, trusted_job.status)

    def test_get_status(self):
        with db.session_scope() as session:
            trusted_job: TrustedJob = session.query(TrustedJob).get(1)
            job: Job = session.query(Job).get(1)
            self.assertEqual(trusted_job.get_status(), TrustedJobStatus.PENDING)
            job.state = JobState.STARTED
            self.assertEqual(trusted_job.get_status(), TrustedJobStatus.RUNNING)
            job.state = JobState.FAILED
            self.assertEqual(trusted_job.get_status(), TrustedJobStatus.FAILED)
            job.state = JobState.WAITING
            self.assertEqual(trusted_job.get_status(), TrustedJobStatus.FAILED)

    def test_to_notification(self):
        with db.session_scope() as session:
            trusted_job: TrustedJob = session.query(TrustedJob).get(1)
            notif = trusted_job.to_notification()
            self.assertEqual(notif.type, TrustedNotification.TRUSTED_JOB_EXPORT)
            self.assertEqual(notif.id, 1)
            self.assertEqual(notif.name, 'trusted job group name-V1')
            self.assertEqual(notif.created_at, 1655164800)
            self.assertEqual(notif.coordinator_id, 1)

    def test_get_ticket_auth_status(self):
        with db.session_scope() as session:
            trusted_job: TrustedJob = session.query(TrustedJob).get(1)
            self.assertEqual(trusted_job.get_ticket_auth_status(), TicketAuthStatus.AUTH_PENDING)
            self.participants_info.participants_map['part1'].auth_status = 'AUTHORIZED'
            trusted_job.set_participants_info(self.participants_info)
            self.assertEqual(trusted_job.get_ticket_auth_status(), TicketAuthStatus.AUTHORIZED)
            trusted_job.status = TrustedJobStatus.CREATE_FAILED
            self.assertEqual(trusted_job.get_ticket_auth_status(), TicketAuthStatus.CREATE_FAILED)
            trusted_job.status = TrustedJobStatus.NEW
            self.assertEqual(trusted_job.get_ticket_auth_status(), TicketAuthStatus.CREATE_PENDING)
            trusted_job.ticket_status = TicketStatus.PENDING
            self.assertEqual(trusted_job.get_ticket_auth_status(), TicketAuthStatus.TICKET_PENDING)
            trusted_job.ticket_status = TicketStatus.DECLINED
            self.assertEqual(trusted_job.get_ticket_auth_status(), TicketAuthStatus.TICKET_DECLINED)


if __name__ == '__main__':
    unittest.main()
