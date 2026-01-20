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
from typing import List, Optional
from fedlearner_webconsole.auth.models import Session
from fedlearner_webconsole.participant.models import ProjectParticipant, Participant, ParticipantType


class ParticipantService(object):

    def __init__(self, session: Session):
        self._session = session

    def get_participant_by_pure_domain_name(self, pure_domain_name: str) -> Optional[Participant]:
        """Finds a specific participant by pure domain name, e.g. aliyun-test.

        For compatible reason, we have two kinds of domain name, fl-xxx.com and xxx.fedlearner.net,
        so we need to identify a participant by pure domain name globally."""
        participants = self._session.query(Participant).filter(
            Participant.domain_name.like(f'%{pure_domain_name}%')).all()
        for p in participants:
            if p.pure_domain_name() == pure_domain_name:
                return p
        return None

    def get_participants_by_project(self, project_id: int) -> List:
        # the precision of datetime cannot suffice, use id instead
        participants = self._session.query(Participant).join(
            ProjectParticipant, ProjectParticipant.participant_id == Participant.id).filter(
            ProjectParticipant.project_id == project_id). \
            order_by(Participant.created_at.desc()).all()
        return participants

    # get only platform participant, ignore light-client type participant
    def get_platform_participants_by_project(self, project_id: int) -> List:
        participants = self.get_participants_by_project(project_id)
        platform_participants = []
        for participant in participants:
            # a hack that previous participant_type is null
            if participant.get_type() == ParticipantType.PLATFORM:
                platform_participants.append(participant)
        return platform_participants

    def get_number_of_projects(self, participant_id: int) -> int:
        return self._session.query(ProjectParticipant).filter_by(participant_id=participant_id).count()

    def create_light_client_participant(self,
                                        name: str,
                                        domain_name: str,
                                        comment: Optional[str] = None) -> Participant:
        participant = Participant(name=name,
                                  domain_name=domain_name,
                                  type=ParticipantType.LIGHT_CLIENT,
                                  comment=comment)
        self._session.add(participant)
        return participant

    def create_platform_participant(self,
                                    name: str,
                                    domain_name: str,
                                    host: str,
                                    port: int,
                                    extra: dict,
                                    comment: Optional[str] = None) -> Participant:
        participant = Participant(name=name,
                                  domain_name=domain_name,
                                  host=host,
                                  port=port,
                                  type=ParticipantType.PLATFORM,
                                  comment=comment)
        participant.set_extra_info(extra)
        self._session.add(participant)
        return participant
