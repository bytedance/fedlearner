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
from typing import Tuple

from sqlalchemy.orm import Session

from fedlearner_webconsole.proto.two_pc_pb2 import TwoPcType, TwoPcAction, TransactionData
from fedlearner_webconsole.two_pc.dataset_job_stage_launcher import DatasetJobStageLauncher
from fedlearner_webconsole.two_pc.dataset_job_stage_stopper import DatasetJobStageStopper
from fedlearner_webconsole.two_pc.model_job_creator import ModelJobCreator
from fedlearner_webconsole.two_pc.trusted_export_job_launcher import TrustedExportJobLauncher
from fedlearner_webconsole.two_pc.workflow_state_controller import WorkflowStateController
from fedlearner_webconsole.two_pc.model_job_group_creator import ModelJobGroupCreator
from fedlearner_webconsole.two_pc.model_job_launcher import ModelJobLauncher
from fedlearner_webconsole.two_pc.dataset_job_launcher import DatasetJobLauncher
from fedlearner_webconsole.two_pc.dataset_job_stopper import DatasetJobStopper
from fedlearner_webconsole.two_pc.trusted_job_group_creator import TrustedJobGroupCreator
from fedlearner_webconsole.two_pc.trusted_job_launcher import TrustedJobLauncher
from fedlearner_webconsole.two_pc.trusted_job_stopper import TrustedJobStopper
from fedlearner_webconsole.two_pc.models import Transaction, TransactionState


def run_two_pc_action(session: Session, tid: str, two_pc_type: TwoPcType, action: TwoPcAction,
                      data: TransactionData) -> Tuple[bool, str]:
    # Checks idempotent
    trans = session.query(Transaction).filter_by(uuid=tid).first()
    if trans is None:
        trans = Transaction(
            uuid=tid,
            state=TransactionState.NEW,
        )
        trans.set_type(two_pc_type)
        session.add(trans)
    executed, result, message = trans.check_idempotent(action)
    if executed:
        return result, message

    rm = None
    if two_pc_type == TwoPcType.CREATE_MODEL_JOB:
        rm = ModelJobCreator(session=session, tid=tid, data=data)
    elif two_pc_type == TwoPcType.CONTROL_WORKFLOW_STATE:
        rm = WorkflowStateController(session=session, tid=tid, data=data)
    elif two_pc_type == TwoPcType.CREATE_MODEL_JOB_GROUP:
        rm = ModelJobGroupCreator(session=session, tid=tid, data=data)
    elif two_pc_type == TwoPcType.LAUNCH_MODEL_JOB:
        rm = ModelJobLauncher(session=session, tid=tid, data=data)
    elif two_pc_type == TwoPcType.LAUNCH_DATASET_JOB:
        rm = DatasetJobLauncher(session=session, tid=tid, data=data)
    elif two_pc_type == TwoPcType.STOP_DATASET_JOB:
        rm = DatasetJobStopper(session=session, tid=tid, data=data)
    elif two_pc_type == TwoPcType.CREATE_TRUSTED_JOB_GROUP:
        rm = TrustedJobGroupCreator(session=session, tid=tid, data=data)
    elif two_pc_type == TwoPcType.LAUNCH_TRUSTED_JOB:
        rm = TrustedJobLauncher(session=session, tid=tid, data=data)
    elif two_pc_type == TwoPcType.STOP_TRUSTED_JOB:
        rm = TrustedJobStopper(session=session, tid=tid, data=data)
    elif two_pc_type == TwoPcType.LAUNCH_TRUSTED_EXPORT_JOB:
        rm = TrustedExportJobLauncher(session=session, tid=tid, data=data)
    elif two_pc_type == TwoPcType.LAUNCH_DATASET_JOB_STAGE:
        rm = DatasetJobStageLauncher(session=session, tid=tid, data=data)
    elif two_pc_type == TwoPcType.STOP_DATASET_JOB_STAGE:
        rm = DatasetJobStageStopper(session=session, tid=tid, data=data)
    if rm is None:
        raise NotImplementedError()

    succeeded = False
    try:
        if trans.is_valid_action(action):
            succeeded, message = rm.run_two_pc(action)
    except Exception as e:  # pylint: disable=broad-except
        message = str(e)
    return trans.update(action, succeeded, message)
