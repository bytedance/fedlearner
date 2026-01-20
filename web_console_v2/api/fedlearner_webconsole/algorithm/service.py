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

import os
import tarfile
import tempfile
from io import FileIO
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from fedlearner_webconsole.exceptions import InvalidArgumentException
from fedlearner_webconsole.proto.filtering_pb2 import FilterOp, FilterExpression
from fedlearner_webconsole.utils.file_manager import FileManager
from fedlearner_webconsole.utils.file_operator import FileOperator
from fedlearner_webconsole.utils.filtering import SupportedField, FieldType, FilterBuilder
from fedlearner_webconsole.utils.resource_name import resource_uuid
from fedlearner_webconsole.algorithm.models import Algorithm, AlgorithmProject, Source, ReleaseStatus, PublishStatus, \
    PendingAlgorithm, AlgorithmType

# TODO(wangzeju): use singleton of file_manager or file_operator
file_manager = FileManager()
file_operator = FileOperator()


class AlgorithmProjectService:

    FILTER_FIELDS = {
        'name': SupportedField(type=FieldType.STRING, ops={FilterOp.CONTAIN: None}),
        'type': SupportedField(type=FieldType.STRING, ops={FilterOp.IN: None}),
    }

    def __init__(self, session: Session):
        self._session = session
        self._filter_builder = FilterBuilder(model_class=AlgorithmProject, supported_fields=self.FILTER_FIELDS)

    @staticmethod
    def _extract_to(file, path):
        with tempfile.TemporaryDirectory() as directory:
            with tarfile.open(fileobj=file) as tar:
                tar.extractall(directory)
                for root, _, files in os.walk(directory):
                    for name in files:
                        # There will be error files starting with '._' when the file is uploaded from the MacOS system
                        if name.startswith('._') or name.endswith('.pyc'):
                            os.remove(os.path.join(root, name))
            file_operator.copy_to(directory, path)

    def create_algorithm_project(self,
                                 name: str,
                                 project_id: int,
                                 algorithm_type: AlgorithmType,
                                 username: str,
                                 parameter,
                                 path: str,
                                 comment: Optional[str] = None,
                                 file: Optional[FileIO] = None) -> AlgorithmProject:
        if file is not None:
            self._extract_to(file, path)
        algo_project = AlgorithmProject(name=name,
                                        uuid=resource_uuid(),
                                        project_id=project_id,
                                        type=algorithm_type,
                                        source=Source.USER,
                                        username=username,
                                        path=path,
                                        comment=comment)
        algo_project.set_parameter(parameter)
        self._session.add(algo_project)
        self._session.flush()
        return algo_project

    def release_algorithm(self,
                          algorithm_project: AlgorithmProject,
                          username: str,
                          path: str,
                          participant_id: Optional[int] = None,
                          comment: Optional[str] = None):
        # apply exclusive lock on algorithm project to avoid race condition on algorithm version
        algo_project: AlgorithmProject = self._session.query(
            AlgorithmProject).populate_existing().with_for_update().get(algorithm_project.id)
        file_operator.copy_to(algorithm_project.path, path, create_dir=True)
        algo = Algorithm(name=algorithm_project.name,
                         type=algorithm_project.type,
                         parameter=algorithm_project.parameter,
                         path=path,
                         source=Source.USER,
                         username=username,
                         participant_id=participant_id,
                         project_id=algorithm_project.project_id,
                         algorithm_project_id=algorithm_project.id,
                         comment=comment)
        algo.uuid = resource_uuid()
        algo.version = algo_project.latest_version + 1
        algo_project.latest_version += 1
        algo_project.release_status = ReleaseStatus.RELEASED
        self._session.add(algo)
        return algo

    # TODO(linfan): implement delete file from file system
    def delete(self, algorithm_project: AlgorithmProject):
        algorithm_service = AlgorithmService(self._session)
        for algo in algorithm_project.algorithms:
            algorithm_service.delete(algo)
        self._session.delete(algorithm_project)

    def get_published_algorithm_projects(self, project_id: int,
                                         filter_exp: Optional[FilterExpression]) -> List[AlgorithmProject]:
        query = self._session.query(AlgorithmProject).filter_by(project_id=project_id,
                                                                publish_status=PublishStatus.PUBLISHED)
        try:
            query = self._filter_builder.build_query(query, filter_exp)
        except ValueError as e:
            raise InvalidArgumentException(details=f'Invalid filter: {str(e)}') from e
        return query.all()

    def get_published_algorithms_latest_update_time(self, algorithm_project_id: int) -> datetime:
        algo = self._session.query(Algorithm).filter_by(algorithm_project_id=algorithm_project_id,
                                                        publish_status=PublishStatus.PUBLISHED).order_by(
                                                            Algorithm.updated_at.desc()).limit(1).first()
        return algo.updated_at


class PendingAlgorithmService:

    def __init__(self, session: Session):
        self._session = session

    def create_algorithm_project(self,
                                 pending_algorithm: PendingAlgorithm,
                                 username: str,
                                 name: str,
                                 comment: Optional[str] = None) -> AlgorithmProject:
        algo_project = self._session.query(AlgorithmProject).filter(
            AlgorithmProject.name == name, AlgorithmProject.source == Source.THIRD_PARTY).first()
        if algo_project is not None:
            raise ValueError(f'there already exists algorithm project with name {name} from third party')
        algorithm_project = AlgorithmProject(name=name,
                                             project_id=pending_algorithm.project_id,
                                             latest_version=pending_algorithm.version,
                                             type=pending_algorithm.type,
                                             source=Source.THIRD_PARTY,
                                             username=username,
                                             participant_id=pending_algorithm.participant_id,
                                             comment=comment,
                                             uuid=pending_algorithm.algorithm_project_uuid,
                                             release_status=ReleaseStatus.RELEASED)
        algorithm_project.set_parameter(pending_algorithm.get_parameter())
        self._session.add(algorithm_project)
        return algorithm_project

    def create_algorithm(self,
                         pending_algorithm: PendingAlgorithm,
                         algorithm_project_id: int,
                         username: str,
                         path: str,
                         comment: Optional[str] = None) -> Algorithm:
        file_operator.copy_to(pending_algorithm.path, path, create_dir=True)
        algo = Algorithm(name=pending_algorithm.name,
                         type=pending_algorithm.type,
                         parameter=pending_algorithm.parameter,
                         path=path,
                         source=Source.THIRD_PARTY,
                         username=username,
                         participant_id=pending_algorithm.participant_id,
                         project_id=pending_algorithm.project_id,
                         algorithm_project_id=algorithm_project_id,
                         uuid=pending_algorithm.algorithm_uuid,
                         version=pending_algorithm.version,
                         comment=comment)
        self._session.add(algo)
        return algo


class AlgorithmService:

    def __init__(self, session: Session):
        self._session = session

    def _update_algorithm_project_publish_status(self, algorithm_project_id: int):
        algorithms = self._session.query(Algorithm).filter_by(algorithm_project_id=algorithm_project_id,
                                                              publish_status=PublishStatus.PUBLISHED).all()
        # There may be a race condition here. Only one Algorithm under the AlgorithmProject is published.
        # At this time, if an algorithm is published and an algorithm is unpublished or deleted at the same time,
        # there may be a "published" Algorithm under the AlgorithmProject, but the AlgorithmProject is
        # UNPUBLISHED. The user "Publish" or "Unpublish" the algorithm again, and it will be normal.
        if len(algorithms) == 0:
            algo_project = self._session.query(AlgorithmProject).get(algorithm_project_id)
            algo_project.publish_status = PublishStatus.UNPUBLISHED

    def _update_algorithm_project_release_status(self, algorithm_project_id: int):
        algorithms = self._session.query(Algorithm).filter_by(algorithm_project_id=algorithm_project_id).all()
        # There may be a race condition here too.
        if len(algorithms) == 0:
            algo_project = self._session.query(AlgorithmProject).get(algorithm_project_id)
            algo_project.release_status = ReleaseStatus.UNRELEASED

    def delete(self, algorithm: Algorithm):
        self._session.delete(algorithm)
        algo_project = self._session.query(AlgorithmProject).get(algorithm.algorithm_project_id)
        if algo_project.latest_version == algorithm.version:
            algo_project.release_status = ReleaseStatus.UNRELEASED
        self._update_algorithm_project_publish_status(algorithm_project_id=algorithm.algorithm_project_id)
        self._update_algorithm_project_release_status(algorithm_project_id=algorithm.algorithm_project_id)

    def publish_algorithm(self, algorithm_id: int, project_id: int) -> Algorithm:
        algorithm = self._session.query(Algorithm).filter_by(id=algorithm_id, project_id=project_id).first()
        algorithm.publish_status = PublishStatus.PUBLISHED
        algo_project = self._session.query(AlgorithmProject).get(algorithm.algorithm_project_id)
        algo_project.publish_status = PublishStatus.PUBLISHED
        return algorithm

    def unpublish_algorithm(self, algorithm_id: int, project_id: int) -> Algorithm:
        algorithm = self._session.query(Algorithm).filter_by(id=algorithm_id, project_id=project_id).first()
        algorithm.publish_status = PublishStatus.UNPUBLISHED
        self._update_algorithm_project_publish_status(algorithm_project_id=algorithm.algorithm_project_id)
        return algorithm

    def get_published_algorithms(self, project_id: int, algorithm_project_id: int) -> List[Algorithm]:
        return self._session.query(Algorithm).filter_by(project_id=project_id,
                                                        algorithm_project_id=algorithm_project_id,
                                                        publish_status=PublishStatus.PUBLISHED).all()
