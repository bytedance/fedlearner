# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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

import enum
from sqlalchemy.sql import func
from sqlalchemy.orm import remote, foreign
from sqlalchemy.sql.schema import Index, UniqueConstraint
from fedlearner_webconsole.utils.mixins import to_dict_mixin
from fedlearner_webconsole.db import db, default_table_args
from fedlearner_webconsole.job.models import Job


class ModelType(enum.Enum):
    NN_MODEL = 0
    NN_EVALUATION = 1
    TREE_MODEL = 2
    TREE_EVALUATION = 3


class ModelState(enum.Enum):
    NEW = -1  # before workflow has synced both party
    COMMITTING = 0  # (transient) after workflow has synced both party, before committing to k8s
    COMMITTED = 1  # after committed to k8s but before running
    WAITING = 2  # k8s is queueing the related job(s)
    RUNNING = 3  # k8s is running the related job(s)
    PAUSED = 4  # related workflow has been paused by end-user
    SUCCEEDED = 5
    FAILED = 6
    # DROPPING = 7  # (transient) removing model and its related resources
    DROPPED = 8  # model has been removed


# TODO transaction
@to_dict_mixin()
class Model(db.Model):
    __tablename__ = 'models_v2'
    __table_args__ = (Index('idx_job_name', 'job_name'),
                      UniqueConstraint('job_name', name='uniq_job_name'),
                      default_table_args('model'))

    id = db.Column(db.Integer, primary_key=True, comment='id')
    name = db.Column(db.String(255),
                     comment='name')  # can be modified by end-user
    version = db.Column(db.Integer, default=0, comment='version')
    type = db.Column(db.Integer, comment='type')
    state = db.Column(db.Integer, comment='state')
    job_name = db.Column(db.String(255), comment='job_name')
    parent_id = db.Column(db.Integer, comment='parent_id')
    params = db.Column(db.Text(), comment='params')
    metrics = db.Column(db.Text(), comment='metrics')
    created_at = db.Column(db.DateTime(timezone=True),
                           comment='created_at',
                           server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True),
                           comment='updated_at',
                           server_default=func.now(),
                           onupdate=func.now())
    deleted_at = db.Column(db.DateTime(timezone=True), comment='deleted_at')

    group_id = db.Column(db.Integer, default=0, comment='group_id')
    # TODO https://code.byted.org/data/fedlearner_web_console_v2/issues/289
    extra = db.Column(db.Text(), comment='extra')  # json string

    parent = db.relationship('Model',
                             primaryjoin=remote(id) == foreign(parent_id),
                             backref='children')
    job = db.relationship('Job', primaryjoin=Job.name == foreign(job_name))

    def get_eval_model(self):
        return [
            child for child in self.children if child.type in
            [ModelType.NN_EVALUATION.value, ModelType.TREE_EVALUATION.value]
        ]


@to_dict_mixin()
class ModelGroup(db.Model):
    __tablename__ = 'model_groups_v2'
    __table_args__ = (default_table_args('model_groups_v2'))

    id = db.Column(db.Integer, primary_key=True, comment='id')
    name = db.Column(db.String(255),
                     comment='name')  # can be modified by end-user

    created_at = db.Column(db.DateTime(timezone=True),
                           comment='created_at',
                           server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True),
                           comment='updated_at',
                           server_default=func.now(),
                           onupdate=func.now())
    deleted_at = db.Column(db.DateTime(timezone=True), comment='deleted_at')

    # TODO https://code.byted.org/data/fedlearner_web_console_v2/issues/289
    extra = db.Column(db.Text(), comment='extra')  # json string
