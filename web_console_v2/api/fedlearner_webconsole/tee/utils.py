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

from urllib.parse import urlparse
from sqlalchemy.orm import Session
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.dataset.models import Dataset
from fedlearner_webconsole.algorithm.models import Algorithm
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.exceptions import InvalidArgumentException, NotFoundException
from fedlearner_webconsole.tee.models import TrustedJobGroup, TrustedJob
from fedlearner_webconsole.proto.algorithm_pb2 import AlgorithmPb
from fedlearner_webconsole.algorithm.fetcher import AlgorithmFetcher


def get_project(session: Session, project_id: int) -> Project:
    project = session.query(Project).get(project_id)
    if project is None:
        raise InvalidArgumentException(f'project {project_id} is not found')
    return project


def get_dataset(session: Session, dataset_id: int) -> Dataset:
    dataset = session.query(Dataset).get(dataset_id)
    if dataset is None:
        raise InvalidArgumentException(f'dataset {dataset_id} is not found')
    return dataset


def get_algorithm(session: Session, algorithm_id: int) -> Algorithm:
    algorithm = session.query(Algorithm).get(algorithm_id)
    if algorithm is None:
        raise InvalidArgumentException(f'algorithm {algorithm_id} is not found')
    return algorithm


def get_participant(session: Session, participant_id: int) -> Participant:
    participant = session.query(Participant).get(participant_id)
    if participant is None:
        raise InvalidArgumentException(f'participant {participant_id} is not found')
    return participant


def get_trusted_job_group(session: Session, project_id: int, group_id: int) -> TrustedJobGroup:
    group = session.query(TrustedJobGroup).filter_by(id=group_id, project_id=project_id).first()
    if group is None:
        raise NotFoundException(f'trusted job group {group_id} is not found')
    return group


def get_trusted_job(session: Session, project_id: int, trusted_job_id: int) -> TrustedJob:
    trusted_job = session.query(TrustedJob).filter_by(id=trusted_job_id, project_id=project_id).first()
    if trusted_job is None:
        raise NotFoundException(f'trusted job {trusted_job_id} is not found')
    return trusted_job


def get_algorithm_with_uuid(project_id: int, algorithm_uuid: str) -> AlgorithmPb:
    try:
        return AlgorithmFetcher(project_id).get_algorithm(algorithm_uuid)
    except NotFoundException as e:
        raise InvalidArgumentException(f'algorithm {algorithm_uuid} is not found') from e


def get_pure_path(path: str) -> str:
    return urlparse(path).path
