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
from sqlalchemy import UniqueConstraint
from fedlearner_webconsole.db import db, to_dict_mixin
from fedlearner_webconsole.proto import dataset_pb2


class DatasetType(enum.Enum):
    PSI = 'PSI'
    STREAMING = 'STREAMING'


class BatchState(enum.Enum):
    NEW = 'NEW'
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
    name = db.Column(db.String(255), unique=True, nullable=False)
    dataset_type = db.Column(db.Enum(DatasetType, native_enum=False),
                             nullable=False)
    path = db.Column(db.String(512))
    comment = db.Column('cmt', db.Text(), key='comment')
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(),
                           onupdate=func.now())
    deleted_at = db.Column(db.DateTime(timezone=True))

    data_batches = db.relationship(
        'DataBatch',
        primaryjoin='foreign(DataBatch.dataset_id) == Dataset.id')


@to_dict_mixin(
    extras={
        'details': (lambda batch: batch.get_details())
    })
class DataBatch(db.Model):
    __tablename__ = 'data_batches_v2'
    __table_args__ = (UniqueConstraint('event_time', 'dataset_id'),)
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_time = db.Column(db.TIMESTAMP(timezone=True),
                           nullable=False)
    dataset_id = db.Column(db.Integer, nullable=False)
    path = db.Column(db.String(512))
    state = db.Column(db.Enum(BatchState, native_enum=False),
                      default=BatchState.NEW)
    move = db.Column(db.Boolean, default=False)
    # Serialized proto of DatasetBatch
    details = db.Column(db.LargeBinary())
    file_size = db.Column(db.Integer, default=0)
    num_imported_file = db.Column(db.Integer, default=0)
    num_file = db.Column(db.Integer, default=0)
    comment = db.Column('cmt', db.Text(), key='comment')
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(),
                           server_onupdate=func.now())
    deleted_at = db.Column(db.DateTime(timezone=True))

    dataset = db.relationship('Dataset', foreign_keys=[dataset_id],
                              primaryjoin='Dataset.id == DataBatch.dataset_id',
                              back_populates='data_batches')

    def set_details(self, proto):
        self.num_file = len(proto.files)
        num_imported_file = 0
        num_failed_file = 0
        file_size = 0
        # Aggregates stats
        for file in proto.files:
            if file.state == dataset_pb2.File.State.COMPLETED:
                num_imported_file += 1
                file_size += file.size
            elif file.state == dataset_pb2.File.State.FAILED:
                num_failed_file += 1
        if num_imported_file + num_failed_file == self.num_file:
            if num_failed_file > 0:
                self.state = BatchState.FAILED
            else:
                self.state = BatchState.SUCCESS
        self.num_imported_file = num_imported_file
        self.file_size = file_size
        self.details = proto.SerializeToString()

    def get_details(self):
        if self.details is None:
            return None
        proto = dataset_pb2.DataBatch()
        proto.ParseFromString(self.details)
        return proto
