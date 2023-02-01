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

import enum
import json
import logging
from datetime import timezone, datetime
from sqlalchemy import UniqueConstraint, Index
from sqlalchemy.engine import Engine
from sqlalchemy.sql import func
from croniter import croniter

from fedlearner_webconsole.db import db, default_table_args
from fedlearner_webconsole.proto import composer_pb2
from fedlearner_webconsole.utils.pp_datetime import now
from fedlearner_webconsole.utils.mixins import to_dict_mixin
from fedlearner_webconsole.utils.proto import to_json, parse_from_json
from fedlearner_webconsole.proto.composer_pb2 import SchedulerItemPb, SchedulerRunnerPb
from fedlearner_webconsole.utils.pp_datetime import to_timestamp


class Context(object):

    def __init__(self, data: dict, internal: dict, db_engine: Engine):
        self._data = data  # user data
        self._internal = internal  # internal system data
        self._db_engine = db_engine  # db engine

    @property
    def data(self) -> dict:
        return self._data

    def set_data(self, key: str, val: object):
        self._data[key] = val

    @property
    def internal(self) -> dict:
        return self._internal

    def set_internal(self, key: str, val: object):
        self._internal[key] = val

    @property
    def db_engine(self) -> Engine:
        return self._db_engine


class ContextEncoder(json.JSONEncoder):

    def default(self, o) -> dict:
        d = o.__dict__
        return {'_data': d.get('_data', {}), '_internal': d.get('_internal', {})}


class ContextDecoder(json.JSONDecoder):

    def __init__(self, db_engine: Engine):
        self.db_engine = db_engine
        super().__init__(object_hook=self.dict2object)

    def dict2object(self, val):
        if '_data' in val and '_internal' in val:
            return Context(data=val.get('_data', {}), internal=val.get('_internal', {}), db_engine=self.db_engine)
        return val


def decode_context(val: str, db_engine: Engine) -> Context:
    if val in ('', '{}'):
        return Context(data={}, internal={}, db_engine=db_engine)
    return ContextDecoder(db_engine=db_engine).decode(val)


class ItemStatus(enum.Enum):
    OFF = 0  # invalid or expired
    ON = 1  # need to run


@to_dict_mixin(extras={'need_run': (lambda si: si.need_run())})
class SchedulerItem(db.Model):
    __tablename__ = 'scheduler_item_v2'
    __table_args__ = (
        UniqueConstraint('name', name='uniq_name'),
        # idx_status is a common name will may cause conflict in sqlite
        Index('idx_item_status', 'status'),
        default_table_args('scheduler items'),
    )
    id = db.Column(db.Integer, comment='id', primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), comment='item name', nullable=False)
    pipeline = db.Column(db.Text(16777215), comment='pipeline', nullable=False, default='{}')
    status = db.Column(db.Integer, comment='item status', nullable=False, default=ItemStatus.ON.value)
    cron_config = db.Column(db.String(255), comment='cron expression in UTC timezone')
    last_run_at = db.Column(db.DateTime(timezone=True), comment='last runner time')
    retry_cnt = db.Column(db.Integer, comment='retry count when item is failed', nullable=False, default=0)
    extra = db.Column(db.Text(), comment='extra info')
    created_at = db.Column(db.DateTime(timezone=True), comment='created at', server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True),
                           comment='updated at',
                           server_default=func.now(),
                           onupdate=func.now())
    deleted_at = db.Column(db.DateTime(timezone=True), comment='deleted at')

    def need_run(self) -> bool:
        if not self.cron_config:
            # job runs once
            return self.last_run_at is None
        # cronjob
        if self.last_run_at is None:  # never run
            # if there is no start time, croniter will return next run
            # datetime (UTC) based on create time
            base = self.created_at.replace(tzinfo=timezone.utc)
        else:
            base = self.last_run_at.replace(tzinfo=timezone.utc)
        next_run_at = croniter(self.cron_config, base).get_next(datetime)
        utc_now = now(timezone.utc)
        logging.debug(f'[composer] item id: {self.id}, '
                      f'next_run_at: {next_run_at.timestamp()}, '
                      f'utc_now: {utc_now.timestamp()}')
        return next_run_at.timestamp() < utc_now.timestamp()

    def set_pipeline(self, proto: composer_pb2.Pipeline):
        self.pipeline = to_json(proto)

    def get_pipeline(self) -> composer_pb2.Pipeline:
        return parse_from_json(self.pipeline, composer_pb2.Pipeline())

    def to_proto(self) -> SchedulerItemPb:
        return SchedulerItemPb(id=self.id,
                               name=self.name,
                               pipeline=self.get_pipeline(),
                               status=ItemStatus(self.status).name,
                               cron_config=self.cron_config,
                               last_run_at=to_timestamp(self.last_run_at) if self.last_run_at else None,
                               retry_cnt=self.retry_cnt,
                               created_at=to_timestamp(self.created_at) if self.created_at else None,
                               updated_at=to_timestamp(self.updated_at) if self.updated_at else None,
                               deleted_at=to_timestamp(self.deleted_at) if self.deleted_at else None)


class RunnerStatus(enum.Enum):
    INIT = 0
    RUNNING = 1
    DONE = 2
    FAILED = 3


@to_dict_mixin()
class SchedulerRunner(db.Model):
    __tablename__ = 'scheduler_runner_v2'
    __table_args__ = (
        # idx_status is a common name will may cause conflict in sqlite
        Index('idx_runner_status', 'status'),
        Index('idx_runner_item_id', 'item_id'),
        default_table_args('scheduler runners'),
    )
    id = db.Column(db.Integer, comment='id', primary_key=True, autoincrement=True)
    item_id = db.Column(db.Integer, comment='item id', nullable=False)
    status = db.Column(db.Integer, comment='runner status', nullable=False, default=RunnerStatus.INIT.value)
    start_at = db.Column(db.DateTime(timezone=True), comment='runner start time')
    end_at = db.Column(db.DateTime(timezone=True), comment='runner end time')
    pipeline = db.Column(db.Text(16777215), comment='pipeline from scheduler item', nullable=False, default='{}')
    output = db.Column(db.Text(), comment='output', nullable=False, default='{}')
    context = db.Column(db.Text(16777215), comment='context', nullable=False, default='{}')
    extra = db.Column(db.Text(), comment='extra info')
    created_at = db.Column(db.DateTime(timezone=True), comment='created at', server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True),
                           comment='updated at',
                           server_default=func.now(),
                           onupdate=func.now())
    deleted_at = db.Column(db.DateTime(timezone=True), comment='deleted at')

    def set_pipeline(self, proto: composer_pb2.Pipeline):
        self.pipeline = to_json(proto)

    def get_pipeline(self) -> composer_pb2.Pipeline:
        return parse_from_json(self.pipeline, composer_pb2.Pipeline())

    def set_context(self, proto: composer_pb2.PipelineContextData):
        self.context = to_json(proto)

    def get_context(self) -> composer_pb2.PipelineContextData:
        return parse_from_json(self.context, composer_pb2.PipelineContextData())

    def set_output(self, proto: composer_pb2.RunnerOutput):
        self.output = to_json(proto)

    def get_output(self) -> composer_pb2.RunnerOutput:
        return parse_from_json(self.output, composer_pb2.RunnerOutput())

    def to_proto(self) -> SchedulerRunnerPb:
        return SchedulerRunnerPb(id=self.id,
                                 item_id=self.item_id,
                                 status=RunnerStatus(self.status).name,
                                 start_at=to_timestamp(self.start_at) if self.start_at else None,
                                 end_at=to_timestamp(self.end_at) if self.end_at else None,
                                 pipeline=self.get_pipeline(),
                                 output=self.get_output(),
                                 context=self.get_context(),
                                 created_at=to_timestamp(self.created_at) if self.created_at else None,
                                 updated_at=to_timestamp(self.updated_at) if self.updated_at else None,
                                 deleted_at=to_timestamp(self.deleted_at) if self.deleted_at else None)


class OptimisticLock(db.Model):
    __tablename__ = 'optimistic_lock_v2'
    __table_args__ = (
        UniqueConstraint('name', name='uniq_name'),
        default_table_args('optimistic lock'),
    )
    id = db.Column(db.Integer, comment='id', primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), comment='lock name', nullable=False)
    version = db.Column(db.BIGINT, comment='lock version', nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), comment='created at', server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True),
                           comment='updated at',
                           server_default=func.now(),
                           onupdate=func.now())
    deleted_at = db.Column(db.DateTime(timezone=True), comment='deleted at')
