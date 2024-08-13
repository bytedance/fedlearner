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

import grpc
from envs import Envs
from fedlearner_webconsole.algorithm.models import Algorithm, Source
from fedlearner_webconsole.algorithm.utils import algorithm_cache_path
from fedlearner_webconsole.algorithm.utils import check_algorithm_file
from fedlearner_webconsole.algorithm.transmit.receiver import AlgorithmReceiver
from fedlearner_webconsole.db import db
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.proto.algorithm_pb2 import AlgorithmPb
from fedlearner_webconsole.rpc.v2.resource_service_client import ResourceServiceClient
from fedlearner_webconsole.utils.file_manager import file_manager
from fedlearner_webconsole.exceptions import NotFoundException


class AlgorithmFetcher:

    def __init__(self, project_id: int):
        self._project_id = project_id

    def get_algorithm_from_participant(self, algorithm_uuid: str, participant_id: int) -> AlgorithmPb:
        with db.session_scope() as session:
            project = session.query(Project).get(self._project_id)
            participant = session.query(Participant).get(participant_id)
        client = ResourceServiceClient.from_project_and_participant(participant.domain_name, project.name)
        algorithm = client.get_algorithm(algorithm_uuid=algorithm_uuid)
        algo_cache_path = algorithm_cache_path(Envs.STORAGE_ROOT, algorithm_uuid)
        if not file_manager.exists(algo_cache_path):
            data_iterator = client.get_algorithm_files(algorithm_uuid=algorithm_uuid)
            # Get the hash in the first response to be used for verification when the file is received
            resp = next(data_iterator)
            with check_algorithm_file(algo_cache_path):
                AlgorithmReceiver().write_data_and_extract(data_iterator, algo_cache_path, resp.hash)
        algorithm.path = algo_cache_path
        algorithm.source = Source.PARTICIPANT.name
        algorithm.participant_id = participant_id
        return algorithm

    def get_algorithm(self, uuid: str) -> AlgorithmPb:
        """Raise NotFoundException when the algorithm is not found"""

        with db.session_scope() as session:
            algorithm = session.query(Algorithm).filter_by(uuid=uuid).first()
            participants = session.query(Project).get(self._project_id).participants
            if algorithm:
                return algorithm.to_proto()
        for participant in participants:
            try:
                return self.get_algorithm_from_participant(algorithm_uuid=uuid, participant_id=participant.id)
            except grpc.RpcError:
                continue
        raise NotFoundException(f'the algorithm uuid: {uuid} is not found')
