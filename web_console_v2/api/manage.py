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

from flask import url_for
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

from fedlearner_webconsole.app import create_app, db
from fedlearner_webconsole.auth.models import User

app = create_app('config.Config')
manager = Manager(app)
manager.add_command('db', MigrateCommand)

@manager.command
def create_db():
    db.create_all()
    user = User(username='ada')
    user.set_password('ada')
    db.session.add(user)
    db.session.commit()

@manager.command
def list_routes():
    import urllib
    output = []
    for rule in app.url_map.iter_rules():

        options = {}
        for arg in rule.arguments:
            options[arg] = '[{0}]'.format(arg)

        methods = ','.join(rule.methods)
        url = url_for(rule.endpoint, **options)
        line = urllib.parse.unquote(
            '{:50s} {:20s} {}'.format(rule.endpoint, methods, url))
        output.append(line)

    for line in sorted(output):
        print(line)

if __name__ == '__main__':
    manager.run()
