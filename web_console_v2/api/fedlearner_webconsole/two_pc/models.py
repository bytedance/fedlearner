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
from typing import Tuple, Optional

from sqlalchemy import func, Index

from fedlearner_webconsole.db import db, default_table_args
from fedlearner_webconsole.proto.two_pc_pb2 import TwoPcType, TwoPcAction
from fedlearner_webconsole.utils.mixins import to_dict_mixin


class TransactionState(enum.Enum):
    NEW = 'NEW'
    PREPARE_SUCCEEDED = 'PREPARE_SUCCEEDED'
    PREPARE_FAILED = 'PREPARE_FAILED'
    COMMITTED = 'COMMITTED'
    ABORTED = 'ABORTED'
    INVALID = 'INVALID'


# Valid transition mappings:
# Current state - action - result - new state
_VALID_TRANSITIONS = {
    TransactionState.NEW: {
        TwoPcAction.PREPARE: {
            True: TransactionState.PREPARE_SUCCEEDED,
            False: TransactionState.PREPARE_FAILED,
        }
    },
    TransactionState.PREPARE_SUCCEEDED: {
        TwoPcAction.COMMIT: {
            True: TransactionState.COMMITTED,
        },
        TwoPcAction.ABORT: {
            True: TransactionState.ABORTED,
        }
    },
    TransactionState.PREPARE_FAILED: {
        TwoPcAction.ABORT: {
            True: TransactionState.ABORTED,
        }
    }
}


@to_dict_mixin(ignores=['_type'], extras={'type': lambda t: t.get_type()})
class Transaction(db.Model):
    __tablename__ = 'transactions_v2'
    __table_args__ = (Index('uniq_uuid', 'uuid', unique=True), default_table_args('2pc transactions'))
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='id')
    uuid = db.Column(db.String(64), comment='uuid')
    # 2PC type, consistent with TwoPcType in proto
    _two_pc_type = db.Column('type', db.String(32), comment='2pc type name')
    state = db.Column(db.Enum(TransactionState, native_enum=False, create_constraint=False, length=32),
                      default=TransactionState.NEW,
                      comment='state')
    message = db.Column(db.Text(), comment='message of the last action')
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), comment='created_at')
    updated_at = db.Column(db.DateTime(timezone=True),
                           onupdate=func.now(),
                           server_default=func.now(),
                           comment='update_at')

    def get_type(self) -> TwoPcType:
        return TwoPcType.Value(self._two_pc_type)

    def set_type(self, t: TwoPcType):
        self._two_pc_type = TwoPcType.Name(t)

    def is_valid_action(self, action: TwoPcAction) -> bool:
        """Checks if the action is valid for current state or not."""
        possible_results = _VALID_TRANSITIONS.get(self.state, {}).get(action, None)
        return possible_results is not None

    def check_idempotent(self, current_action: TwoPcAction) -> Tuple[bool, Optional[bool], Optional[str]]:
        """Checks if the action executed and the result.

        Returns:
            (executed or not, result, message)
        """
        if self.state == TransactionState.INVALID:
            return True, False, self.message
        for current_state, actions in _VALID_TRANSITIONS.items():
            for action, results in actions.items():
                for result, new_state in results.items():
                    if new_state == self.state and action == current_action:
                        # Hits the history
                        return True, result, self.message
        return False, None, None

    def update(self, action: TwoPcAction, succeeded: bool, message: str) -> Tuple[bool, str]:
        new_state = _VALID_TRANSITIONS.get(self.state, {}).get(action, {}).get(succeeded, None)
        if new_state is None:
            self.message = f'[2pc] Invalid transition: [{self.state} - {action} - {succeeded}], extra: {message}'
            self.state = TransactionState.INVALID
            return False, self.message
        self.state = new_state
        self.message = message
        return succeeded, message
