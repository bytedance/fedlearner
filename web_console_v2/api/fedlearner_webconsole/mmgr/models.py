# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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
from datetime import datetime
from sqlalchemy.orm import remote, foreign
from fedlearner_webconsole.db import db, to_dict_mixin, default_table_args
from fedlearner_webconsole.job.models import Job


class ModelType(enum.Enum):
    NN_MODEL = 0
    NN_EVALUATION = 1
    TREE_MODEL = 2
    TREE_EVALUATION = 3


class ModelState(enum.Enum):
    COMMITTING = 0  # Uncommitted Model
    COMMITTED = 1  # Committed Model Before Running
    RUNNING = 2  # Running Model
    STOPPED = 3  # Stop by User
    FINISHED = 4  # Finished Model
    SUCCEEDED = 5  # Finished and SUCCEEDED
    FAILED = 6  # Finished and Failed
    DROPPING = 7  # Uncommitted Dropping Model
    DROPPED = 8  # Deleted Model


# TODO transaction
@to_dict_mixin()
class Model(db.Model):
    __tablename__ = 'models_v2'
    __table_args__ = (default_table_args('model'))

    id = db.Column(db.Integer, primary_key=True, comment='id')
    name = db.Column(db.String(255), comment='model_name')
    version = db.Column(db.Integer, comment='model_version')
    parent_id = db.Column(db.String(255), comment='parent_id')
    job_name = db.Column(db.String(255), comment='job_name')
    type = db.Column(db.Enum(ModelType, native_enum=False), comment='type')
    state = db.Column(db.Enum(ModelState, native_enum=False), comment='state')
    create_time = db.Column(db.DateTime(timezone=True), comment='create_time')
    params = db.Column(db.Text(), comment='params')
    metrics = db.Column(db.Text(), comment='metrics')
    output_base_dir = db.Column(db.String(255),
                                comment='model checkpoint/export path')
    parent = db.relationship('Model',
                             primaryjoin=remote(id) == foreign(parent_id),
                             backref='children')
    job = db.relationship('Job', primaryjoin=Job.name == foreign(job_name))

    def __init__(self):
        self.create_time = datetime.now()
        self.version = 0

    def commit(self):
        db.session.add(self)
        db.session.commit()

    def get_eval_model(self):
        """
        Get the evaluation model inherited model

        Returns:
             a list of evaluation model
        """
        eval_model = [
            child for child in self.children if child.type in
            [ModelType.NN_EVALUATION, ModelType.TREE_EVALUATION]
        ]
        return eval_model
