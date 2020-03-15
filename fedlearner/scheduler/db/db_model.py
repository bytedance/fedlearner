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

import sys
import datetime
import inspect
import logging
from enum import Enum
from peewee import Model, CharField, IntegerField,\
        TextField, ForeignKeyField
from playhouse.apsw_ext import DateTimeField
from fedlearner.scheduler.db.db_base import get_session

DB = get_session()


class APPSTATUS(Enum):
    NEW = "FLStateNew"
    BOOTSTRAPPED = "FLStateBootstrapped"
    SYNCSEND = "FLStateSyncSent"
    RUNNING = "FLStateRunning"
    COMPELTE = "FLStateComplete"
    FAILING = "FLStateFailing"
    SHUTDOWN = "FLStateShutDown"
    FAILED = "FLStateFailed"


class JOBSTATUS(Enum):
    SUBMMITTED = 'submitted'
    RUNNING = 'running'
    KILLING = 'killing'
    FAILING = 'failing'
    KILLED = 'killed'
    FAILED = 'failed'
    SUCCESS = 'success'


JOB_STATUS_TRANSITION = {
    JOBSTATUS.SUBMMITTED.value:
    set([JOBSTATUS.RUNNING.value, JOBSTATUS.FAILED.value]),
    JOBSTATUS.RUNNING.value:
    set([
        JOBSTATUS.KILLING.value, JOBSTATUS.FAILED.value,
        JOBSTATUS.KILLED.value, JOBSTATUS.FAILING.value,
        JOBSTATUS.SUCCESS.value
    ]),
    JOBSTATUS.KILLING.value:
    set([JOBSTATUS.KILLED.value]),
    JOBSTATUS.FAILED.value:
    set([JOBSTATUS.FAILED.value])
}


def init_database_tables():
    with DB.connection_context():
        members = inspect.getmembers(sys.modules[__name__], inspect.isclass)
        table_objs = []
        for name, obj in members:
            if obj != Model and issubclass(obj, Model):
                table_objs.append(obj)
        DB.create_tables(table_objs)


class DataSourceMeta(Model):
    name = CharField(max_length=500)
    description = TextField(null=True, default='')
    path = TextField()
    create_time = DateTimeField(default=datetime.datetime.now)
    update_time = DateTimeField(null=True)

    class Meta:
        database = DB
        db_table = "data_source_meta"

    def __str__(self):
        return str(self.__dict__['__data__'])

    def save(self, *args, **kwargs):
        self.update_time = datetime.datetime.now()
        super(DataSourceMeta, self).save(*args, **kwargs)


class ModelMeta(Model):
    name = CharField(max_length=500)
    description = TextField(null=True, default='')
    image = CharField(max_length=500)
    code_url = CharField(max_length=500)
    create_time = DateTimeField(default=datetime.datetime.now)
    update_time = DateTimeField(null=True)

    def __str__(self):
        return str(self.__dict__['__data__'])

    class Meta:
        database = DB
        db_table = "model_meta"

    def save(self, *args, **kwargs):
        self.update_time = datetime.datetime.now()
        super(ModelMeta, self).save(*args, **kwargs)


class ModelVersion(Model):
    model_meta_id = ForeignKeyField(ModelMeta, backref='model_version')
    commit = CharField(max_length=500)
    description = CharField(max_length=500)
    create_time = DateTimeField(default=datetime.datetime.now)
    update_time = DateTimeField(null=True)

    class Meta:
        database = DB
        db_table = "model_version"

    def __str__(self):
        return str(self.__dict__['__data__'])

    def save(self, *args, **kwargs):
        self.update_time = datetime.datetime.now()
        super(ModelVersion, self).save(*args, **kwargs)


class Job(Model):
    name = CharField(max_length=500)
    description = TextField(null=True, default='')
    role = CharField(max_length=50, index=True)
    application_id = CharField(max_length=500, null=True)
    model_version_id = ForeignKeyField(ModelVersion, backref='model_version')
    serving_version = CharField(max_length=500)
    data_source_id = ForeignKeyField(DataSourceMeta,
                                     backref='data_source_meta')
    cluster_spec = TextField()
    status = CharField(max_length=50)
    k8s_status = CharField(max_length=50, default='unknown')
    progress = IntegerField(null=True, default=0)
    group_list = TextField(null=False, default='{}')
    create_time = DateTimeField(default=datetime.datetime.now)
    update_time = DateTimeField(null=True)
    start_time = DateTimeField(null=True)
    end_time = DateTimeField(null=True)

    class Meta:
        database = DB
        db_table = "job"

    def to_json(self):
        return self.__dict__['__data__']

    def save(self, *args, **kwargs):
        self.update_time = datetime.datetime.now()
        super(Job, self).save(*args, **kwargs)


def change_job_status(job, from_status, to_status):
    if from_status == to_status:
        return
    if to_status not in JOB_STATUS_TRANSITION.get(from_status, set()):
        raise Exception('task_status_transition; [%s] -> [%s] is illegal' %
                        (from_status, to_status))
    if from_status == JOBSTATUS.SUBMMITTED.value:
        job.start_time = datetime.datetime.now()
    if to_status in [
            JOBSTATUS.FAILED.value, JOBSTATUS.KILLED.value,
            JOBSTATUS.SUCCESS.value
    ]:
        job.end_time = datetime.datetime.now()
    job.status = to_status
    job.save()
    logging.info('job [%d] change status [%s] to [%s].', job.id, from_status,
                 to_status)
