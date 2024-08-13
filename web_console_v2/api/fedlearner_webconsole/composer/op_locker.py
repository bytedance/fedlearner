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

import logging

from sqlalchemy.engine import Engine

from fedlearner_webconsole.composer.models import OptimisticLock
from fedlearner_webconsole.db import get_session


class OpLocker(object):

    def __init__(self, name: str, db_engine: Engine):
        """Optimistic Lock

        Args:
            name (str): lock name should be unique in same thread
            db_engine (Engine): db engine
        """
        self._name = name
        self._version = 0
        self._has_lock = False
        self.db_engine = db_engine

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> int:
        return self._version

    def try_lock(self) -> 'OpLocker':
        with get_session(self.db_engine) as session:
            try:
                lock = session.query(OptimisticLock).filter_by(name=self._name).first()
                if lock:
                    self._has_lock = True
                    self._version = lock.version
                    return self
                new_lock = OptimisticLock(name=self._name, version=self._version)
                session.add(new_lock)
                session.commit()
                self._has_lock = True
                return self
            except Exception as e:  # pylint: disable=broad-except
                logging.error(f'failed to require lock, exception: {e}')
                return self

    def is_latest_version(self) -> bool:
        if not self._has_lock:
            return False

        with get_session(self.db_engine) as session:
            try:
                new_lock = session.query(OptimisticLock).filter_by(name=self._name).first()
                if not new_lock:
                    return False
                logging.info(f'[op_locker] version, current: {self._version}, ' f'new: {new_lock.version}')
                return self._version == new_lock.version
            except Exception as e:  # pylint: disable=broad-except
                logging.error(f'failed to check lock is conflict, exception: {e}')
                return False

    def update_version(self) -> bool:
        # double check
        if not self.is_latest_version():
            return False

        with get_session(self.db_engine) as session:
            try:
                lock = session.query(OptimisticLock).filter_by(name=self._name).first()
                lock.version = self._version + 1
                session.commit()
                return True
            except Exception as e:  # pylint: disable=broad-except
                logging.error(f'failed to update lock version, exception: {e}')
                return False
