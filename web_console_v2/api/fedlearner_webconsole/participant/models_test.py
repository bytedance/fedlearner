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

from fedlearner_webconsole.participant.models import Participant, ParticipantType
from fedlearner_webconsole.proto import participant_pb2
from testing.no_web_server_test_case import NoWebServerTestCase


class ParticipantTest(NoWebServerTestCase):

    def test_to_proto(self):
        created_at = datetime(2022, 5, 1, 10, 10, tzinfo=timezone.utc)
        participant = Participant(id=123,
                                  name='testp',
                                  domain_name='fl-test.com',
                                  host='test.fl.com',
                                  port=32443,
                                  type=ParticipantType.PLATFORM,
                                  comment='c',
                                  created_at=created_at,
                                  updated_at=created_at,
                                  extra='{"is_manual_configured":true}')
        self.assertEqual(
            participant.to_proto(),
            participant_pb2.Participant(id=123,
                                        name='testp',
                                        domain_name='fl-test.com',
                                        pure_domain_name='test',
                                        host='test.fl.com',
                                        port=32443,
                                        type='PLATFORM',
                                        comment='c',
                                        created_at=int(created_at.timestamp()),
                                        updated_at=int(created_at.timestamp()),
                                        extra=participant_pb2.ParticipantExtra(is_manual_configured=True)))


if __name__ == '__main__':
    unittest.main()
