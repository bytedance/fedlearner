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
import logging
import enum
import json
from sqlalchemy.sql import func
from sqlalchemy.sql.schema import Index
from fedlearner_webconsole.db import db, to_dict_mixin
from fedlearner_webconsole.k8s_client import get_client
from fedlearner_webconsole.utils.k8s_client import CrdKind
from fedlearner_webconsole.proto.workflow_definition_pb2 import JobDefinition


class ModelModel(db.Model):
    __tablename__ = "model"
    __table_args__ = (Index("idx_modelID", "modelID"), {
        "mysql_engine": "innodb",
        "mysql_charset": "utf8mb4",
    })

    modelID = db.Column(db.String(255), primary_key=True, unique=True)
    state = db.Column(db.Text())

    def commit(self):
        db.session.add(self)
        db.session.commit()


def queryModel(modelID):
    objs = db.session.query(ModelModel).filter_by(modelID=modelID).all()
    return objs[0] if len(objs) == 1 else None
