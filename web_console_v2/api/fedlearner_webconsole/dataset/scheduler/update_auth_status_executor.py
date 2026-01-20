# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from typing import List
from sqlalchemy import or_

from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.controllers import DatasetJobController
from fedlearner_webconsole.dataset.services import DatasetService
from fedlearner_webconsole.dataset.scheduler.base_executor import BaseExecutor
from fedlearner_webconsole.dataset.scheduler.consts import ExecutorResult
from fedlearner_webconsole.dataset.models import DATASET_JOB_FINISHED_STATE, Dataset, DatasetJob, \
    DatasetJobSchedulerState


class UpdateAuthStatusExecutor(BaseExecutor):

    def get_item_ids(self) -> List[int]:
        with db.session_scope() as session:
            datasets = DatasetService(session=session).query_dataset_with_parent_job().filter(
                Dataset.participants_info.isnot(None)).filter(
                    or_(DatasetJob.state.not_in(DATASET_JOB_FINISHED_STATE),
                        DatasetJob.scheduler_state != DatasetJobSchedulerState.STOPPED)).all()
        return [dataset.id for dataset in datasets]

    def run_item(self, item_id: int) -> ExecutorResult:
        with db.session_scope() as session:
            dataset: Dataset = session.query(Dataset).get(item_id)
            # if all participants cache are authorized, just skip
            if dataset.is_all_participants_authorized():
                return ExecutorResult.SKIP
            DatasetJobController(session=session).update_auth_status_cache(dataset_job=dataset.parent_dataset_job)
            session.commit()
        return ExecutorResult.SUCCEEDED
