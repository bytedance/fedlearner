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
from typing import Optional
from flask_restful import Resource
from http import HTTPStatus
from marshmallow import Schema, fields, post_load, validate
from webargs.flaskparser import use_kwargs
from google.protobuf.json_format import ParseDict
from fedlearner_webconsole.db import db
from fedlearner_webconsole.review.ticket_helper import get_ticket_helper
from fedlearner_webconsole.utils.decorators.pp_flask import input_validator
from fedlearner_webconsole.utils.flask_utils import make_flask_response, FilterExpField, get_current_user
from fedlearner_webconsole.utils.filtering import SupportedField, FieldType, FilterBuilder
from fedlearner_webconsole.utils.paginate import paginate
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.auth.third_party_sso import credentials_required
from fedlearner_webconsole.audit.decorators import emits_event
from fedlearner_webconsole.proto.audit_pb2 import Event
from fedlearner_webconsole.proto.filtering_pb2 import FilterExpression, FilterOp
from fedlearner_webconsole.proto.review_pb2 import TicketType, TicketDetails
from fedlearner_webconsole.exceptions import ResourceConflictException, InvalidArgumentException, NoAccessException, \
    InternalException, NotFoundException
from fedlearner_webconsole.tee.models import TrustedJobGroup, GroupCreateStatus, TrustedJob, \
    TrustedJobStatus, TrustedJobType
from fedlearner_webconsole.tee.controller import TrustedJobGroupController, launch_trusted_job, stop_trusted_job, \
    get_tee_enabled_participants, TrustedJobController
from fedlearner_webconsole.tee.services import TrustedJobGroupService, TrustedJobService
from fedlearner_webconsole.tee.utils import get_project, get_algorithm, get_dataset, get_participant, \
    get_trusted_job_group, get_trusted_job, get_algorithm_with_uuid
from fedlearner_webconsole.proto.tee_pb2 import Resource as ResourcePb, ParticipantDatasetList
from fedlearner_webconsole.swagger.models import schema_manager
from fedlearner_webconsole.utils.resource_name import resource_uuid
from fedlearner_webconsole.flag.models import Flag
from fedlearner_webconsole.participant.services import ParticipantService
from fedlearner_webconsole.algorithm.models import AlgorithmType
from fedlearner_webconsole.algorithm.fetcher import AlgorithmFetcher


class ParticipantDatasetParams(Schema):
    participant_id = fields.Integer(required=True)
    uuid = fields.Str(required=True)
    name = fields.Str(required=True)


class ResourceParams(Schema):
    cpu = fields.Integer(required=True)
    memory = fields.Integer(required=True)
    replicas = fields.Integer(required=True)


class CreateTrustedJobGroupParams(Schema):
    name = fields.Str(required=True)
    comment = fields.Str(required=False, load_default=None)
    # TODO(liuledian): remove algorithm_id after frontend completed
    algorithm_id = fields.Integer(required=False, load_default=None)
    algorithm_uuid = fields.Str(required=False, load_default=None)
    dataset_id = fields.Integer(required=False, load_default=None)
    participant_datasets = fields.List(fields.Nested(ParticipantDatasetParams), required=False, load_default=None)
    resource = fields.Nested(ResourceParams, required=True)

    @post_load()
    def make(self, data, **kwargs):
        data['resource'] = ParseDict(data['resource'], ResourcePb())
        data['participant_datasets'] = ParseDict({'items': data['participant_datasets']}, ParticipantDatasetList())
        return data


class ConfigTrustedJobGroupParams(Schema):
    comment = fields.Str(required=False, load_default=None)
    auth_status = fields.Str(required=False,
                             load_default=None,
                             validate=validate.OneOf([AuthStatus.PENDING.name, AuthStatus.AUTHORIZED.name]))
    # TODO(liuledian): remove algorithm_id after frontend completed
    algorithm_id = fields.Integer(required=False, load_default=None)
    algorithm_uuid = fields.Str(required=False, load_default=None)
    resource = fields.Nested(ResourceParams, required=False, load_default=None)

    @post_load()
    def make(self, data, **kwargs):
        if data['resource'] is not None:
            data['resource'] = ParseDict(data['resource'], ResourcePb())
        if data['auth_status'] is not None:
            data['auth_status'] = AuthStatus[data['auth_status']]
        return data


class TrustedJobGroupsApi(Resource):

    FILTER_FIELDS = {
        'name': SupportedField(type=FieldType.STRING, ops={FilterOp.CONTAIN: None}),
    }

    def __init__(self):
        self._filter_builder = FilterBuilder(model_class=TrustedJobGroup, supported_fields=self.FILTER_FIELDS)

    @credentials_required
    @use_kwargs(
        {
            'page': fields.Integer(required=False, load_default=None),
            'page_size': fields.Integer(required=False, load_default=None),
            'filter_exp': FilterExpField(data_key='filter', required=False, load_default=None),
        },
        location='query')
    def get(
        self,
        page: Optional[int],
        page_size: Optional[int],
        filter_exp: Optional[FilterExpression],
        project_id: int,
    ):
        """Get the list of trusted job groups
        ---
        tags:
          - tee
        description: get the list of trusted job groups
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        - in: query
          name: page
          schema:
            type: integer
        - in: query
          name: page_size
          schema:
            type: integer
        - in: query
          name: filter
          schema:
            type: string
        responses:
          200:
            description: the list of trusted job groups
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.TrustedJobGroupRef'
          400:
            description: invalid argument
          403:
            description: the trusted job group is forbidden to access
        """
        if not Flag.TRUSTED_COMPUTING_ENABLED.value:
            raise NoAccessException('trusted computing is not enabled')
        with db.session_scope() as session:
            # TODO(liuledian): filter out groups in notification
            query = session.query(TrustedJobGroup).filter(TrustedJobGroup.resource.isnot(None)).order_by(
                TrustedJobGroup.created_at.desc())
            if project_id:
                query = query.filter_by(project_id=project_id)
            if filter_exp:
                try:
                    query = self._filter_builder.build_query(query, filter_exp)
                except ValueError as e:
                    raise InvalidArgumentException(details=f'Invalid filter: {str(e)}') from e
            pagination = paginate(query, page, page_size)
            data = [d.to_ref() for d in pagination.get_items()]
            session.commit()
        return make_flask_response(data=data, page_meta=pagination.get_metadata())

    @input_validator
    @credentials_required
    @emits_event(resource_type=Event.ResourceType.TRUSTED_JOB_GROUP, op_type=Event.OperationType.CREATE)
    @use_kwargs(CreateTrustedJobGroupParams(), location='json')
    def post(self, name: str, comment: Optional[str], algorithm_id: Optional[int], algorithm_uuid: Optional[str],
             dataset_id: Optional[int], participant_datasets: ParticipantDatasetList, resource: ResourcePb,
             project_id: int):
        """Create a trusted job group
        ---
        tags:
          - tee
        description: create a trusted job group
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        requestBody:
          required: true
          content:
           application/json:
             schema:
               $ref: '#/definitions/CreateTrustedJobGroupParams'
        responses:
          201:
            description: the detail of the trusted job group
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.TrustedJobGroupPb'
          400:
            description: invalid argument
          403:
            description: the trusted job group is forbidden to create
          409:
            description: the trusted job group already exists
        """
        if not Flag.TRUSTED_COMPUTING_ENABLED.value:
            raise NoAccessException('trusted computing is not enabled')
        if dataset_id is None and not participant_datasets.items:
            raise InvalidArgumentException('dataset_id and participant_datasets are both missing')
        with db.session_scope() as session:
            project = get_project(session, project_id)
            # TODO(liuledian): remove algorithm_id logic after frontend completed
            if not algorithm_uuid:
                algorithm_uuid = get_algorithm(session, algorithm_id).uuid
            algorithm = get_algorithm_with_uuid(project_id, algorithm_uuid)
            if algorithm.type != AlgorithmType.TRUSTED_COMPUTING.name:
                raise InvalidArgumentException(f'algorithm {algorithm_uuid} invalid type')
            if dataset_id is not None:
                dataset = get_dataset(session, dataset_id)
                if not dataset.is_published:
                    raise InvalidArgumentException(f'dataset {dataset.id} not published')
            for pd in participant_datasets.items:
                get_participant(session, pd.participant_id)
            group = session.query(TrustedJobGroup).filter_by(name=name, project_id=project_id).first()
            if group is not None:
                raise ResourceConflictException(f'trusted job group {name} in project {project_id} already exists')
            # TODO(liuledian): let creator assign analyzer id
            enabled_pids = get_tee_enabled_participants(session, project_id)
            if len(enabled_pids) != 1:
                raise InternalException('tee enabled participants not valid')
            analyzer_id = enabled_pids[0]

        with db.session_scope() as session:
            group = TrustedJobGroup(
                name=name,
                uuid=resource_uuid(),
                latest_version=0,
                comment=comment,
                project_id=project.id,
                creator_username=get_current_user().username,
                coordinator_id=0,
                analyzer_id=analyzer_id,
                auth_status=AuthStatus.AUTHORIZED,
                algorithm_uuid=algorithm_uuid,
                dataset_id=dataset_id,
            )
            participants = ParticipantService(session).get_participants_by_project(project.id)
            group.set_unauth_participant_ids([p.id for p in participants])
            group.set_resource(resource)
            group.set_participant_datasets(participant_datasets)
            session.add(group)
            get_ticket_helper(session).create_ticket(TicketType.TK_CREATE_TRUSTED_JOB_GROUP,
                                                     TicketDetails(uuid=group.uuid))
            session.commit()
            return make_flask_response(data=group.to_proto(), status=HTTPStatus.CREATED)


class TrustedJobGroupApi(Resource):

    @credentials_required
    def get(self, project_id: int, group_id: int):
        """Get the trusted job group
        ---
        tags:
          - tee
        descriptions: get the trusted job group
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        - in: path
          name: group_id
          schema:
            type: integer
          required: true
        responses:
          200:
            description: detail of the trusted job group
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.TrustedJobGroupPb'
          403:
            description: the trusted job group is forbidden access
          404:
            description: trusted job group is not found
        """
        if not Flag.TRUSTED_COMPUTING_ENABLED.value:
            raise NoAccessException('trusted computing is not enabled')
        with db.session_scope() as session:
            group = get_trusted_job_group(session, project_id, group_id)
            try:
                TrustedJobGroupController(session, project_id).update_unauth_participant_ids(group)
                data = group.to_proto()
                algorithm = AlgorithmFetcher(project_id).get_algorithm(group.algorithm_uuid)
                data.algorithm_project_uuid = algorithm.algorithm_project_uuid
                data.algorithm_participant_id = algorithm.participant_id
            except InternalException:
                logging.warning(f'[trusted-job-group] group {group_id} update unauth_participant_ids failed')
            except NotFoundException:
                logging.warning(f'[trusted-job-group] group {group_id} fetch algorithm {group.algorithm_uuid} failed')
            session.commit()
        return make_flask_response(data)

    @input_validator
    @credentials_required
    @emits_event(resource_type=Event.ResourceType.TRUSTED_JOB_GROUP, op_type=Event.OperationType.UPDATE)
    @use_kwargs(ConfigTrustedJobGroupParams(), location='json')
    def put(self, comment: Optional[str], auth_status: Optional[AuthStatus], algorithm_id: Optional[int],
            algorithm_uuid: Optional[str], resource: Optional[ResourcePb], project_id: int, group_id: int):
        """Update the trusted job group
        ---
        tags:
          - tee
        description: update the trusted job group
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        - in: path
          name: group_id
          schema:
            type: integer
          required: true
        requestBody:
          required: true
          content:
            application/json:
              schema:
                $ref: '#/definitions/ConfigTrustedJobGroupParams'
        responses:
          200:
            description: update the trusted job group successfully
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.TrustedJobGroupPb'
          400:
            description: invalid argument
          403:
            description: the trusted job group is forbidden to update
          404:
            description: trusted job group is not found
          409:
            description: the trusted job group has not been fully created
        """
        if not Flag.TRUSTED_COMPUTING_ENABLED.value:
            raise NoAccessException('trusted computing is not enabled')
        with db.session_scope() as session:
            group = get_trusted_job_group(session, project_id, group_id)
            controller = TrustedJobGroupController(session, project_id)
            if group.status != GroupCreateStatus.SUCCEEDED:
                raise ResourceConflictException('the trusted job group has not been fully created')
            if comment is not None:
                group.comment = comment
            if auth_status is not None and auth_status != group.auth_status:
                controller.inform_trusted_job_group(group, auth_status)
            if algorithm_uuid or algorithm_id:
                if group.coordinator_id:
                    raise NoAccessException('only coordinator can update algorithm')
                # TODO(liuledian): remove after frontend completed
                if not algorithm_uuid:
                    algorithm_uuid = get_algorithm(session, algorithm_id).uuid
                algorithm = get_algorithm_with_uuid(project_id, algorithm_uuid)
                old_algorithm = get_algorithm_with_uuid(project_id, group.algorithm_uuid)
                if algorithm.algorithm_project_uuid != old_algorithm.algorithm_project_uuid:
                    raise InvalidArgumentException('algorithm project mismatch between old and new algorithm')
                controller.update_trusted_job_group(group, algorithm_uuid)
            if resource is not None:
                group.set_resource(resource)
            data = group.to_proto()
            session.commit()
        return make_flask_response(data)

    @credentials_required
    @emits_event(resource_type=Event.ResourceType.TRUSTED_JOB_GROUP, op_type=Event.OperationType.DELETE)
    def delete(self, project_id: int, group_id: int):
        """Delete the trusted job group
        ---
        tags:
          - tee
        description: delete the trusted job group
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        - in: path
          name: group_id
          schema:
            type: integer
          required: true
        responses:
          204:
            description: delete the trusted job group successfully
          403:
            description: the trusted job group is forbidden to delete
          409:
            description: the trusted job group cannot be deleted
        """
        if not Flag.TRUSTED_COMPUTING_ENABLED.value:
            raise NoAccessException('trusted computing is not enabled')
        with db.session_scope() as session:
            group = session.query(TrustedJobGroup).filter_by(project_id=project_id, id=group_id).first()
            if group is not None:
                if group.coordinator_id:
                    raise NoAccessException('only creator can delete the trusted job group')
                if not group.is_deletable():
                    raise ResourceConflictException('the trusted job group cannot be deleted')
                TrustedJobGroupController(session, project_id).delete_trusted_job_group(group)
                session.commit()
            return make_flask_response(status=HTTPStatus.NO_CONTENT)


class LaunchTrustedJobApi(Resource):

    @input_validator
    @credentials_required
    @emits_event(resource_type=Event.ResourceType.TRUSTED_JOB, op_type=Event.OperationType.LAUNCH)
    @use_kwargs({'comment': fields.Str(required=False, load_default=None)}, location='json')
    def post(self, comment: Optional[str], project_id: int, group_id: int):
        """Launch the trusted job
        ---
        tags:
          - tee
        description: launch the trusted job
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        - in: path
          name: group_id
          schema:
            type: integer
          required: true
        requestBody:
          required: False
          content:
            application/json:
              schema:
                type: object
                properties:
                  comment:
                    type: string
        responses:
          201:
            description: launch the trusted job successfully
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.TrustedJobPb'
          403:
            description: the trusted job is forbidden to launch
          404:
            description: trusted job group is not found
          409:
            description: the trusted job group is not fully created or authorized
          500:
            description: internal exception
        """
        if not Flag.TRUSTED_COMPUTING_ENABLED.value:
            raise NoAccessException('trusted computing is not enabled')
        with db.session_scope() as session:
            group = get_trusted_job_group(session, project_id, group_id)
            if (group.status != GroupCreateStatus.SUCCEEDED or group.get_unauth_participant_ids() or
                    group.auth_status != AuthStatus.AUTHORIZED):
                raise ResourceConflictException('the trusted job group is not fully created or authorized')
            group = TrustedJobGroupService(session).lock_and_update_version(group_id)
            session.commit()
        succeeded, msg = launch_trusted_job(project_id, group.uuid, group.latest_version)
        if not succeeded:
            raise InternalException(f'launching trusted job failed with message: {msg}')
        with db.session_scope() as session:
            trusted_job: TrustedJob = session.query(TrustedJob).filter_by(trusted_job_group_id=group_id,
                                                                          version=group.latest_version).first()
            trusted_job.comment = comment
            session.commit()
            return make_flask_response(trusted_job.to_proto(), status=HTTPStatus.CREATED)


class GetTrustedJobsParams(Schema):
    trusted_job_group_id = fields.Integer(required=True)
    page = fields.Integer(required=False, load_default=None)
    page_size = fields.Integer(required=False, load_default=None)
    trusted_job_type = fields.Str(required=False,
                                  data_key='type',
                                  load_default=TrustedJobType.ANALYZE.name,
                                  validate=validate.OneOf([TrustedJobType.ANALYZE.name, TrustedJobType.EXPORT.name]))

    @post_load()
    def make(self, data, **kwargs):
        if data['trusted_job_type'] is not None:
            data['trusted_job_type'] = TrustedJobType[data['trusted_job_type']]
        return data


class TrustedJobsApi(Resource):

    @credentials_required
    @use_kwargs(GetTrustedJobsParams(), location='query')
    def get(self, trusted_job_group_id: int, page: Optional[int], page_size: Optional[int], trusted_job_type: str,
            project_id: int):
        """Get the list of trusted jobs
        ---
        tags:
          - tee
        description: get the list of trusted jobs
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        - in: query
          name: group_id
          schema:
            type: integer
        - in: query
          name: page
          schema:
            type: integer
        - in: query
          name: page_size
          schema:
            type: integer
        - in: query
          name: type
          schema:
            type: string
        responses:
          200:
            description: list of trusted jobs
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.TrustedJobRef'
          403:
            description: trusted job list is forbidden to access
        """
        if not Flag.TRUSTED_COMPUTING_ENABLED.value:
            raise NoAccessException('trusted computing is not enabled')
        with db.session_scope() as session:
            query = session.query(TrustedJob).filter_by(type=trusted_job_type)
            # filter out trusted jobs in notification when getting the export type
            if trusted_job_type == TrustedJobType.EXPORT:
                query = query.filter(TrustedJob.auth_status != AuthStatus.PENDING)
            if project_id:
                query = query.filter_by(project_id=project_id)
            if trusted_job_group_id:
                query = query.filter_by(trusted_job_group_id=trusted_job_group_id)
            if trusted_job_type == TrustedJobType.ANALYZE:
                query = query.order_by(TrustedJob.version.desc())
            else:
                # the version of tee export job equals to corresponding tee analyze job, so sort by creation time
                query = query.order_by(TrustedJob.created_at.desc())
            pagination = paginate(query, page, page_size)
            data = [d.to_ref() for d in pagination.get_items()]
            session.commit()
        return make_flask_response(data=data, page_meta=pagination.get_metadata())


class UpdateTrustedJobParams(Schema):
    comment = fields.Str(required=False, load_default=None)
    auth_status = fields.Str(required=False,
                             load_default=None,
                             validate=validate.OneOf([AuthStatus.AUTHORIZED.name, AuthStatus.WITHDRAW.name]))

    @post_load()
    def make(self, data, **kwargs):
        if data['auth_status'] is not None:
            data['auth_status'] = AuthStatus[data['auth_status']]
        return data


class TrustedJobApi(Resource):

    @credentials_required
    def get(self, project_id: int, trusted_job_id: int):
        """Get the trusted job by id
        ---
        tags:
          - tee
        description: get the trusted job by id
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        - in: path
          name: trusted_job_id
          schema:
            type: integer
          required: true
        responses:
          200:
            description: detail of the trusted job
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.TrustedJobPb'
          403:
            description: the trusted job is forbidden to access
          404:
            description: the trusted job is not found
        """
        if not Flag.TRUSTED_COMPUTING_ENABLED.value:
            raise NoAccessException('trusted computing is not enabled')
        with db.session_scope() as session:
            trusted_job = get_trusted_job(session, project_id, trusted_job_id)
            if trusted_job.type == TrustedJobType.EXPORT:
                TrustedJobController(session, project_id).update_participants_info(trusted_job)
            data = trusted_job.to_proto()
            session.commit()
        return make_flask_response(data)

    @input_validator
    @credentials_required
    @emits_event(resource_type=Event.ResourceType.TRUSTED_JOB, op_type=Event.OperationType.UPDATE)
    @use_kwargs(UpdateTrustedJobParams(), location='json')
    def put(self, comment: str, auth_status: AuthStatus, project_id: int, trusted_job_id: int):
        """Update the trusted job
        ---
        tags:
          - tee
        description: update the trusted job
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        - in: path
          name: trusted_job_id
          schema:
            type: integer
          required: true
        requestBody:
          required: true
          content:
            application/json:
              schema:
                $ref: '#/definitions/UpdateTrustedJobParams'
        responses:
          200:
            description: detail of the model job
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.TrustedJobPb'
          403:
            description: the trusted job is forbidden to update
          404:
            description: the trusted job is not found
        """
        if not Flag.TRUSTED_COMPUTING_ENABLED.value:
            raise NoAccessException('trusted computing is not enabled')
        with db.session_scope() as session:
            trusted_job = get_trusted_job(session, project_id, trusted_job_id)
            if comment is not None:
                trusted_job.comment = comment
            if auth_status is not None:
                TrustedJobController(session, project_id).inform_auth_status(trusted_job, auth_status)
            data = trusted_job.to_proto()
            session.commit()
        return make_flask_response(data)


class StopTrustedJobApi(Resource):

    @credentials_required
    def post(self, project_id: int, trusted_job_id: int):
        """Stop the trusted job
        ---
        tags:
          - tee
        description: stop the trusted job
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        - in: path
          name: trusted_job_id
          schema:
            type: integer
          required: true
        responses:
          204:
            description: stop the trusted job successfully
          403:
            description: the trusted job is forbidden to stop
          404:
            description: the trusted job is not found
          409:
            description: the trusted job is not running
        """
        if not Flag.TRUSTED_COMPUTING_ENABLED.value:
            raise NoAccessException('trusted computing is not enabled')
        with db.session_scope() as session:
            trusted_job = get_trusted_job(session, project_id, trusted_job_id)
            if trusted_job.get_status() != TrustedJobStatus.RUNNING:
                raise ResourceConflictException(f'the trusted job {trusted_job.id} is not running')
        succeeded, msg = stop_trusted_job(project_id, trusted_job.uuid)
        if not succeeded:
            raise InternalException(f'stop trusted job failed with msg {msg}')
        return make_flask_response(status=HTTPStatus.NO_CONTENT)


class TrustedNotificationsApi(Resource):

    @credentials_required
    def get(self, project_id: int):
        """Get the list of trusted notifications
        ---
        tags:
          - tee
        description: get the list of trusted notifications
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        responses:
          200:
            description: list of trusted notifications
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.TrustedNotification'
          403:
            description: trusted notification is forbidden to access
        """
        if not Flag.TRUSTED_COMPUTING_ENABLED.value:
            raise NoAccessException('trusted computing is not enabled')
        with db.session_scope() as session:
            query = session.query(TrustedJobGroup).filter_by(resource=None)
            if project_id:
                query = query.filter_by(project_id=project_id)
            data = [d.to_notification() for d in query.all()]
            query = session.query(TrustedJob).filter_by(auth_status=AuthStatus.PENDING, type=TrustedJobType.EXPORT)
            if project_id:
                query = query.filter_by(project_id=project_id)
            data += [d.to_notification() for d in query.all()]
            data.sort(key=lambda x: x.created_at, reverse=True)
            return make_flask_response(data)


class ExportTrustedJobApi(Resource):

    @credentials_required
    @emits_event(resource_type=Event.ResourceType.TRUSTED_EXPORT_JOB, op_type=Event.OperationType.CREATE)
    def post(self, project_id: int, trusted_job_id: int):
        """Export the trusted job
        ---
        tags:
          - tee
        description: export the trusted job
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
          required: true
        - in: path
          name: trusted_job_id
          schema:
            type: integer
          required: true
        responses:
          204:
            description: export the trusted job successfully
          403:
            description: the trusted job is forbidden to export
          404:
            description: the trusted job is not found
          409:
            description: the trusted job is not succeeded
        """
        if not Flag.TRUSTED_COMPUTING_ENABLED.value:
            raise NoAccessException('trusted computing is not enabled')
        with db.session_scope() as session:
            trusted_job = get_trusted_job(session, project_id, trusted_job_id)
            if trusted_job.type != TrustedJobType.ANALYZE or trusted_job.get_status() != TrustedJobStatus.SUCCEEDED:
                raise ResourceConflictException(f'the trusted job {trusted_job.id} is not valid')
            trusted_job = TrustedJobService(session).lock_and_update_export_count(trusted_job_id)
            session.commit()
        with db.session_scope() as session:
            uuid = resource_uuid()
            TrustedJobService(session).create_internal_export(uuid, trusted_job)
            get_ticket_helper(session).create_ticket(TicketType.TK_CREATE_TRUSTED_EXPORT_JOB, TicketDetails(uuid=uuid))
            session.commit()
        return make_flask_response(status=HTTPStatus.NO_CONTENT)


def initialize_tee_apis(api):
    api.add_resource(TrustedJobGroupsApi, '/projects/<int:project_id>/trusted_job_groups')
    api.add_resource(TrustedJobGroupApi, '/projects/<int:project_id>/trusted_job_groups/<int:group_id>')
    api.add_resource(LaunchTrustedJobApi, '/projects/<int:project_id>/trusted_job_groups/<int:group_id>:launch')
    api.add_resource(TrustedJobsApi, '/projects/<int:project_id>/trusted_jobs')
    api.add_resource(TrustedJobApi, '/projects/<int:project_id>/trusted_jobs/<int:trusted_job_id>')
    api.add_resource(StopTrustedJobApi, '/projects/<int:project_id>/trusted_jobs/<int:trusted_job_id>:stop')
    api.add_resource(TrustedNotificationsApi, '/projects/<int:project_id>/trusted_notifications')
    api.add_resource(ExportTrustedJobApi, '/projects/<int:project_id>/trusted_jobs/<int:trusted_job_id>:export')

    schema_manager.append(CreateTrustedJobGroupParams)
    schema_manager.append(ConfigTrustedJobGroupParams)
    schema_manager.append(GetTrustedJobsParams)
    schema_manager.append(UpdateTrustedJobParams)
