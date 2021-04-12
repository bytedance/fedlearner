# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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
from datetime import timedelta

from sqlalchemy import UniqueConstraint
from sqlalchemy.engine import Engine
from sqlalchemy.sql import func

from fedlearner_webconsole.db import db, default_table_args


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
    def default(self, obj) -> dict:
        d = obj.__dict__
        return {
            '_data': d.get('_data', {}),
            '_internal': d.get('_internal', {})
        }


class ContextDecoder(json.JSONDecoder):
    def __init__(self, db_engine: Engine):
        self.db_engine = db_engine
        super().__init__(object_hook=self.dict2object)

    def dict2object(self, val):
        if '_data' in val and '_internal' in val:
            return Context(data=val.get('_data', {}),
                           internal=val.get('_internal', {}),
                           db_engine=self.db_engine)
        return val


def decode_context(val: str, db_engine: Engine) -> Context:
    if val in ('', '{}'):
        return Context(data={}, internal={}, db_engine=db_engine)
    return ContextDecoder(db_engine=db_engine).decode(val)


class ItemStatus(enum.Enum):
    OFF = 0  # invalid or expired
    ON = 1  # need to run


class SchedulerItem(db.Model):
    __tablename__ = 'scheduler_item_v2'
    __table_args__ = (UniqueConstraint('name', name='uniq_name'),
                      default_table_args('scheduler items'))
    id = db.Column(db.Integer,
                   comment='id',
                   primary_key=True,
                   autoincrement=True)
    name = db.Column(db.String(255), comment='item name', nullable=False)
    pipeline = db.Column(db.Text,
                         comment='pipeline',
                         nullable=False,
                         default='{}')
    status = db.Column(db.Integer,
                       comment='item status',
                       nullable=False,
                       default=ItemStatus.ON.value)
    interval = db.Column(db.Integer,
                         comment='item run interval in second',
                         nullable=False,
                         default=-1)
    last_run_at = db.Column(db.DateTime(timezone=True),
                            comment='last runner time')
    retry_cnt = db.Column(db.Integer,
                          comment='retry count when item is failed',
                          nullable=False,
                          default=0)
    extra = db.Column(db.Text(), comment='extra info')
    created_at = db.Column(db.DateTime(timezone=True),
                           comment='created at',
                           server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True),
                           comment='updated at',
                           server_default=func.now(),
                           onupdate=func.now())
    deleted_at = db.Column(db.DateTime(timezone=True), comment='deleted at')

    def need_run(self) -> bool:
        # job runs one time
        if self.interval == -1 and self.last_run_at is None:
            return True
        if self.interval > 0:  # cronjob
            if self.last_run_at is None:  # never run
                return True
            # compare datetime in utc
            if self.last_run_at + timedelta(
                    seconds=self.interval) < func.now():
                return True
        return False


class RunnerStatus(enum.Enum):
    INIT = 0
    RUNNING = 1
    DONE = 2
    FAILED = 3


class SchedulerRunner(db.Model):
    __tablename__ = 'scheduler_runner_v2'
    __table_args__ = (default_table_args('scheduler runners'))
    id = db.Column(db.Integer,
                   comment='id',
                   primary_key=True,
                   autoincrement=True)
    item_id = db.Column(db.Integer, comment='item id', nullable=False)
    status = db.Column(db.Integer,
                       comment='runner status',
                       nullable=False,
                       default=RunnerStatus.INIT.value)
    start_at = db.Column(db.DateTime(timezone=True),
                         comment='runner start time')
    end_at = db.Column(db.DateTime(timezone=True), comment='runner end time')
    pipeline = db.Column(db.Text(),
                         comment='pipeline from scheduler item',
                         nullable=False,
                         default='{}')
    output = db.Column(db.Text(),
                       comment='output',
                       nullable=False,
                       default='{}')
    context = db.Column(db.Text(),
                        comment='context',
                        nullable=False,
                        default='{}')
    extra = db.Column(db.Text(), comment='extra info')
    created_at = db.Column(db.DateTime(timezone=True),
                           comment='created at',
                           server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True),
                           comment='updated at',
                           server_default=func.now(),
                           onupdate=func.now())
    deleted_at = db.Column(db.DateTime(timezone=True), comment='deleted at')


class OptimisticLock(db.Model):
    __tablename__ = 'optimistic_lock_v2'
    __table_args__ = (
        UniqueConstraint('name', name='uniq_name'),
        default_table_args('optimistic lock'),
    )
    id = db.Column(db.Integer,
                   comment='id',
                   primary_key=True,
                   autoincrement=True)
    name = db.Column(db.String(255), comment='lock name', nullable=False)
    version = db.Column(db.BIGINT, comment='lock version', nullable=False)
    created_at = db.Column(db.DateTime(timezone=True),
                           comment='created at',
                           server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True),
                           comment='updated at',
                           server_default=func.now(),
                           onupdate=func.now())
    deleted_at = db.Column(db.DateTime(timezone=True), comment='deleted at')
