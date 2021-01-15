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

import enum
from sqlalchemy.sql import func
from sqlalchemy import PrimaryKeyConstraint
from fedlearner_webconsole.db import db, to_dict_mixin
from fedlearner_webconsole.proto import dataset_pb2


class DatasetType(enum.Enum):
    PSI = 'PSI'
    STREAMING = 'STREAMING'


class BatchState(enum.Enum):
    SUCCESS = 'SUCCESS'
    FAILED = 'FAILED'
    IMPORTING = 'IMPORTING'


@to_dict_mixin(
    extras={
        'data_batches': lambda dataset: [data_batch.to_dict()
                                         for data_batch in dataset.data_batches]
    }
)
class Dataset(db.Model):
    __tablename__ = 'datasets_v2'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), unique=True)
    type = db.Column(db.Enum(DatasetType))
    external_storage_path = db.Column(db.Text())
    comment = db.Column(db.Text())
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(),
                           server_onupdate=func.now())
    deleted_at = db.Column(db.DateTime(timezone=True))

    data_batches = db.relationship('DataBatch', back_populates='dataset')


@to_dict_mixin(
    extras={
        'source': (lambda batch: batch.get_source())
    })
class DataBatch(db.Model):
    __tablename__ = 'data_batches_v2'
    __table_args__ = (PrimaryKeyConstraint('event_time', 'dataset_id'),)
    event_time = db.Column(db.TIMESTAMP(timezone=True))
    dataset_id = db.Column(db.Integer, db.ForeignKey(Dataset.id))
    state = db.Column(db.Enum(BatchState))
    source = db.Column(db.Text(),
                       default=dataset_pb2.DatasetSource().SerializeToString())
    failed_source = db.Column(db.Text())
    file_size = db.Column(db.Integer, default=0)
    imported_file_num = db.Column(db.Integer, default=0)
    file_num = db.Column(db.Integer, default=0)
    comment = db.Column(db.Text())
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(),
                           server_onupdate=func.now())
    deleted_at = db.Column(db.DateTime(timezone=True))

    dataset = db.relationship('Dataset', back_populates='data_batches')

    def set_source(self, proto):
        self.source = proto.SerializeToString()

    def get_source(self):
        if self.source is None:
            return None
        proto = dataset_pb2.DatasetSource()
        proto.ParseFromString(self.source)
        return proto
