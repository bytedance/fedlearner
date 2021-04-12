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

import logging
import sys
import unittest

from testing.common import BaseTestCase, OptimisticLock
from fedlearner_webconsole.db import db
from fedlearner_webconsole.composer.op_locker import OpLocker


class OpLockTest(BaseTestCase):
    class Config(BaseTestCase.Config):
        STORAGE_ROOT = '/tmp'
        START_SCHEDULER = False
        START_GRPC_SERVER = False
        START_COMPOSER = False

    def setUp(self):
        super().setUp()

    def test_lock(self):
        lock = OpLocker('test', db.engine).try_lock()
        self.assertEqual(True, lock.is_latest_version(),
                         'should be latest version')

        # update database version
        new_lock = db.session.query(OptimisticLock).filter_by(
            name=lock.name).first()
        new_lock.version = new_lock.version + 1
        db.session.commit()
        self.assertEqual(False, lock.is_latest_version(),
                         'should not be latest version')


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    unittest.main()
