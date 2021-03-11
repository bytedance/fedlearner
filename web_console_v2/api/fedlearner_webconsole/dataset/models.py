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
        'data_batches':
        lambda dataset:
        [data_batch.to_dict() for data_batch in dataset.data_batches]
    })
class Dataset(db.Model):
    __tablename__ = 'datasets_v2'
    __table_args__ = ({
        'comment': 'This is webconsole dataset table',
        'mysql_engine': 'innodb',
        'mysql_charset': 'utf8mb4',
    })

    id = db.Column(db.Integer,
                   primary_key=True,
                   autoincrement=True,
                   comment='id')
    name = db.Column(db.String(255), nullable=False, comment='dataset name')
    dataset_type = db.Column(db.Enum(DatasetType, native_enum=False),
                             nullable=False,
                             comment='data type')
    path = db.Column(db.String(512), comment='dataset path')
    comment = db.Column('cmt',
                        db.Text(),
                        key='comment',
                        comment='comment of dataset')
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(),
                           comment='created time')
    updated_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(),
                           onupdate=func.now(),
                           comment='updated time')
    deleted_at = db.Column(db.DateTime(timezone=True), comment='deleted time')

    data_batches = db.relationship(
        'DataBatch', primaryjoin='foreign(DataBatch.dataset_id) == Dataset.id')


@to_dict_mixin(extras={'details': (lambda batch: batch.get_details())})
class DataBatch(db.Model):
    __tablename__ = 'data_batches_v2'
    __table_args__ = (
        UniqueConstraint('event_time',
                         'dataset_id',
                         name='uniq_event_time_dataset_id'),
        {
            'comment': 'This is webconsole dataset table',
            'mysql_engine': 'innodb',
            'mysql_charset': 'utf8mb4',
        },
    )
    id = db.Column(db.Integer,
                   primary_key=True,
                   autoincrement=True,
                   comment='id')
    event_time = db.Column(db.TIMESTAMP(timezone=True),
                           nullable=False,
                           comment='event_time')
    dataset_id = db.Column(db.Integer, nullable=False, comment='dataset_id')
    path = db.Column(db.String(512), comment='path')
    state = db.Column(db.Enum(BatchState, native_enum=False),
                      default=BatchState.NEW,
                      comment='state')
    move = db.Column(db.Boolean, default=False, comment='move')
    # Serialized proto of DatasetBatch
    details = db.Column(db.LargeBinary(), comment='details')
    file_size = db.Column(db.Integer, default=0, comment='file_size')
    num_imported_file = db.Column(db.Integer,
                                  default=0,
                                  comment='num_imported_file')
    num_file = db.Column(db.Integer, default=0, comment='num_file')
    comment = db.Column('cmt', db.Text(), key='comment', comment='comment')
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(),
                           comment='created_at')
    updated_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(),
                           server_onupdate=func.now(),
                           comment='updated_at')
    deleted_at = db.Column(db.DateTime(timezone=True), comment='deleted_at')

    dataset = db.relationship('Dataset',
                              primaryjoin='Dataset.id == '
                              'foreign(DataBatch.dataset_id)',
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
