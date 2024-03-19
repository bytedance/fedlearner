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

import logging

from fedlearner_webconsole.db import db
from fedlearner_webconsole.dataset.models import DatasetJob


def migrate_dataset_job_name():
    logging.info('[migration]: start to migrate dataset_job name from result dataset name')
    with db.session_scope() as session:
        dataset_job_ids = session.query(DatasetJob.id).filter(DatasetJob.name.is_(None)).all()
        logging.info(f'[migration]: {len(dataset_job_ids)} dataset_jobs need to migrate name')
    failed_ids = []
    for dataset_job_id in dataset_job_ids:
        try:
            with db.session_scope() as session:
                dataset_job: DatasetJob = session.query(DatasetJob).get(dataset_job_id)
                dataset_job.name = dataset_job.output_dataset.name
                session.commit()
        except Exception as e:  # pylint: disable=broad-except
            failed_ids.append(dataset_job_id)
            logging.error(f'[migration]: migrate dataset_job {dataset_job_id} failed: {str(e)}')
    if failed_ids:
        logging.error(f'[migration]: {failed_ids} failed')
    logging.info('[migration]: finish dataset_job name migration')
