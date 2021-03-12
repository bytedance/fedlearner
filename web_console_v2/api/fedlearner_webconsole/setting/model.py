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
# pylint: disable=raise-missing-from

from sqlalchemy import UniqueConstraint
from fedlearner_webconsole.db import db


class Setting(db.Model):
    __tablename__ = 'settings_v2'
    __table_args__ = (UniqueConstraint('key', name='uniq_key'), {
                        'comment': 'workflow_v2',
                        'mysql_engine': 'innodb',
                        'mysql_charset': 'utf8mb4',
                      })
    id = db.Column(db.Integer, primary_key=True, comment='id')
    key = db.Column(db.String(255), nullable=False, comment='key')
    value = db.Column(db.Text, comment='value')
