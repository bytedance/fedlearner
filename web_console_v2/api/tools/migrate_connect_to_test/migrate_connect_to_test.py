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

import logging
from sqlalchemy.orm import Session
from envs import Envs
from fedlearner_webconsole.db import db
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.participant.k8s_utils import create_or_update_participant_in_k8s
from fedlearner_webconsole.k8s.k8s_client import k8s_client


def _migrate_participant(session: Session):
    # defensive delete the dirty data.
    deleted_count = session.query(Participant).filter_by(domain_name='fl-bytedance-test.com').delete()
    logging.info(f'Deleting {deleted_count} rows which has `domain_name`: `fl-bytedance-test.com`')

    participant = session.query(Participant).filter_by(domain_name='fl-bytedance.com').first()
    if participant is None:
        error_msg = 'Failed to find participant whose `domain_name` is `bytedance`'
        logging.error(error_msg)
        raise RuntimeError(error_msg)

    logging.info('Updating domain_name from `fl-bytedance.com` to `fl-bytedance-test.com`')
    participant.domain_name = 'fl-bytedance-test.com'
    participant.host = 'bytedance-test.fedlearner.net'
    participant.port = 443


def migrate_connect_to_test():
    logging.basicConfig(level=logging.DEBUG)
    with db.session_scope() as session:
        _migrate_participant(session)

        logging.info('Updating ingress and service resources in kubernetes...')
        create_or_update_participant_in_k8s('fl-bytedance-test.com',
                                            'bytedance-test.fedlearner.net',
                                            443,
                                            namespace=Envs.K8S_NAMESPACE)
        k8s_client.delete_service(name='fl-bytedance')
        k8s_client.delete_ingress(name='fl-bytedance-client-auth')
        session.commit()
    logging.info('Congratulations! Migration is done.')


if __name__ == '__main__':
    migrate_connect_to_test()
