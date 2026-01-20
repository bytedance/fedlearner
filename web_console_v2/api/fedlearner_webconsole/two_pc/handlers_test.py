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
from unittest import mock
from unittest.mock import patch, MagicMock

from testing.no_web_server_test_case import NoWebServerTestCase
from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto.two_pc_pb2 import TwoPcType, TwoPcAction, TransactionData
from fedlearner_webconsole.two_pc.handlers import run_two_pc_action
from fedlearner_webconsole.two_pc.models import Transaction, TransactionState


class HandlersTest(NoWebServerTestCase):

    @patch('fedlearner_webconsole.two_pc.handlers.ModelJobCreator')
    def test_run_two_pc_action_new_transaction(self, mock_model_job_creator_class):
        mock_model_job_creator = MagicMock()
        mock_model_job_creator.run_two_pc = MagicMock(return_value=(True, 'aloha'))
        mock_model_job_creator_class.return_value = mock_model_job_creator

        tid = '123'
        tdata = TransactionData()
        with db.session_scope() as session:
            succeeded, message = run_two_pc_action(session=session,
                                                   tid=tid,
                                                   two_pc_type=TwoPcType.CREATE_MODEL_JOB,
                                                   action=TwoPcAction.PREPARE,
                                                   data=tdata)
            session.commit()
        self.assertTrue(succeeded)
        self.assertEqual(message, 'aloha')
        mock_model_job_creator_class.assert_called_once_with(tid=tid, data=tdata, session=mock.ANY)
        mock_model_job_creator.run_two_pc.assert_called_once_with(TwoPcAction.PREPARE)
        with db.session_scope() as session:
            trans: Transaction = session.query(Transaction).filter_by(uuid=tid).first()
            self.assertEqual(trans.get_type(), TwoPcType.CREATE_MODEL_JOB)
            self.assertEqual(trans.state, TransactionState.PREPARE_SUCCEEDED)
            self.assertEqual(trans.message, 'aloha')

    @patch('fedlearner_webconsole.two_pc.handlers.ModelJobCreator')
    def test_run_two_pc_action_redundant_action_idempotent(self, mock_model_job_creator_class):
        tid = '234234'
        with db.session_scope() as session:
            trans = Transaction(uuid=tid, state=TransactionState.PREPARE_SUCCEEDED, message='prepared')
            session.add(trans)
            session.commit()
        with db.session_scope() as session:
            succeeded, message = run_two_pc_action(session=session,
                                                   tid=tid,
                                                   two_pc_type=TwoPcType.CREATE_MODEL_JOB,
                                                   action=TwoPcAction.PREPARE,
                                                   data=TransactionData())
        self.assertTrue(succeeded)
        self.assertEqual(message, 'prepared')
        mock_model_job_creator_class.assert_not_called()

    @patch('fedlearner_webconsole.two_pc.handlers.ModelJobCreator')
    def test_run_two_pc_action_exception(self, mock_model_job_creator_class):
        mock_model_job_creator = MagicMock()
        mock_model_job_creator.run_two_pc = MagicMock(side_effect=RuntimeError('Unknown error'))
        mock_model_job_creator_class.return_value = mock_model_job_creator

        tid = '123234234'
        tdata = TransactionData()
        with db.session_scope() as session:
            trans = Transaction(uuid=tid, state=TransactionState.PREPARE_SUCCEEDED, message='prepared')
            session.add(trans)
            session.commit()
            succeeded, message = run_two_pc_action(session=session,
                                                   tid=tid,
                                                   two_pc_type=TwoPcType.CREATE_MODEL_JOB,
                                                   action=TwoPcAction.COMMIT,
                                                   data=tdata)
            session.commit()
        self.assertFalse(succeeded)
        self.assertIn('Unknown error', message)
        mock_model_job_creator.run_two_pc.assert_called_once_with(TwoPcAction.COMMIT)
        with db.session_scope() as session:
            trans: Transaction = session.query(Transaction).filter_by(uuid=tid).first()
            self.assertEqual(trans.state, TransactionState.INVALID)
            self.assertIn('Unknown error', trans.message)


if __name__ == '__main__':
    unittest.main()
