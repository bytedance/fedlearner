# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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
from sqlalchemy import UniqueConstraint, func
from fedlearner_webconsole.db import db, default_table_args
from fedlearner_webconsole.proto.setting_pb2 import SettingPb


class Setting(db.Model):
    __tablename__ = 'settings_v2'
    __table_args__ = (UniqueConstraint('uniq_key',
                                       name='uniq_key'), default_table_args('this is webconsole settings table'))
    id = db.Column(db.Integer, primary_key=True, comment='id', autoincrement=True)
    uniq_key = db.Column(db.String(255), nullable=False, comment='uniq_key')
    value = db.Column(db.Text, comment='value')
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), comment='created at')
    updated_at = db.Column(db.DateTime(timezone=True),
                           onupdate=func.now(),
                           server_default=func.now(),
                           comment='updated at')

    def to_proto(self):
        return SettingPb(
            uniq_key=self.uniq_key,
            value=self.value,
        )
