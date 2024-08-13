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

import argparse
import logging

import sys
from sqlalchemy import or_
from sqlalchemy.orm import Session

from fedlearner_webconsole.dataset.models import Dataset
from fedlearner_webconsole.db import db
from fedlearner_webconsole.job.models import Job, JobDependency
from fedlearner_webconsole.mmgr.models import Model, ModelJob, ModelJobGroup
from fedlearner_webconsole.participant.models import ProjectParticipant
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.serving.models import ServingModel, ServingDeployment, ServingNegotiator
from fedlearner_webconsole.workflow.models import Workflow


class _ProjectCleaner(object):

    def __init__(self, session: Session, project_id: int):
        self._session = session
        self.project_id = project_id

    def _delete_rows(self, model: db.Model):
        count = self._session.query(model).filter_by(project_id=self.project_id).delete()
        logging.info(f'Deleted {count} rows from {model.__tablename__}')

    def _delete_datasets(self):
        datasets = self._session.query(Dataset).filter_by(project_id=self.project_id).all()
        dataset_count = 0
        for dataset in datasets:
            batch_count = 0
            for batch in dataset.data_batches:
                self._session.delete(batch)
                batch_count += 1
            logging.info(f'Deleted {batch_count} batches for dataset {dataset.id}')
            if dataset.parent_dataset_job:
                dataset_job_id = dataset.parent_dataset_job.id
                self._session.delete(dataset.parent_dataset_job)
                logging.info(f'Deleted dataset job {dataset_job_id} for dataset {dataset.id}')
            self._session.delete(dataset)
            dataset_count += 1
        logging.info(f'Deleted {dataset_count} rows from {Dataset.__tablename__}')

    def _delete_workflows(self):
        jobs = self._session.query(Job).filter_by(project_id=self.project_id).all()
        job_count = 0
        for job in jobs:
            job_deps = self._session.query(JobDependency).filter(
                or_(JobDependency.src_job_id == job.id, JobDependency.dst_job_id == job.id)).all()
            job_dep_count = 0
            for job_dep in job_deps:
                self._session.delete(job_dep)
                job_dep_count += 1
            logging.info(f'Deleted {job_dep_count} job deps for job {job.id}')
            self._session.delete(job)
            job_count += 1
        logging.info(f'Deleted {job_count} rows from {Job.__tablename__}')
        self._delete_rows(Workflow)

    def run(self):
        # Cleans up model
        self._delete_rows(ModelJob)
        self._delete_rows(Model)
        self._delete_rows(ModelJobGroup)
        # TODO(hangweiqiang): cleans up algorithm
        # Cleans up serving related stuff
        self._delete_rows(ServingModel)
        self._delete_rows(ServingDeployment)
        self._delete_rows(ServingNegotiator)
        # Cleans up dataset
        self._delete_datasets()
        # Cleans up workflow
        self._delete_workflows()
        # Cleans up participant
        self._delete_rows(ProjectParticipant)
        # Deletes project
        count = self._session.query(Project).filter_by(id=self.project_id).delete()
        logging.info(f'Deleted {count} rows from {Project.__tablename__}')


def delete_project(project_id: int):
    """Deletes project and related resources' metadata.

    TODO(linfan.fine): cleans up resources on the disk."""
    with db.session_scope() as session:
        project = session.query(Project).get(project_id)
        project_name = project.name if project is not None else '[NOT EXISTING]'
        print(f'You are deleting project (id: {project_id} - name: {project_name}), y/n?')
        confirm = input()
        if confirm not in ['y', 'Y', 'yes', 'YES', 'yes']:
            return
        _ProjectCleaner(session, project_id).run()
        session.commit()
        logging.info(f'Project {project_id} cleaned up')


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    parser = argparse.ArgumentParser(description='Project cleanup')
    parser.add_argument('--project_id', type=int, required=True, help='Project needs to be cleaned up')
    args = parser.parse_args()
    delete_project(args.project_id)
