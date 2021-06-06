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



from google.protobuf.json_format import ParseDict

from fedlearner_webconsole.db import db
from fedlearner_webconsole.auth.models import User
from fedlearner_webconsole.proto import project_pb2
from fedlearner_webconsole.project.models import Project


def init_db(port, domain_name):
    db.create_all()
    user = User(username='ada')
    user.set_password('ada')
    db.session.add(user)
    config = {
        'name': 'test',
        'participants': [
            {
                'name': f'{domain_name}',
                'url': f'127.0.0.1:{port}',
                'domain_name': f'{domain_name}',
                'grpc_spec': {
                    'authority': f'{domain_name[:-4]}-client-auth.com'
                }
            }
        ],
        'variables': [
            {
                'name': 'namespace',
                'value': 'default'
            },
            {
                'name': 'storage_root_dir',
                'value': '/data'
            },
            {
                'name': 'EGRESS_URL',
                'value': f'127.0.0.1:{port}'
            }

        ]
    }
    project = Project(name='test',
                      config=ParseDict(config,
                                       project_pb2.Project()).SerializeToString())
    db.session.add(project)
    db.session.commit()
