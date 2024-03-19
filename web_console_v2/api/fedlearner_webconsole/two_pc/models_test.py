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
import unittest

from fedlearner_webconsole.proto.two_pc_pb2 import TwoPcType, TwoPcAction
from fedlearner_webconsole.two_pc.models import Transaction, TransactionState


class TransactionTest(unittest.TestCase):

    def test_two_pc_type(self):
        trans = Transaction()
        trans.set_type(TwoPcType.CREATE_MODEL_JOB)
        self.assertEqual(trans._two_pc_type, 'CREATE_MODEL_JOB')  # pylint: disable=protected-access
        self.assertEqual(trans.get_type(), TwoPcType.CREATE_MODEL_JOB)

    def test_is_valid_action(self):
        trans = Transaction(state=TransactionState.NEW)
        self.assertTrue(trans.is_valid_action(TwoPcAction.PREPARE))
        self.assertFalse(trans.is_valid_action(TwoPcAction.COMMIT))
        trans.state = TransactionState.PREPARE_FAILED
        self.assertTrue(trans.is_valid_action(TwoPcAction.ABORT))
        self.assertFalse(trans.is_valid_action(TwoPcAction.COMMIT))
        trans.state = TransactionState.INVALID
        self.assertFalse(trans.is_valid_action(TwoPcAction.ABORT))

    def test_check_idempotent_invalid(self):
        trans = Transaction(state=TransactionState.INVALID, message='invalid')
        executed, result, message = trans.check_idempotent(TwoPcAction.COMMIT)
        self.assertTrue(executed)
        self.assertFalse(result)
        self.assertEqual(message, 'invalid')

    def test_check_idempotent_executed(self):
        trans = Transaction(state=TransactionState.PREPARE_SUCCEEDED, message='prepared')
        executed, result, message = trans.check_idempotent(TwoPcAction.PREPARE)
        self.assertTrue(executed)
        self.assertTrue(result)
        self.assertEqual(message, 'prepared')

    def test_check_idempotent_has_not_executed(self):
        trans = Transaction(state=TransactionState.PREPARE_SUCCEEDED, message='prepared')
        self.assertEqual(trans.check_idempotent(TwoPcAction.COMMIT), (False, None, None))

    def test_update_failed(self):
        trans = Transaction(state=TransactionState.PREPARE_SUCCEEDED)
        trans.update(TwoPcAction.COMMIT, False, 'failed to abort')
        self.assertEqual(trans.state, TransactionState.INVALID)
        self.assertEqual(
            trans.message,
            '[2pc] Invalid transition: [TransactionState.PREPARE_SUCCEEDED - 1 - False], extra: failed to abort')

    def test_update_successfully(self):
        trans = Transaction(state=TransactionState.PREPARE_SUCCEEDED)
        trans.update(TwoPcAction.COMMIT, True, 'yeah')
        self.assertEqual(trans.state, TransactionState.COMMITTED)
        self.assertEqual(trans.message, 'yeah')

        trans = Transaction(state=TransactionState.PREPARE_SUCCEEDED)
        trans.update(action=TwoPcAction.ABORT, succeeded=True, message='yep')
        self.assertEqual(trans.state, TransactionState.ABORTED)
        self.assertEqual(trans.message, 'yep')


if __name__ == '__main__':
    unittest.main()
