# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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
import os
import logging
import secrets
from google.protobuf.json_format import ParseDict
from fedlearner_webconsole.app import create_app
from fedlearner_webconsole.db import db
from fedlearner_webconsole.auth.models import User
from fedlearner_webconsole.proto import project_pb2
from fedlearner_webconsole.project.models import Project
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

left_app = create_app('left_config.Left')
# export FLASK_APP=left_manage:left_app
# flask create-db
# export FLASK_ENV=development
# flask run --host=0.0.0.0 -p 5000

@left_app.cli.command('create-db')
def create_db():
    db.create_all()
    user = User(username='ada')
    user.set_password('ada')
    db.session.add(user)
    config = {
        'name': 'test',
        'domain_name': 'fl-leader.com',
        'participants': [
            {
                'name': 'party_follower',
                'url': '127.0.0.1:1991',
                'domain_name': 'fl-follower.com',
                'grpc_spec': {
                    'peer_url': '127.0.0.1:1991',
                }
            }
        ],
        'variables': [
            {
                'name': 'namespace',
                'value': 'leader'
            },
            {
                'name': 'basic_envs',
                'value': '{}'
            },
            {
                'name': 'storage_root_dir',
                'value': '/'
            }
        ]
    }
    project = Project(name='test',
                      config=ParseDict(config,
                                       project_pb2.Project()).SerializeToString())
    db.session.add(project)
    db.session.commit()
