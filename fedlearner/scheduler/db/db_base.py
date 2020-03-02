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
from playhouse.apsw_ext import APSWDatabase
from playhouse.pool import PooledMySQLDatabase
from fedlearner.settings import DATABASE
from fedlearner.scheduler.db import DBTYPE

db_connection = None


def db_config():
    global db_connection #pylint: disable=W0603
    database_config = DATABASE.copy()
    db_type = database_config.pop("db_type")
    db_name = database_config.pop("db_name")
    if db_type == DBTYPE.SQLITE:
        db_connection = APSWDatabase(
            database_config.get('db_path', 'fedlearner.db'))
        logging.info('init sqlite database on standalone mode successfully')
    elif db_type == DBTYPE.MYSQL:
        db_connection = PooledMySQLDatabase(db_name, **database_config)
        logging.info('init mysql database on standalone mode successfully')
    else:
        raise Exception('can not init database')


def get_session():
    if db_connection:
        return db_connection
    db_config()
    return db_connection


def close_session(db_session):
    try:
        if db_session:
            db_session.close()
    except Exception as e: # pylint: disable=W0703
        logging.exception(e)
