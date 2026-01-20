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

from http import HTTPStatus

from unittest.mock import patch, MagicMock

from fedlearner_webconsole.utils.pp_time import sleep
from fedlearner_webconsole.db import db
from fedlearner_webconsole.participant.models import Participant, ProjectParticipant, ParticipantType
from testing.common import BaseTestCase


class ParticipantsApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.fake_certs = {'test/test.certs': 'key'}
        self.default_participant = Participant(name='test-particitant-name',
                                               domain_name='fl-test.com',
                                               host='1.1.1.1',
                                               port=32443,
                                               comment='test comment')
        self.default_participant.set_extra_info({'is_manual_configured': False})

        self.participant_manually = Participant(name='test-manual-participant',
                                                domain_name='fl-test-manual.com',
                                                host='1.1.1.2',
                                                port=443)
        self.participant_manually.set_extra_info({
            'is_manual_configured': True,
        })

        with db.session_scope() as session:
            session.add(self.default_participant)
            session.flush()
            sleep(1)
            session.add(self.participant_manually)
            session.commit()

    @patch('fedlearner_webconsole.participant.apis.get_host_and_port')
    def test_post_participant_without_certificate(self, mock_get_host_and_port):
        name = 'test-post-participant'
        domain_name = 'fl-post-test.com'
        comment = 'test post participant'
        host = '120.0.0.20'
        port = 20
        mock_get_host_and_port.return_value = (host, port)

        create_response = self.post_helper('/api/v2/participants',
                                           data={
                                               'name': name,
                                               'domain_name': domain_name,
                                               'is_manual_configured': False,
                                               'comment': comment
                                           })
        self.assertEqual(HTTPStatus.CREATED, create_response.status_code)
        participant = self.get_response_data(create_response)
        # yapf: disable
        self.assertPartiallyEqual(participant, {
            'id': 3,
            'comment': comment,
            'domain_name': 'fl-post-test.com',
            'pure_domain_name': 'post-test',
            'host': host,
            'name': name,
            'port': port,
            'extra': {
                'is_manual_configured': False,
            },
            'type': 'PLATFORM',
            'last_connected_at': 0,
            'num_project': 0,
        }, ignore_fields=['created_at', 'updated_at'])
        # yapf: enable

    @patch('fedlearner_webconsole.participant.apis.create_or_update_participant_in_k8s')
    def test_post_participant_manually(self, mock_create_or_update_participant_in_k8s):
        name = 'test-post-participant'
        domain_name = 'fl-post-test.com'
        comment = 'test post participant'
        host = '120.0.0.20'
        port = 20

        create_response = self.post_helper('/api/v2/participants',
                                           data={
                                               'name': name,
                                               'domain_name': domain_name,
                                               'comment': comment,
                                               'is_manual_configured': True,
                                               'host': host,
                                               'port': port,
                                           })

        self.assertEqual(HTTPStatus.CREATED, create_response.status_code)
        participant = self.get_response_data(create_response)
        # yapf: disable
        self.assertPartiallyEqual(participant, {
            'id': 3,
            'comment': comment,
            'domain_name': 'fl-post-test.com',
            'pure_domain_name': 'post-test',
            'host': host,
            'name': name,
            'port': port,
            'extra': {
                'is_manual_configured': True,
            },
            'type': 'PLATFORM',
            'last_connected_at': 0,
            'num_project': 0,
        }, ignore_fields=['created_at', 'updated_at'])
        # yapf: enable
        mock_create_or_update_participant_in_k8s.assert_called_once_with(domain_name='fl-post-test.com',
                                                                         host='120.0.0.20',
                                                                         namespace='default',
                                                                         port=20)

    def test_post_light_client_participant(self):
        resp = self.post_helper('/api/v2/participants',
                                data={
                                    'name': 'light-client',
                                    'domain_name': 'fl-light-client.com',
                                    'type': 'LIGHT_CLIENT',
                                    'is_manual_configured': False,
                                })
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        with db.session_scope() as session:
            participant = session.query(Participant).filter_by(name='light-client').first()
            self.assertEqual(participant.domain_name, 'fl-light-client.com')
            self.assertEqual(participant.type, ParticipantType.LIGHT_CLIENT)
        self.assertResponseDataEqual(resp, {
            'name': 'light-client',
            'domain_name': 'fl-light-client.com',
            'pure_domain_name': 'light-client',
            'host': '',
            'port': 0,
            'type': 'LIGHT_CLIENT',
            'comment': '',
            'extra': {
                'is_manual_configured': False
            },
            'last_connected_at': 0,
            'num_project': 0,
        },
                                     ignore_fields=['id', 'created_at', 'updated_at'])

    @patch('fedlearner_webconsole.participant.apis.get_host_and_port')
    def test_post_conflict_domain_name_participant(self, mock_get_host_and_port):
        mock_get_host_and_port.return_value = ('1.1.1.1', 1)
        create_response = self.post_helper('/api/v2/participants',
                                           data={
                                               'name': 'test-post-conflict-participant',
                                               'domain_name': 'fl-test.com',
                                               'is_manual_configured': False,
                                           })

        self.assertEqual(HTTPStatus.CONFLICT, create_response.status_code)

    def test_list_participant(self):
        list_response = self.get_helper('/api/v2/participants')
        participants = self.get_response_data(list_response)
        self.assertPartiallyEqual(
            participants,
            [{
                'comment': '',
                'domain_name': 'fl-test-manual.com',
                'pure_domain_name': 'test-manual',
                'host': '1.1.1.2',
                'id': 2,
                'name': 'test-manual-participant',
                'port': 443,
                'extra': {
                    'is_manual_configured': True,
                },
                'last_connected_at': 0,
                'num_project': 0,
                'type': 'PLATFORM',
            }, {
                'comment': 'test comment',
                'domain_name': 'fl-test.com',
                'pure_domain_name': 'test',
                'host': '1.1.1.1',
                'id': 1,
                'name': 'test-particitant-name',
                'port': 32443,
                'extra': {
                    'is_manual_configured': False,
                },
                'last_connected_at': 0,
                'num_project': 0,
                'type': 'PLATFORM',
            }],
            ignore_fields=['created_at', 'updated_at'],
        )

    @patch('fedlearner_webconsole.participant.apis.get_host_and_port')
    def test_update_participant(self, mock_get_host_and_port):
        name = 'test-update-participant'
        domain_name = 'fl-update-test.com'
        comment = 'test update participant'
        ip = '120.0.0.30'
        port = 30
        mock_get_host_and_port.return_value = (ip, port)

        update_response = self.patch_helper('/api/v2/participants/1',
                                            data={
                                                'name': name,
                                                'domain_name': domain_name,
                                                'comment': comment,
                                            })
        participant = self.get_response_data(update_response)

        self.assertEqual(update_response.status_code, HTTPStatus.OK)
        # yapf: disable
        self.assertPartiallyEqual(participant, {
            'comment': comment,
            'domain_name': 'fl-update-test.com',
            'pure_domain_name': 'update-test',
            'host': ip,
            'id': 1,
            'name': name,
            'port': port,
            'extra': {
                'is_manual_configured': False,
            },
            'last_connected_at': 0,
            'num_project': 0,
            'type': 'PLATFORM'
        }, ignore_fields=['created_at', 'updated_at'])
        # yapf: enable

    def test_update_participant_conflict_domain_name(self):
        update_response = self.patch_helper('/api/v2/participants/1', data={
            'domain_name': 'fl-test-manual.com',
        })
        self.assertEqual(update_response.status_code, HTTPStatus.CONFLICT)

    @patch('fedlearner_webconsole.participant.apis.create_or_update_participant_in_k8s')
    def test_update_host_and_port(self, mock_create_or_update_participant_in_k8s):
        update_response = self.patch_helper('/api/v2/participants/2', data={
            'host': '1.112.212.20',
            'port': 9999,
        })

        self.assertEqual(update_response.status_code, HTTPStatus.OK)
        self.assertEqual(self.get_response_data(update_response)['port'], 9999)

        mock_create_or_update_participant_in_k8s.assert_called_once()

    @patch('fedlearner_webconsole.participant.apis.create_or_update_participant_in_k8s')
    def test_update_only_name(self, mock_create_or_update_participant_in_k8s):
        update_response = self.patch_helper('/api/v2/participants/2', data={
            'name': 'fl-test-only-name',
        })

        self.assertEqual(update_response.status_code, HTTPStatus.OK)
        self.assertEqual(self.get_response_data(update_response)['name'], 'fl-test-only-name')

        mock_create_or_update_participant_in_k8s.assert_not_called()

    def test_update_light_client(self):
        with db.session_scope() as session:
            party = Participant(name='test-party', domain_name='fl-light-client.com', type=ParticipantType.LIGHT_CLIENT)
            session.add(party)
            session.commit()
        resp = self.patch_helper(f'/api/v2/participants/{party.id}',
                                 data={
                                     'name': 'test-name',
                                     'domain_name': 'fl-1.com',
                                     'comment': 'comment'
                                 })
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        with db.session_scope() as session:
            party = session.query(Participant).get(party.id)
            self.assertEqual(party.name, 'test-name')
            self.assertEqual(party.domain_name, 'fl-1.com')
            self.assertEqual(party.comment, 'comment')

    def test_get_participant(self):
        with db.session_scope() as session:
            relationship = ProjectParticipant(project_id=1, participant_id=1)
            session.add(relationship)
            session.commit()
        get_response = self.get_helper('/api/v2/participants/1')
        participant = self.get_response_data(get_response)
        # yapf: disable
        self.assertPartiallyEqual(participant, {
            'comment': 'test comment',
            'domain_name': 'fl-test.com',
            'pure_domain_name': 'test',
            'host': '1.1.1.1',
            'id': 1,
            'name': 'test-particitant-name',
            'port': 32443,
            'extra': {
                'is_manual_configured': False,
            },
            'type': 'PLATFORM',
            'last_connected_at': 0,
            'num_project': 0,
        }, ignore_fields=['created_at', 'updated_at'])
        # yapf: enable

    def test_delete_participant(self):
        self.signin_as_admin()
        with db.session_scope() as session:
            relationship = ProjectParticipant(project_id=1, participant_id=2)
            session.add(relationship)
            session.commit()
        # test delete participant which does not exist
        delete_response = self.delete_helper('/api/v2/participants/3')
        self.assertEqual(delete_response.status_code, HTTPStatus.NOT_FOUND)

        # test delete participant which has related projects
        delete_response = self.delete_helper('/api/v2/participants/2')
        self.assertEqual(delete_response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

        # test delete participant successfully
        delete_response = self.delete_helper('/api/v2/participants/1')
        self.assertEqual(delete_response.status_code, HTTPStatus.NO_CONTENT)


class ParticipantCandidatesApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.signin_as_admin()

    def test_get_valid_candidates(self):
        get_response = self.get_helper('/api/v2/participant_candidates')
        data = self.get_response_data(get_response)
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertEqual(data, [{'domain_name': 'fl-aaa.com'}, {'domain_name': 'fl-ccc.com'}])


class ParticipantFlagsApiTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        with db.session_scope() as session:
            session.add(Participant(id=1, name='party', domain_name='fl-test.com'))
            session.commit()

    @patch('fedlearner_webconsole.participant.apis.SystemServiceClient')
    def test_get_peer_flags(self, mock_client: MagicMock):
        instance = mock_client.from_participant.return_value
        instance.list_flags.return_value = {'key': 'value'}
        # fail due to participant not found
        resp = self.get_helper('/api/v2/participants/2/flags')
        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)
        resp = self.get_helper('/api/v2/participants/1/flags')
        mock_client.from_participant.assert_called_with(domain_name='fl-test.com')
        self.assertResponseDataEqual(resp, {'key': 'value'})


if __name__ == '__main__':
    unittest.main()
