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
from sqlalchemy.orm import Session

from fedlearner_webconsole.dataset.models import Dataset, DatasetJob
from fedlearner_webconsole.flag.models import Flag
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.proto.project_pb2 import ParticipantsInfo, ParticipantInfo


class AuthService(object):

    def __init__(self, session: Session, dataset_job: DatasetJob):
        self._session = session
        self._dataset_job = dataset_job
        self._output_dataset: Dataset = dataset_job.output_dataset

    def initialize_participants_info_as_coordinator(self, participants: List[Participant]):
        participants_info = ParticipantsInfo()
        for participant in participants:
            # default auth status is pending
            participant_info = ParticipantInfo(auth_status=AuthStatus.PENDING.value)
            participants_info.participants_map[participant.pure_domain_name()].CopyFrom(participant_info)

        coordinator_domain_name = SettingService.get_system_info().pure_domain_name
        coordinator_info = ParticipantInfo(auth_status=self._output_dataset.auth_status.name)
        participants_info.participants_map[coordinator_domain_name].CopyFrom(coordinator_info)

        self._output_dataset.set_participants_info(participants_info=participants_info)

    def initialize_participants_info_as_participant(self, participants_info: ParticipantsInfo):
        self._output_dataset.set_participants_info(participants_info=participants_info)

    def update_auth_status(self, domain_name: str, auth_status: AuthStatus):
        participants_info = self._output_dataset.get_participants_info()
        participants_info.participants_map[domain_name].auth_status = auth_status.name
        self._output_dataset.set_participants_info(participants_info=participants_info)

    def check_local_authorized(self) -> bool:
        if not Flag.DATASET_AUTH_STATUS_CHECK_ENABLED.value:
            return True
        return self._output_dataset.auth_status == AuthStatus.AUTHORIZED

    def check_participants_authorized(self) -> bool:
        if not Flag.DATASET_AUTH_STATUS_CHECK_ENABLED.value:
            return True
        return self._output_dataset.is_all_participants_authorized()
