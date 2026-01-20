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

from sqlalchemy import or_
from fedlearner_webconsole.mmgr.models import ModelJob
from fedlearner_webconsole.workflow.models import WorkflowExternalState
from fedlearner_webconsole.dataset.models import Dataset, DatasetJobSchedulerState, ResourceState, DatasetJob
from typing import List, Tuple


class DatasetDeleteDependency(object):

    def __init__(self, session) -> None:
        self._session = session
        self._check_pipeline = [self._check_model_jobs, self._check_dataset, self._check_dataset_jobs]

    def is_deletable(self, dataset: Dataset) -> Tuple[bool, List[str]]:
        # warning: No lock on modelJob table
        # TODO(wangzeju): Ensure correct check results when concurrently modifying modelJob
        is_deletable, msg = True, []
        for check_func in self._check_pipeline:
            result = check_func(dataset=dataset)
            is_deletable, msg = is_deletable & result[0], msg + result[1]
        return is_deletable, msg

    def _check_model_jobs(self, dataset: Dataset) -> Tuple[bool, List[str]]:
        dataset_id = dataset.id
        is_deletable, msg = True, []
        model_jobs: List[ModelJob] = self._session.query(ModelJob).filter_by(dataset_id=dataset_id).all()
        for model_job in model_jobs:
            state = model_job.state
            if state not in [
                    WorkflowExternalState.COMPLETED, WorkflowExternalState.FAILED, WorkflowExternalState.STOPPED,
                    WorkflowExternalState.INVALID
            ]:
                is_deletable, msg = False, msg + [f'The Model Job: {model_job.name} is using this dataset']
        return is_deletable, msg

    def _check_dataset_jobs(self, dataset: Dataset) -> Tuple[bool, List[str]]:
        is_deletable, msg = True, []
        dataset_jobs = self._session.query(DatasetJob).filter(DatasetJob.input_dataset_id == dataset.id).all()
        for dataset_job in dataset_jobs:
            if not dataset_job.is_finished():
                is_deletable, msg = False, msg + [
                    f'dependent dataset_job is not finished, dataset_job_id: {dataset_job.id}'
                ]
        cron_dataset_jobs = self._session.query(DatasetJob).filter(
            or_(DatasetJob.input_dataset_id == dataset.id, DatasetJob.output_dataset_id == dataset.id)).filter(
                DatasetJob.scheduler_state == DatasetJobSchedulerState.RUNNABLE).all()
        if cron_dataset_jobs:
            is_deletable, msg = False, msg + [
                'dependent cron dataset_job is still runnable, plz stop scheduler first! ' \
                f'dataset_jobs_id: {[cron_dataset_job.id for cron_dataset_job in cron_dataset_jobs]}'
            ]
        return is_deletable, msg

    def _check_dataset(self, dataset: Dataset) -> Tuple[bool, List[str]]:
        if not dataset.get_frontend_state() in [ResourceState.SUCCEEDED, ResourceState.FAILED]:
            return False, [f'The dataset {dataset.name} is being processed']
        return True, []
