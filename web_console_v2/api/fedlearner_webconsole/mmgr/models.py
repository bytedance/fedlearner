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

import json
from sqlalchemy.sql.schema import Index
from fedlearner_webconsole.db import db
from datetime import datetime


# TODO transaction
class Model(db.Model):
    __tablename__ = 'models_v2'
    # TODO use `default_table_args`
    __table_args__ = (Index('idx_id', 'id'), {
        'mysql_engine': 'innodb',
        'mysql_charset': 'utf8mb4',
    })

    id = db.Column(db.String(255), primary_key=True, unique=True, comment="id")
    parent_id = db.Column(db.String(255), comment="parent_id")
    type = db.Column(db.String(16), comment="type")  # MODEL/EVALUATION
    state = db.Column(db.String(16), comment="state")
    c_time = db.Column(db.Float(), comment="c_time")

    def __init__(self):
        self.c_time = datetime.now().timestamp()

    def commit(self):
        db.session.add(self)
        db.session.commit()


def query_model(model_id):
    return db.session.query(Model).filter_by(id=model_id).one_or_none()


def query_models():
    return db.session.query(Model).all()


def model_to_json(o):
    return {
        'model_id': o.id,
        'parent_id': o.parent_id,
        'type': o.type,
        'state': o.state,
        'detail_level': o.detail_level,
    } if o else None
