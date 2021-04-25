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
from contextlib import contextmanager
from enum import Enum
from datetime import datetime, timezone
from typing import List, Dict, Callable

from flask_sqlalchemy import SQLAlchemy
from google.protobuf.message import Message
from google.protobuf.json_format import MessageToDict
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

# Explicitly set autocommit and autoflush
# Disables autocommit to make developers to commit manually
# Enables autoflush to make changes visible in the same session
SESSION_OPTIONS = {'autocommit': False, 'autoflush': True}
db = SQLAlchemy(session_options=SESSION_OPTIONS)


def to_dict_mixin(ignores: List[str] = None,
                  extras: Dict[str, Callable] = None):
    if ignores is None:
        ignores = []
    if extras is None:
        extras = {}

    def decorator(cls):
        """A decorator to add a to_dict method to a sqlalchemy model class."""
        def to_dict(self: db.Model):
            """A helper function to convert a sqlalchemy model to dict."""
            dic = {}
            # Puts all columns into the dict
            for col in self.__table__.columns:
                if col.key in ignores:
                    continue
                dic[col.key] = getattr(self, col.key)
            # Puts extra items specified by consumer
            for extra_key, func in extras.items():
                dic[extra_key] = func(self)
            # Converts type
            for key in dic:
                value = dic[key]
                if isinstance(value, datetime):
                    # If there is no timezone, we should treat it as
                    # UTC datetime,otherwise it will be calculated
                    # as local time when converting to timestamp.
                    # Context: all datetime in db is UTC datetime,
                    # see details in config.py#turn_db_timezone_to_utc
                    if value.tzinfo is None:
                        dic[key] = int(value.replace(
                            tzinfo=timezone.utc).timestamp())
                    else:
                        dic[key] = int(value.timestamp())
                elif isinstance(value, Message):
                    dic[key] = MessageToDict(
                        value,
                        preserving_proto_field_name=True,
                        including_default_value_fields=True)
                elif isinstance(value, Enum):
                    dic[key] = value.name
            return dic

        setattr(cls, 'to_dict', to_dict)
        return cls

    return decorator


def default_table_args(comment: str) -> dict:
    return {
        'comment': comment,
        'mysql_engine': 'innodb',
        'mysql_charset': 'utf8mb4',
    }


@contextmanager
def get_session(db_engine: Engine):
    """Get session from database engine.

    Example:
        with get_session(db_engine) as session:
            # write your query, do not need to handle database connection
            session.query(MODEL).filter_by(field=value).first()
    """
    try:
        session = sessionmaker(bind=db_engine, **SESSION_OPTIONS)()
    except Exception:
        raise Exception('unknown db engine')
    else:
        yield session
    finally:
        session.close()
