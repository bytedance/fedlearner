# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
from http import HTTPStatus
from typing import Optional
from flask_restful import Api, Resource
from webargs import fields, validate
from google.protobuf.json_format import MessageToDict

from fedlearner_webconsole.audit.decorators import emits_event
from fedlearner_webconsole.db import db
from fedlearner_webconsole.exceptions import InvalidArgumentException, ResourceConflictException, \
    NotFoundException, MethodNotAllowedException
from fedlearner_webconsole.participant.k8s_utils import get_host_and_port, get_valid_candidates, \
    create_or_update_participant_in_k8s
from fedlearner_webconsole.participant.models import Participant, ParticipantType
from fedlearner_webconsole.participant.services import ParticipantService
from fedlearner_webconsole.proto.common_pb2 import StatusCode
from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.utils.decorators.pp_flask import use_kwargs, input_validator, admin_required
from fedlearner_webconsole.auth.third_party_sso import credentials_required
from fedlearner_webconsole.utils.flask_utils import make_flask_response
from fedlearner_webconsole.rpc.v2.system_service_client import SystemServiceClient


def _get_empty_message_hint(field: str) -> str:
    return f'{field} should not be empty'


def _create_participant_in_k8s(domain_name: str, host: str, port: int, namespace: str):
    # crete manually must have all the arguments
    if host is None or port is None:
        raise InvalidArgumentException('Do not have host or port.')
    # create ingress and service
    # TODO(taoyanting)：validate url
    create_or_update_participant_in_k8s(domain_name=domain_name, host=host, port=port, namespace=namespace)


class ParticipantsApi(Resource):

    @credentials_required
    def get(self):
        """Get all participant information ordered by `created_by`.
        ---
        tags:
          - participant
        description: Get all participant information ordered by `created_by`.
        responses:
          200:
            description: list of paritcipant
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.Participant'
        """
        with db.session_scope() as session:
            participants = session.query(Participant). \
                order_by(Participant.created_at.desc()).all()
            participant_service = ParticipantService(session)
            protos = []
            for participant in participants:
                # A trade-off to join project counts with participants
                proto = participant.to_proto()
                proto.num_project = participant_service.get_number_of_projects(participant.id)
                protos.append(proto)
            return make_flask_response(data=protos)

    # TODO(taoyanting): refactor this api
    @input_validator
    @credentials_required
    @emits_event(audit_fields=['is_manual_configured', 'type'])
    @use_kwargs({
        'name':
            fields.Str(required=True),
        'domain_name':
            fields.Str(required=True),
        'is_manual_configured':
            fields.Bool(required=False, load_default=False),
        'type':
            fields.Str(required=False,
                       load_default=ParticipantType.PLATFORM.name,
                       validate=validate.OneOf([t.name for t in ParticipantType])),
        'host':
            fields.Str(required=False, load_default=None),
        'port':
            fields.Integer(required=False, load_default=None),
        'comment':
            fields.Str(required=False, load_default=None),
    })
    def post(
            self,
            name: str,
            domain_name: str,
            is_manual_configured: bool,
            type: Optional[str],  # pylint: disable=redefined-builtin
            host: Optional[str],
            port: Optional[int],
            comment: Optional[str]):
        """Create new participant
        ---
        tags:
          - participant
        description: Create new participant
        requestBody:
          required: true
          content:
            application/json:
              schema:
                type: object
                properties:
                  name:
                    type: string
                  domain_name:
                    type: string
                  is_manual_configured:
                    type: boolean
                  type:
                    type: string
                  host:
                    type: string
                  port:
                    type: integer
                  comment:
                    type: string
        responses:
          200:
            description: Participant that you created.
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.Participant'
        """

        extra = {}
        extra['is_manual_configured'] = is_manual_configured
        participant_type = ParticipantType[type]

        with db.session_scope() as session:
            if session.query(Participant). \
                    filter_by(domain_name=domain_name).first() is not None:
                raise ResourceConflictException(message='Participant domain name has been used')
            service = ParticipantService(session)
            if participant_type == ParticipantType.LIGHT_CLIENT:
                participant = service.create_light_client_participant(name, domain_name, comment)
            else:
                if is_manual_configured:
                    namespace = SettingService(session).get_namespace()
                    _create_participant_in_k8s(domain_name, host, port, namespace)
                else:
                    host, port = get_host_and_port(domain_name)
                participant = service.create_platform_participant(name, domain_name, host, port, extra, comment)
            try:
                session.commit()
            except Exception as e:
                raise InvalidArgumentException(details=str(e)) from e
            return make_flask_response(data=participant.to_proto(), status=HTTPStatus.CREATED)


class ParticipantApi(Resource):

    @credentials_required
    def get(self, participant_id: int):
        """Get details of particiapnt
        ---
        tags:
          - participant
        description: Get details of particiapnt
        parameters:
        - in: path
          name: participant_id
          schema:
            type: integer
        responses:
          200:
            description: the specified participant
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.Participant'
        """
        with db.session_scope() as session:
            participant = session.query(Participant).filter_by(id=participant_id).first()
            if participant is None:
                raise NotFoundException(f'Failed to find participant: {participant_id}')
            return make_flask_response(data=participant.to_proto())

    @credentials_required
    @input_validator
    @emits_event()
    @use_kwargs({
        'name': fields.Str(required=False, load_default=None),
        'domain_name': fields.Str(required=False, load_default=None),
        'host': fields.Str(required=False, load_default=None),
        'port': fields.Integer(required=False, load_default=None),
        'comment': fields.Str(required=False, load_default=None),
    })
    def patch(self, participant_id: int, name: Optional[str], domain_name: Optional[str], host: Optional[str],
              port: Optional[int], comment: Optional[str]):
        """Partial update the given participant
        ---
        tags:
          - participant
        description: Partial update the given participant
        parameters:
        - in: path
          name: participant_id
          schema:
            type: integer
        requestBody:
          required: true
          content:
            application/json:
              schema:
                type: object
                properties:
                  name:
                    type: string
                  domain_name:
                    type: string
                  host:
                    type: string
                  port:
                    type: integer
                  comment:
                    type: string
        responses:
          200:
            description: the updated participant
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.Participant'
        """
        with db.session_scope() as session:
            participant: Participant = session.query(Participant).filter_by(id=participant_id).first()
            if participant is None:
                raise NotFoundException(f'Failed to find participant: {participant_id}')

            participant.name = name or participant.name
            participant.comment = comment or participant.comment

            if domain_name is not None and domain_name != participant.domain_name:
                if session.query(Participant).filter_by(domain_name=domain_name).first() is not None:
                    raise ResourceConflictException(message='Participant domain name has been used')
                participant.domain_name = domain_name
            if participant.type == ParticipantType.PLATFORM:
                extra = participant.get_extra_info()
                if extra['is_manual_configured']:
                    if domain_name or host or port:
                        participant.host = host or participant.host
                        participant.port = port or participant.port

                        # TODO(taoyanting)：validate url
                        try:
                            namespace = SettingService(session).get_namespace()
                            create_or_update_participant_in_k8s(domain_name=participant.domain_name,
                                                                host=participant.host,
                                                                port=participant.port,
                                                                namespace=namespace)
                        except Exception as e:
                            raise InvalidArgumentException(details=str(e)) from e
                elif domain_name is not None:
                    host, port = get_host_and_port(participant.domain_name)
                    participant.host = host
                    participant.port = port
                participant.set_extra_info(extra)
            try:
                session.commit()
                return make_flask_response(data=participant.to_proto())
            except Exception as e:
                raise InvalidArgumentException(details=e) from e

    @credentials_required
    @admin_required
    @emits_event()
    def delete(self, participant_id):
        """Delete a participant
        ---
        tags:
          - participant
        description: Delete a participant
        parameters:
        - in: path
          name: participant_id
          schema:
            type: integer
        responses:
          204:
            description: Deleted successfully
        """
        with db.session_scope() as session:
            participant = session.query(Participant).filter_by(id=participant_id).first()
            if participant is None:
                raise NotFoundException(f'Failed to find participant: {participant_id}')

            service = ParticipantService(session)
            num_project = service.get_number_of_projects(participant_id)
            if num_project != 0:
                raise MethodNotAllowedException(f'Failed to delete participant: {participant_id}, '
                                                f'because it has related projects')
            session.delete(participant)
            session.commit()
        return make_flask_response(status=HTTPStatus.NO_CONTENT)


class ParticipantConnectionChecksApi(Resource):

    @credentials_required
    def get(self, participant_id: int):
        """Check participant connection status
        ---
        tags:
          - participant
        description: Check participant connection status
        parameters:
        - in: path
          name: participant_id
          schema:
            type: integer
        responses:
          200:
            description: connection status
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    success:
                      type: boolean
                    message:
                      type: string
                    application_version:
                      $ref: '#/definitions/proto.ApplicationVersion'
        """
        with db.session_scope() as session:
            participant = session.query(Participant).filter_by(id=participant_id).first()
            if participant is None:
                raise NotFoundException(f'Failed to find participant: {participant_id}')

        client = RpcClient.from_participant(participant.domain_name)
        result = client.check_peer_connection()
        version = {}
        if result.status.code == StatusCode.STATUS_SUCCESS:
            version = MessageToDict(result.application_version, preserving_proto_field_name=True)
        return make_flask_response({
            'success': result.status.code == StatusCode.STATUS_SUCCESS,
            'message': result.status.msg,
            'application_version': version
        })


class ParticipantCandidatesApi(Resource):

    @credentials_required
    @admin_required
    def get(self):
        """Get candidate participant according to kueburnetes resource.
        ---
        tags:
          - participant
        description: Get candidate participant according to kueburnetes resource.
        responses:
          200:
            description:
            content:
              application/json:
                schema:
                  type: array
                  items:
                    type: object
                    properties:
                      domain_name:
                        type: string
        """
        return make_flask_response(get_valid_candidates())


class ParticipantFlagsApi(Resource):

    def get(self, participant_id: int):
        """Get flags from participant
        ---
        tags:
          - flag
        responses:
          200:
            description: Participant's flags are returned
            content:
              application/json:
                schema:
                  type: object
                  additionalProperties: true
                  example:
                    FLAG_1: string_value
                    FLAG_2: true
                    FLAG_3: 1
        """
        with db.session_scope() as session:
            participant: Participant = session.query(Participant).get(participant_id)
            if participant is None:
                raise NotFoundException(f'Failed to find participant: {participant_id}')
            client = SystemServiceClient.from_participant(domain_name=participant.domain_name)
        return make_flask_response(data=client.list_flags())


def initialize_participant_apis(api: Api):
    api.add_resource(ParticipantsApi, '/participants')
    api.add_resource(ParticipantApi, '/participants/<int:participant_id>')
    api.add_resource(ParticipantConnectionChecksApi, '/participants/<int:participant_id>/connection_checks')
    api.add_resource(ParticipantCandidatesApi, '/participant_candidates')
    api.add_resource(ParticipantFlagsApi, '/participants/<int:participant_id>/flags')
