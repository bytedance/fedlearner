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

# pylint: disable=raise-missing-from
from datetime import timedelta
import logging
from typing import Any, Dict, Optional, List
from urllib.parse import urlparse

from http import HTTPStatus
from flask_restful import Resource, Api
from webargs.flaskparser import use_kwargs, use_args
from marshmallow.exceptions import ValidationError
from marshmallow import post_load, validate, fields
from marshmallow.schema import Schema
from google.protobuf.json_format import ParseDict, ParseError
from envs import Envs

from fedlearner_webconsole.audit.decorators import emits_event
from fedlearner_webconsole.composer.composer_service import ComposerService
from fedlearner_webconsole.composer.models import RunnerStatus
from fedlearner_webconsole.dataset.controllers import DatasetJobController
from fedlearner_webconsole.dataset.job_configer.dataset_job_configer import DatasetJobConfiger
from fedlearner_webconsole.dataset.job_configer.base_configer import set_variable_value_to_job_config
from fedlearner_webconsole.dataset.local_controllers import DatasetJobStageLocalController
from fedlearner_webconsole.dataset.models import (DataBatch, DataSource, DataSourceType, Dataset,
                                                  DatasetJobSchedulerState, ResourceState, DatasetJob, DatasetJobKind,
                                                  DatasetJobStage, DatasetJobState, ImportType, StoreFormat,
                                                  DatasetType, DatasetSchemaChecker, DatasetKindV2, DatasetFormat)
from fedlearner_webconsole.dataset.services import (DatasetJobService, DatasetService, DataSourceService,
                                                    DatasetJobStageService)
from fedlearner_webconsole.dataset.util import get_export_dataset_name, add_default_url_scheme, is_streaming_folder, \
    CronInterval
from fedlearner_webconsole.dataset.auth_service import AuthService
from fedlearner_webconsole.dataset.filter_funcs import dataset_auth_status_filter_op_in, dataset_format_filter_op_in, \
    dataset_format_filter_op_equal, dataset_publish_frontend_filter_op_equal
from fedlearner_webconsole.exceptions import InvalidArgumentException, MethodNotAllowedException, NoAccessException, \
    NotFoundException
from fedlearner_webconsole.db import db
from fedlearner_webconsole.proto.dataset_pb2 import DatasetJobGlobalConfigs, TimeRange
from fedlearner_webconsole.proto.filtering_pb2 import FilterExpression, FilterOp
from fedlearner_webconsole.proto.review_pb2 import TicketDetails, TicketType
from fedlearner_webconsole.review.ticket_helper import get_ticket_helper
from fedlearner_webconsole.rpc.v2.job_service_client import JobServiceClient
from fedlearner_webconsole.rpc.v2.resource_service_client import ResourceServiceClient
from fedlearner_webconsole.rpc.v2.system_service_client import SystemServiceClient
from fedlearner_webconsole.setting.service import SettingService
from fedlearner_webconsole.utils.base_model.auth_model import AuthStatus
from fedlearner_webconsole.utils.decorators.pp_flask import admin_required, input_validator
from fedlearner_webconsole.utils.domain_name import get_pure_domain_name
from fedlearner_webconsole.auth.third_party_sso import credentials_required
from fedlearner_webconsole.utils.file_manager import FileManager
from fedlearner_webconsole.utils import filtering, sorting
from fedlearner_webconsole.utils.flask_utils import FilterExpField, make_flask_response
from fedlearner_webconsole.proto import dataset_pb2
from fedlearner_webconsole.swagger.models import schema_manager
from fedlearner_webconsole.participant.services import ParticipantService
from fedlearner_webconsole.project.models import Project
from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.utils.paginate import paginate
from fedlearner_webconsole.utils.file_tree import FileTreeBuilder
from fedlearner_webconsole.workflow.models import WorkflowExternalState
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.flag.models import Flag

_DEFAULT_DATA_SOURCE_PREVIEW_FILE_NUM = 3


def _path_authority_validator(path: str):
    """Validate data_source path
        this func is used to forbiden access to local filesystem
        1. if path is not nfs, pass
        2. if path is nfs and belongs to STORAGE_ROOT, pass
        3. if path is nfs but doesn's belong to STORAGE_ROOT, raise ValidationError
    """
    path = path.strip()
    authority_path = add_default_url_scheme(Envs.STORAGE_ROOT)
    if not authority_path.endswith('/'):
        authority_path += '/'
    validate_path = add_default_url_scheme(path)
    if _parse_data_source_url(validate_path).type != DataSourceType.FILE.value:
        return
    if not validate_path.startswith(authority_path):
        raise ValidationError(f'no access to unauchority path {validate_path}!')


def _export_path_validator(path: str):
    path = path.strip()
    if len(path) == 0:
        raise ValidationError('export path is empty!')
    fm = FileManager()
    if not fm.can_handle(path):
        raise ValidationError('cannot handle export path!')
    if not fm.isdir(path):
        raise ValidationError('export path is not exist!')
    _path_authority_validator(path)


def _parse_data_source_url(data_source_url: str) -> dataset_pb2.DataSource:
    data_source_url = data_source_url.strip()
    data_source_url = add_default_url_scheme(data_source_url)
    url_parser = urlparse(data_source_url)
    data_source_type = url_parser.scheme
    # source_type must in DataSourceType
    if data_source_type not in [o.value for o in DataSourceType]:
        raise ValidationError(f'{data_source_type} is not a supported data_source type')
    return dataset_pb2.DataSource(
        type=data_source_type,
        url=data_source_url,
        is_user_upload=False,
        is_user_export=False,
    )


def _validate_data_source(data_source_url: str, dataset_type: DatasetType):
    fm = FileManager()
    if not fm.can_handle(path=data_source_url):
        raise InvalidArgumentException(f'invalid data_source_url: {data_source_url}')
    if not fm.isdir(path=data_source_url):
        raise InvalidArgumentException(f'cannot connect to data_source_url: {data_source_url}')
    if dataset_type == DatasetType.STREAMING:
        res, message = is_streaming_folder(data_source_url)
        if not res:
            raise InvalidArgumentException(message)


class DatasetJobConfigParameter(Schema):
    dataset_uuid = fields.Str(required=False)
    dataset_id = fields.Integer(required=False)
    variables = fields.List(fields.Dict())

    @post_load
    def make_dataset_job_config(self, item: Dict[str, Any], **kwargs) -> dataset_pb2.DatasetJobConfig:
        del kwargs  # this variable is not needed for now

        try:
            dataset_job_config = dataset_pb2.DatasetJobConfig()
            return ParseDict(item, dataset_job_config)
        except ParseError as err:
            raise ValidationError(message='failed to convert dataset_job_config',
                                  field_name='global_configs',
                                  data=err.args)


class DatasetJobParameter(Schema):
    global_configs = fields.Dict(required=True, keys=fields.Str(), values=fields.Nested(DatasetJobConfigParameter()))
    dataset_job_kind = fields.Str(required=False,
                                  validate=validate.OneOf([o.value for o in DatasetJobKind]),
                                  load_default='')

    @post_load
    def make_dataset_job(self, item: Dict[str, Any], **kwargs) -> dataset_pb2.DatasetJob:
        del kwargs  # this variable is not needed for now

        global_configs = item['global_configs']
        global_configs_pb = DatasetJobGlobalConfigs()
        for domain_name, job_config in global_configs.items():
            global_configs_pb.global_configs[get_pure_domain_name(domain_name)].MergeFrom(job_config)

        return dataset_pb2.DatasetJob(kind=item['dataset_job_kind'], global_configs=global_configs_pb)


class DatasetJobVariablesParameter(Schema):
    variables = fields.List(fields.Dict())

    @post_load
    def make_dataset_job_config(self, item: Dict[str, Any], **kwargs) -> dataset_pb2.DatasetJobConfig:
        del kwargs  # this variable is not needed for now

        try:
            dataset_job_config = dataset_pb2.DatasetJobConfig()
            return ParseDict(item, dataset_job_config)
        except ParseError as err:
            raise ValidationError(message='failed to convert dataset_job_config',
                                  field_name='dataset_job_config',
                                  data=err.args)


class DatasetApi(Resource):

    @credentials_required
    def get(self, dataset_id: int):
        """Get dataset details
        ---
        tags:
          - dataset
        description: get details of dataset
        parameters:
        - in: path
          required: true
          name: dataset_id
          schema:
            type: integer
        responses:
          200:
            description: get details of dataset
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.Dataset'
        """
        with db.session_scope() as session:
            dataset = DatasetService(session).get_dataset(dataset_id)
            # TODO(liuhehan): this commit is a lazy update of dataset store_format, remove it after release 2.4
            session.commit()
            return make_flask_response(dataset)

    @input_validator
    @credentials_required
    @emits_event()
    @use_kwargs({'comment': fields.Str(required=False, load_default=None)})
    def patch(self, dataset_id: int, comment: Optional[str]):
        """Change dataset info
        ---
        tags:
          - dataset
        description: change dataset info
        parameters:
        - in: path
          required: true
          name: dataset_id
          schema:
            type: integer
        requestBody:
          required: false
          content:
            application/json:
              schema:
                type: object
                properties:
                  comment:
                    type: string
        responses:
          200:
            description: change dataset info
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.Dataset'
        """
        with db.session_scope() as session:
            dataset = session.query(Dataset).filter_by(id=dataset_id).first()
            if not dataset:
                raise NotFoundException(f'Failed to find dataset: {dataset_id}')
            if comment:
                dataset.comment = comment
            session.commit()
            return make_flask_response(dataset.to_proto())

    @credentials_required
    @emits_event()
    def delete(self, dataset_id: int):
        """Delete dataset
        ---
        tags:
          - dataset
        description: delete dataset
        parameters:
        - in: path
          required: true
          name: dataset_id
          schema:
            type: integer
        responses:
          204:
            description: deleted dataset result
        """
        with db.session_scope() as session:
            # added an exclusive lock to this row
            # ensure the state is modified correctly in a concurrency scenario.
            dataset = session.query(Dataset).with_for_update().populate_existing().get(dataset_id)
            if not dataset:
                raise NotFoundException(f'Failed to find dataset: {dataset_id}')
            DatasetService(session).cleanup_dataset(dataset)
            session.commit()
        return make_flask_response(status=HTTPStatus.NO_CONTENT)


class DatasetPreviewApi(Resource):

    @credentials_required
    @use_kwargs({
        'batch_id': fields.Integer(required=True),
    }, location='query')
    def get(self, dataset_id: int, batch_id: int):
        """Get dataset preview
        ---
        tags:
          - dataset
        description: get dataset preview
        parameters:
        - in: path
          required: true
          name: dataset_id
          schema:
            type: integer
        - in: query
          name: batch_id
          schema:
            type: integer
        responses:
          200:
            description: dataset preview info
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    dtypes:
                      type: array
                      items:
                        type: object
                        properties:
                          key:
                            type: string
                          value:
                            type: string
                    sample:
                      type: array
                      items:
                        type: array
                        items:
                          anyOf:
                          - type: string
                          - type: integer
                          - type: number
                    num_example:
                      type: integer
                    metrics:
                      type: object
                    images:
                      type: array
                      items:
                        type: object
                        properties:
                          created_at:
                            type: string
                          file_name:
                            type: string
                          name:
                            type: string
                          height:
                            type: string
                          width:
                            type: string
                          path:
                            type: string
        """
        if dataset_id <= 0:
            raise NotFoundException(f'Failed to find dataset: {dataset_id}')
        with db.session_scope() as session:
            data = DatasetService(session).get_dataset_preview(dataset_id, batch_id)
            return make_flask_response(data)


class DatasetLedgerApi(Resource):

    def get(self, dataset_id: int):
        """Get dataset ledger
        ---
        tags:
          - dataset
        description: get
        parameters:
        - in: path
          name: dataset_id
          schema:
            type: integer
        responses:
          200:
            description: get dataset ledger page
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.DatasetLedger'
        """
        return make_flask_response(data={}, status=HTTPStatus.NO_CONTENT)


class DatasetExportApi(Resource):

    @credentials_required
    @use_kwargs({
        'export_path': fields.Str(required=True, validate=_export_path_validator),
        'batch_id': fields.Integer(required=False, load_default=None)
    })
    def post(self, dataset_id: int, export_path: str, batch_id: Optional[int]):
        """Export dataset
        ---
        tags:
          - dataset
        description: Export dataset
        parameters:
        - in: path
          required: true
          name: dataset_id
          schema:
            type: integer
        requestBody:
          required: true
          content:
            application/json:
              schema:
                type: object
                properties:
                  export_path:
                    type: string
                    required: true
                  batch_id:
                    type: integer
                    required: false
        responses:
          201:
            description: Export dataset
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    export_dataset_id:
                      type: integer
                    dataset_job_id:
                      type: integer
        """
        export_path = _parse_data_source_url(export_path).url
        with db.session_scope() as session:
            input_dataset: Dataset = session.query(Dataset).get(dataset_id)
            if not input_dataset:
                raise NotFoundException(f'Failed to find dataset: {dataset_id}')
            export_index = session.query(DatasetJob).filter(DatasetJob.kind == DatasetJobKind.EXPORT).filter(
                DatasetJob.input_dataset_id == dataset_id).count()
            if batch_id:
                data_batch = session.query(DataBatch).filter(DataBatch.dataset_id == dataset_id).filter(
                    DataBatch.id == batch_id).first()
                if data_batch is None:
                    raise NotFoundException(f'Failed to find data_batch {batch_id} in dataset {dataset_id}')
                data_batches = [data_batch]
                export_dataset_name = get_export_dataset_name(index=export_index,
                                                              input_dataset_name=input_dataset.name,
                                                              input_data_batch_name=data_batch.batch_name)
            else:
                data_batches = input_dataset.data_batches
                export_dataset_name = get_export_dataset_name(index=export_index, input_dataset_name=input_dataset.name)
            dataset_job_config = dataset_pb2.DatasetJobConfig(dataset_uuid=input_dataset.uuid)
            store_format = StoreFormat.UNKNOWN.value if input_dataset.store_format == StoreFormat.UNKNOWN \
                else StoreFormat.CSV.value
            dataset_parameter = dataset_pb2.DatasetParameter(name=export_dataset_name,
                                                             type=input_dataset.dataset_type.value,
                                                             project_id=input_dataset.project.id,
                                                             kind=DatasetKindV2.EXPORTED.value,
                                                             format=DatasetFormat(input_dataset.dataset_format).name,
                                                             is_published=False,
                                                             store_format=store_format,
                                                             auth_status=AuthStatus.AUTHORIZED.name,
                                                             path=export_path)
            output_dataset = DatasetService(session=session).create_dataset(dataset_parameter=dataset_parameter)
            session.flush()
            global_configs = DatasetJobGlobalConfigs()
            pure_domain_name = SettingService.get_system_info().pure_domain_name
            global_configs.global_configs[pure_domain_name].MergeFrom(dataset_job_config)
            export_dataset_job = DatasetJobService(session).create_as_coordinator(project_id=input_dataset.project_id,
                                                                                  kind=DatasetJobKind.EXPORT,
                                                                                  output_dataset_id=output_dataset.id,
                                                                                  global_configs=global_configs)
            session.flush()
            for data_batch in reversed(data_batches):
                # skip non-succeeded data_batch
                if not data_batch.is_available():
                    continue
                DatasetJobStageLocalController(session=session).create_data_batch_and_job_stage_as_coordinator(
                    dataset_job_id=export_dataset_job.id,
                    global_configs=export_dataset_job.get_global_configs(),
                    event_time=data_batch.event_time)

            session.commit()
            return make_flask_response(data={
                'export_dataset_id': output_dataset.id,
                'dataset_job_id': export_dataset_job.id
            },
                                       status=HTTPStatus.OK)


class DatasetStateFixtApi(Resource):

    @credentials_required
    @admin_required
    @use_kwargs({
        'force':
            fields.Str(required=False, load_default=None, validate=validate.OneOf([o.value for o in DatasetJobState]))
    })
    def post(self, dataset_id: int, force: str):
        """fix dataset state
        ---
        tags:
          - dataset
        description: fix dataset state
        parameters:
        - in: path
          required: true
          name: dataset_id
          schema:
            type: integer
        requestBody:
          required: false
          content:
            application/json:
              schema:
                type: object
                properties:
                  force:
                    type: array
                    items:
                      type: string
        responses:
          200:
            description: fix dataset state successfully
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.Dataset'
        """
        with db.session_scope() as session:
            dataset: Dataset = session.query(Dataset).get(dataset_id)
            if not dataset:
                raise NotFoundException(f'Failed to find dataset: {dataset_id}')
            if force:
                dataset.parent_dataset_job.state = DatasetJobState(force)
            else:
                workflow_state = dataset.parent_dataset_job.workflow.get_state_for_frontend()
                # if workflow is completed, restart the batch stats task
                if workflow_state == WorkflowExternalState.COMPLETED:
                    item_name = dataset.parent_dataset_job.get_context().batch_stats_item_name
                    runners = ComposerService(session).get_recent_runners(item_name, count=1)
                    # This is a hack to restart the composer runner, see details in job_scheduler.py
                    if len(runners) > 0:
                        runners[0].status = RunnerStatus.INIT.value
                    dataset.parent_dataset_job.state = DatasetJobState.RUNNING
                elif workflow_state in (WorkflowExternalState.FAILED, WorkflowExternalState.STOPPED,
                                        WorkflowExternalState.INVALID):
                    dataset.parent_dataset_job.state = DatasetJobState.FAILED
            session.commit()
            return make_flask_response(data=dataset.to_proto(), status=HTTPStatus.OK)


class DatasetParameter(Schema):
    name = fields.Str(required=True)
    dataset_type = fields.Str(required=False,
                              load_default=DatasetType.PSI.value,
                              validate=validate.OneOf([o.value for o in DatasetType]))
    comment = fields.Str(required=False)
    project_id = fields.Int(required=True)
    kind = fields.Str(required=False,
                      load_default=DatasetKindV2.RAW.value,
                      validate=validate.OneOf([o.value for o in DatasetKindV2]))
    dataset_format = fields.Str(required=True, validate=validate.OneOf([o.name for o in DatasetFormat]))
    need_publish = fields.Bool(required=False, load_default=False)
    value = fields.Int(required=False, load_default=0, validate=[validate.Range(min=100, max=10000)])
    schema_checkers = fields.List(fields.Str(validate=validate.OneOf([o.value for o in DatasetSchemaChecker])))
    is_published = fields.Bool(required=False, load_default=False)
    import_type = fields.Str(required=False,
                             load_default=ImportType.COPY.value,
                             validate=validate.OneOf([o.value for o in ImportType]))
    store_format = fields.Str(required=False,
                              load_default=StoreFormat.TFRECORDS.value,
                              validate=validate.OneOf([o.value for o in StoreFormat]))

    @post_load
    def make_dataset_parameter(self, item: Dict[str, str], **kwargs) -> dataset_pb2.DatasetParameter:
        return dataset_pb2.DatasetParameter(name=item.get('name'),
                                            type=item.get('dataset_type'),
                                            comment=item.get('comment'),
                                            project_id=item.get('project_id'),
                                            kind=item.get('kind'),
                                            format=item.get('dataset_format'),
                                            need_publish=item.get('need_publish'),
                                            value=item.get('value'),
                                            is_published=item.get('is_published'),
                                            schema_checkers=item.get('schema_checkers'),
                                            import_type=item.get('import_type'),
                                            store_format=item.get('store_format'))


class DatasetsApi(Resource):
    FILTER_FIELDS = {
        'name':
            filtering.SupportedField(type=filtering.FieldType.STRING, ops={FilterOp.CONTAIN: None}),
        'project_id':
            filtering.SupportedField(type=filtering.FieldType.NUMBER, ops={FilterOp.EQUAL: None}),
        'uuid':
            filtering.SupportedField(type=filtering.FieldType.STRING, ops={FilterOp.EQUAL: None}),
        'dataset_kind':
            filtering.SupportedField(type=filtering.FieldType.STRING, ops={
                FilterOp.IN: None,
                FilterOp.EQUAL: None
            }),
        'dataset_format':
            filtering.SupportedField(type=filtering.FieldType.STRING,
                                     ops={
                                         FilterOp.IN: dataset_format_filter_op_in,
                                         FilterOp.EQUAL: dataset_format_filter_op_equal
                                     }),
        'is_published':
            filtering.SupportedField(type=filtering.FieldType.BOOL, ops={FilterOp.EQUAL: None}),
        'dataset_type':
            filtering.SupportedField(type=filtering.FieldType.STRING, ops={FilterOp.EQUAL: None}),
        'publish_frontend_state':
            filtering.SupportedField(type=filtering.FieldType.STRING,
                                     ops={FilterOp.EQUAL: dataset_publish_frontend_filter_op_equal}),
        'auth_status':
            filtering.SupportedField(type=filtering.FieldType.STRING,
                                     ops={FilterOp.IN: dataset_auth_status_filter_op_in}),
    }

    SORTER_FIELDS = ['created_at']

    def __init__(self):
        self._filter_builder = filtering.FilterBuilder(model_class=Dataset, supported_fields=self.FILTER_FIELDS)
        self._sorter_builder = sorting.SorterBuilder(model_class=Dataset, supported_fields=self.SORTER_FIELDS)

    @credentials_required
    @use_kwargs(
        {
            'page':
                fields.Integer(required=False, load_default=1),
            'page_size':
                fields.Integer(required=False, load_default=10),
            'dataset_job_kind':
                fields.String(required=False, load_default=None),
            'state_frontend':
                fields.List(
                    fields.String(
                        required=False, load_default=None, validate=validate.OneOf([o.value for o in ResourceState]))),
            'filter_exp':
                FilterExpField(required=False, load_default=None, data_key='filter'),
            'sorter_exp':
                fields.String(required=False, load_default=None, data_key='order_by'),
            'cron_interval':
                fields.String(
                    required=False, load_default=None, validate=validate.OneOf([o.value for o in CronInterval])),
        },
        location='query')
    def get(self,
            page: int,
            page_size: int,
            dataset_job_kind: Optional[str] = None,
            state_frontend: Optional[List[str]] = None,
            filter_exp: Optional[FilterExpression] = None,
            sorter_exp: Optional[str] = None,
            cron_interval: Optional[str] = None):
        """Get datasets list
        ---
        tags:
          - dataset
        description: get datasets list
        parameters:
        - in: query
          name: page
          schema:
            type: integer
        - in: query
          name: page_size
          schema:
            type: integer
        - in: query
          name: dataset_job_kind
          schema:
            type: string
        - in: query
          name: state_frontend
          schema:
            type: array
            collectionFormat: multi
            items:
              type: string
              enum: [PENDING, PROCESSING, SUCCEEDED, FAILED]
        - in: query
          name: filter
          schema:
            type: string
        - in: query
          name: order_by
          schema:
            type: string
        - in: query
          name: cron_interval
          schema:
            type: string
        responses:
          200:
            description: get datasets list result
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.DatasetRef'
        """
        if dataset_job_kind is not None:
            try:
                dataset_job_kind = DatasetJobKind(dataset_job_kind)
            except TypeError as err:
                raise InvalidArgumentException(
                    details=f'failed to find dataset dataset_job_kind {dataset_job_kind}') from err
        with db.session_scope() as session:
            query = DatasetService(session).query_dataset_with_parent_job()
            if dataset_job_kind:
                query = query.filter(DatasetJob.kind == dataset_job_kind)
            if filter_exp is not None:
                try:
                    query = self._filter_builder.build_query(query, filter_exp)
                except ValueError as e:
                    raise InvalidArgumentException(details=f'Invalid filter: {str(e)}') from e
            try:
                if sorter_exp is not None:
                    sorter_exp = sorting.parse_expression(sorter_exp)
                else:
                    sorter_exp = sorting.SortExpression(field='created_at', is_asc=False)
                query = self._sorter_builder.build_query(query, sorter_exp)
            except ValueError as e:
                raise InvalidArgumentException(details=f'Invalid sorter: {str(e)}') from e
            # TODO(liuhehan): add state_frontend as custom_builder
            if state_frontend is not None:
                states = []
                for state in state_frontend:
                    states.append(ResourceState(state))
                query = DatasetService.filter_dataset_state(query, states)
            # filter daily or hourly cron
            if cron_interval:
                if cron_interval == CronInterval.HOURS.value:
                    time_range = timedelta(hours=1)
                else:
                    time_range = timedelta(days=1)
                query = query.filter(DatasetJob.time_range == time_range)
            pagination = paginate(query=query, page=page, page_size=page_size)
            datasets = []
            for dataset in pagination.get_items():
                dataset_ref = dataset.to_ref()
                dataset_ref.total_value = 0
                datasets.append(dataset_ref)
            # TODO(liuhehan): this commit is a lazy update of dataset store_format, remove it after release 2.4
            session.commit()
            return make_flask_response(data=datasets, page_meta=pagination.get_metadata())

    @input_validator
    @credentials_required
    @emits_event()
    @use_args(DatasetParameter())
    def post(self, dataset_parameter: dataset_pb2.DatasetParameter):
        """Create dataset
        ---
        tags:
          - dataset
        description: Create dataset
        requestBody:
          required: true
          content:
            application/json:
              schema:
                $ref: '#/definitions/DatasetParameter'
        responses:
          201:
            description: Create dataset
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.Dataset'
        """
        with db.session_scope() as session:
            # processed dataset must be is_published
            if DatasetKindV2(dataset_parameter.kind) == DatasetKindV2.PROCESSED and not dataset_parameter.is_published:
                raise InvalidArgumentException('is_published must be true if dataset kind is PROCESSED')
            if DatasetKindV2(dataset_parameter.kind) == DatasetKindV2.PROCESSED and ImportType(
                    dataset_parameter.import_type) != ImportType.COPY:
                raise InvalidArgumentException('import type must be copy if dataset kind is PROCESSED')
            if StoreFormat(dataset_parameter.store_format) == StoreFormat.CSV and DatasetKindV2(
                    dataset_parameter.kind) in [DatasetKindV2.RAW, DatasetKindV2.PROCESSED]:
                raise InvalidArgumentException('csv store_type is not support if dataset kind is RAW or PROCESSED')
            dataset_parameter.auth_status = AuthStatus.AUTHORIZED.name
            dataset = DatasetService(session=session).create_dataset(dataset_parameter=dataset_parameter)
            session.flush()
            # create review ticket for processed_dataset
            if DatasetKindV2(dataset_parameter.kind) == DatasetKindV2.PROCESSED:
                ticket_helper = get_ticket_helper(session=session)
                ticket_helper.create_ticket(TicketType.CREATE_PROCESSED_DATASET, TicketDetails(uuid=dataset.uuid))
            session.commit()
            return make_flask_response(data=dataset.to_proto(), status=HTTPStatus.CREATED)


class ChildrenDatasetsApi(Resource):

    def get(self, dataset_id: int):
        """Get children datasets list
        ---
        tags:
          - dataset
        description: Get children datasets list
        parameters:
        - in: path
          name: dataset_id
          schema:
            type: integer
        responses:
          200:
            description: get children datasets list result
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.DatasetRef'
        """
        with db.session_scope() as session:
            query = DatasetService(session=session).query_dataset_with_parent_job()
            query = query.filter(DatasetJob.input_dataset_id == dataset_id)
            # exported dataset should not be shown in children datasets
            query = query.filter(Dataset.dataset_kind != DatasetKindV2.EXPORTED)
            return make_flask_response(data=[dataset.to_ref() for dataset in query.all()])


class BatchParameter(Schema):
    data_source_id = fields.Integer(required=True)
    comment = fields.Str(required=False)

    @post_load
    def make_batch_parameter(self, item: Dict[str, Any], **kwargs) -> dataset_pb2.BatchParameter:
        data_source_id = item.get('data_source_id')
        comment = item.get('comment')

        with db.session_scope() as session:
            data_source = session.query(DataSource).get(data_source_id)
            if data_source is None:
                raise ValidationError(message=f'failed to find data_source {data_source_id}',
                                      field_name='data_source_id')

        return dataset_pb2.BatchParameter(comment=comment, data_source_id=data_source_id)


class BatchesApi(Resource):

    SORTER_FIELDS = ['created_at', 'updated_at']

    def __init__(self):
        self._sorter_builder = sorting.SorterBuilder(model_class=DataBatch, supported_fields=self.SORTER_FIELDS)

    @credentials_required
    @use_kwargs(
        {
            'page': fields.Integer(required=False, load_default=1),
            'page_size': fields.Integer(required=False, load_default=10),
            'sorter_exp': fields.String(required=False, load_default=None, data_key='order_by')
        },
        location='query')
    def get(self, dataset_id: int, page: int, page_size: int, sorter_exp: Optional[str]):
        """List data batches
        ---
        tags:
          - dataset
        description: List data batches
        parameters:
        - in: path
          name: dataset_id
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
          name: order_by
          schema:
            type: string
        responses:
          200:
            description: list of data batches
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.DataBatch'
        """
        with db.session_scope() as session:
            query = session.query(DataBatch).filter(DataBatch.dataset_id == dataset_id)
            try:
                if sorter_exp is not None:
                    sorter_exp = sorting.parse_expression(sorter_exp)
                else:
                    # default sort is created_at desc
                    sorter_exp = sorting.SortExpression(field='created_at', is_asc=False)
                query = self._sorter_builder.build_query(query, sorter_exp)
            except ValueError as e:
                raise InvalidArgumentException(details=f'Invalid sorter: {str(e)}') from e
            pagination = paginate(query=query, page=page, page_size=page_size)
        return make_flask_response(data=[data_batch.to_proto() for data_batch in pagination.get_items()],
                                   page_meta=pagination.get_metadata())


class BatchApi(Resource):

    @credentials_required
    def get(self, dataset_id: int, data_batch_id: int):
        """Get data batch by id
        ---
        tags:
          - dataset
        description: Get data batch by id
        parameters:
        - in: path
          name: dataset_id
          schema:
            type: integer
        - in: path
          name: data_batch_id
          schema:
            type: integer
        responses:
          200:
            description: Get data batch by id
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.DataBatch'
        """
        with db.session_scope() as session:
            batch: DataBatch = session.query(DataBatch).filter(DataBatch.dataset_id == dataset_id).filter(
                DataBatch.id == data_batch_id).first()
            if batch is None:
                raise NotFoundException(f'failed to find batch {data_batch_id} in dataset {dataset_id}')
            return make_flask_response(data=batch.to_proto())


class BatchAnalyzeApi(Resource):

    @credentials_required
    @use_kwargs({'dataset_job_config': fields.Nested(DatasetJobVariablesParameter())})
    def post(self, dataset_id: int, data_batch_id: int, dataset_job_config: dataset_pb2.DatasetJobConfig):
        """Analyze data_batch by id
        ---
        tags:
          - dataset
        description: Analyze data_batch by id
        parameters:
        - in: path
          name: dataset_id
          schema:
            type: integer
        - in: path
          name: data_batch_id
          schema:
            type: integer
        requestBody:
          required: true
          content:
            application/json:
              schema:
                type: object
                properties:
                  dataset_job_config:
                    $ref: '#/definitions/fedlearner_webconsole.proto.DatasetJobConfig'
        responses:
          200:
            description: analyzer dataset job details
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.DatasetJob'
        """
        with db.session_scope() as session:
            dataset: Dataset = session.query(Dataset).get(dataset_id)
            if dataset is None:
                raise NotFoundException(f'Failed to find dataset: {dataset_id}')
            dataset_job_config.dataset_uuid = dataset.uuid
            global_configs = DatasetJobGlobalConfigs()
            pure_domain_name = SettingService.get_system_info().pure_domain_name
            global_configs.global_configs[pure_domain_name].MergeFrom(dataset_job_config)
            analyzer_dataset_job: DatasetJob = session.query(DatasetJob).filter(
                DatasetJob.output_dataset_id == dataset_id).filter(DatasetJob.kind == DatasetJobKind.ANALYZER).first()
            if analyzer_dataset_job is None:
                analyzer_dataset_job = DatasetJobService(session).create_as_coordinator(project_id=dataset.project_id,
                                                                                        kind=DatasetJobKind.ANALYZER,
                                                                                        output_dataset_id=dataset_id,
                                                                                        global_configs=global_configs)
            else:
                previous_global_configs = analyzer_dataset_job.get_global_configs()
                for variable in dataset_job_config.variables:
                    set_variable_value_to_job_config(previous_global_configs.global_configs[pure_domain_name], variable)
                analyzer_dataset_job.set_global_configs(previous_global_configs)
            session.flush()
            DatasetJobStageService(session).create_dataset_job_stage_as_coordinator(
                project_id=dataset.project_id,
                dataset_job_id=analyzer_dataset_job.id,
                output_data_batch_id=data_batch_id,
                global_configs=analyzer_dataset_job.get_global_configs())
            dataset_job_details = analyzer_dataset_job.to_proto()
            session.commit()

        return make_flask_response(data=dataset_job_details, status=HTTPStatus.OK)


class BatchMetricsApi(Resource):

    @credentials_required
    @use_kwargs({
        'name': fields.Str(required=True),
    }, location='query')
    def get(self, dataset_id: int, data_batch_id: int, name: str):
        """Get data batch metrics info
        ---
        tags:
          - dataset
        description: get data batch metrics info
        parameters:
        - in: path
          required: true
          name: dataset_id
          schema:
            type: integer
        - in: path
          required: true
          name: data_batch_id
          schema:
            type: integer
        - in: query
          required: true
          name: name
          schema:
            type: string
        responses:
          200:
            description: get data batch metrics info
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    name:
                      type: string
                    metrics:
                      type: object
                      properties:
                        count:
                          type: string
                        max:
                          type: string
                        min:
                          type: string
                        mean:
                          type: string
                        stddev:
                          type: string
                        missing_count:
                          type: string
                    hist:
                      type: object
                      properties:
                        x:
                          type: array
                          items:
                            type: number
                        y:
                          type: array
                          items:
                            type: number
        """
        # TODO(liuhehan): return dataset metrics in proto
        with db.session_scope() as session:
            data = DatasetService(session).feature_metrics(name, dataset_id, data_batch_id)
            return make_flask_response(data)


class BatchRerunApi(Resource):

    @credentials_required
    @use_kwargs({'dataset_job_parameter': fields.Nested(DatasetJobParameter())})
    def post(self, dataset_id: int, data_batch_id: int, dataset_job_parameter: dataset_pb2.DatasetJob):
        """rerun data_batch by id
        ---
        tags:
          - dataset
        description: Rerun data_batch by id
        parameters:
        - in: path
          name: dataset_id
          schema:
            type: integer
        - in: path
          name: data_batch_id
          schema:
            type: integer
        requestBody:
          required: true
          content:
            application/json:
              schema:
                type: object
                properties:
                  dataset_job_parameter:
                    $ref: '#/definitions/DatasetJobParameter'
        responses:
          200:
            description: dataset job stage details
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.DatasetJobStage'
        """
        global_configs = dataset_job_parameter.global_configs

        with db.session_scope() as session:
            dataset: Dataset = session.query(Dataset).get(dataset_id)
            if dataset is None:
                raise InvalidArgumentException(f'failed to find dataset: {dataset_id}')
            data_batch: DataBatch = session.query(DataBatch).filter(DataBatch.dataset_id == dataset_id).filter(
                DataBatch.id == data_batch_id).first()
            if data_batch is None:
                raise InvalidArgumentException(f'failed to find data_batch: {data_batch_id}')
            dataset_job: DatasetJob = dataset.parent_dataset_job
            if dataset_job is None:
                raise InvalidArgumentException(f'dataset_job is missing, output_dataset_id: {dataset_id}')
            # get current global_configs
            if dataset_job.is_coordinator():
                current_global_configs = dataset_job.get_global_configs()
            else:
                participant: Participant = session.query(Participant).get(dataset_job.coordinator_id)
                system_client = SystemServiceClient.from_participant(domain_name=participant.domain_name)
                flag_resp = system_client.list_flags()
                if not flag_resp.get(Flag.DATA_BATCH_RERUN_ENABLED.name):
                    raise MethodNotAllowedException(
                        f'particiapnt {participant.pure_domain_name()} not support rerun data_batch, ' \
                        'could only rerun data_batch created as coordinator'
                    )
                client = RpcClient.from_project_and_participant(dataset_job.project.name, dataset_job.project.token,
                                                                participant.domain_name)
                response = client.get_dataset_job(uuid=dataset_job.uuid)
                current_global_configs = response.dataset_job.global_configs
            # set global_configs
            for pure_domain_name in global_configs.global_configs:
                for variable in global_configs.global_configs[pure_domain_name].variables:
                    set_variable_value_to_job_config(current_global_configs.global_configs[pure_domain_name], variable)
            # create dataset_job_stage
            dataset_job_stage = DatasetJobStageService(session).create_dataset_job_stage_as_coordinator(
                project_id=dataset.project_id,
                dataset_job_id=dataset_job.id,
                output_data_batch_id=data_batch_id,
                global_configs=current_global_configs)
            session.flush()
            dataset_job_stage_details = dataset_job_stage.to_proto()
            session.commit()

        return make_flask_response(data=dataset_job_stage_details, status=HTTPStatus.OK)


class DataSourceParameter(Schema):
    name = fields.Str(required=True)
    comment = fields.Str(required=False)
    data_source_url = fields.Str(required=True, validate=_path_authority_validator)
    is_user_upload = fields.Bool(required=False)
    dataset_format = fields.Str(required=False,
                                load_default=DatasetFormat.TABULAR.name,
                                validate=validate.OneOf([o.name for o in DatasetFormat]))
    store_format = fields.Str(required=False,
                              load_default=StoreFormat.UNKNOWN.value,
                              validate=validate.OneOf([o.value for o in StoreFormat]))
    dataset_type = fields.Str(required=False,
                              load_default=DatasetType.PSI.value,
                              validate=validate.OneOf([o.value for o in DatasetType]))

    @post_load
    def make_data_source(self, item: Dict[str, str], **kwargs) -> dataset_pb2.DataSource:
        del kwargs  # this variable is not needed for now
        name = item.get('name')
        comment = item.get('comment')
        data_source_url = item.get('data_source_url')
        is_user_upload = item.get('is_user_upload', False)
        data_source = _parse_data_source_url(data_source_url)
        data_source.name = name
        data_source.dataset_format = item.get('dataset_format')
        data_source.store_format = item.get('store_format')
        data_source.dataset_type = item.get('dataset_type')
        if is_user_upload:
            data_source.is_user_upload = True
        if comment:
            data_source.comment = comment
        return data_source


class DataSourcesApi(Resource):

    @credentials_required
    @use_kwargs({'data_source': fields.Nested(DataSourceParameter()), 'project_id': fields.Integer(required=True)})
    def post(self, data_source: dataset_pb2.DataSource, project_id: int):
        """Create a data source
        ---
        tags:
          - dataset
        description: create a data source
        requestBody:
          required: true
          content:
            application/json:
              schema:
                type: object
                properties:
                  data_source:
                    type: object
                    required: true
                    properties:
                      schema:
                        $ref: '#/definitions/DataSourceParameter'
                  project_id:
                    type: integer
                    required: true
        responses:
          201:
            description: The data source is created
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.DataSource'
          409:
            description: A data source with the same name exists
          400:
            description: |
                A data source that webconsole cannot connect with
                Probably, unexist data source or unauthorized to the data source
        """

        _validate_data_source(data_source.url, DatasetType(data_source.dataset_type))
        with db.session_scope() as session:
            data_source.project_id = project_id
            data_source = DataSourceService(session=session).create_data_source(data_source)
            session.commit()
            return make_flask_response(data=data_source.to_proto(), status=HTTPStatus.CREATED)

    @credentials_required
    @use_kwargs({'project_id': fields.Integer(required=False, load_default=0, validate=validate.Range(min=0))},
                location='query')
    def get(self, project_id: int):
        """Get a list of data source
        ---
        tags:
          - dataset
        description: get a list of data source
        parameters:
        - in: query
          name: project_id
          schema:
            type: integer
        responses:
          200:
            description: list of data source
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.DataSource'
        """

        with db.session_scope() as session:
            data_sources = DataSourceService(session=session).get_data_sources(project_id)
            return make_flask_response(data=data_sources)


class DataSourceApi(Resource):

    @credentials_required
    def get(self, data_source_id: int):
        """Get target data source by id
        ---
        tags:
          - dataset
        description: get target data source by id
        parameters:
        - in: path
          name: data_source_id
          schema:
            type: integer
        responses:
          200:
            description: data source
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.DataSource'
        """

        with db.session_scope() as session:
            data_source: DataSource = session.query(DataSource).get(data_source_id)
            if not data_source:
                raise NotFoundException(message=f'cannot find data_source with id: {data_source_id}')
            return make_flask_response(data=data_source.to_proto())

    @credentials_required
    def delete(self, data_source_id: int):
        """Delete a data source
        ---
        tags:
          - dataset
        description: delete a data source
        parameters:
        - in: path
          name: data_source_id
          schema:
            type: integer
        responses:
          204:
            description: deleted data source result
        """

        with db.session_scope() as session:
            DataSourceService(session=session).delete_data_source(data_source_id)
            session.commit()
            return make_flask_response(data={}, status=HTTPStatus.NO_CONTENT)


class DataSourceTreeApi(Resource):

    @credentials_required
    def get(self, data_source_id: int):
        """Get the data source tree
        ---
        tags:
          - dataset
        description: get the data source tree
        parameters:
        - in: path
          name: data_source_id
          schema:
            type: integer
        responses:
          200:
            description: the file tree of the data source
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.FileTreeNode'
        """
        with db.session_scope() as session:
            data_source: DataSource = session.query(DataSource).get(data_source_id)
            # relative path is used in returned file tree
            file_tree = FileTreeBuilder(data_source.path, relpath=True).build_with_root()
            return make_flask_response(file_tree)


class DataSourceCheckConnectionApi(Resource):

    @credentials_required
    @use_kwargs({
        'data_source_url':
            fields.Str(required=True, validate=_path_authority_validator),
        'file_num':
            fields.Integer(required=False, load_default=_DEFAULT_DATA_SOURCE_PREVIEW_FILE_NUM),
        'dataset_type':
            fields.Str(required=False,
                       load_default=DatasetType.PSI.value,
                       validate=validate.OneOf([o.value for o in DatasetType]))
    })
    def post(self, data_source_url: str, file_num: int, dataset_type: str):
        """Check data source connection status
        ---
        tags:
          - dataset
        description: check data source connection status
        requestBody:
          required: true
          content:
            application/json:
              schema:
                type: object
                properties:
                  data_source_url:
                    type: string
                    required: true
                  file_num:
                    type: integer
                    required: false
                  dataset_type:
                    type: string
                    required: false
        responses:
          200:
            description: status details and file_names
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    extra_nums:
                      type: interger
                    file_names:
                      type: array
                      items:
                        type: string
        """

        data_source_url = _parse_data_source_url(data_source_url).url
        _validate_data_source(data_source_url, DatasetType(dataset_type))
        file_names = FileManager().listdir(data_source_url)
        return make_flask_response(data={
            'file_names': file_names[:file_num],
            'extra_nums': max(len(file_names) - file_num, 0),
        })


class ParticipantDatasetsApi(Resource):

    @credentials_required
    @use_kwargs(
        {
            'kind':
                fields.Str(required=False, load_default=None),
            'uuid':
                fields.Str(required=False, load_default=None),
            'participant_id':
                fields.Integer(required=False, load_default=None),
            'cron_interval':
                fields.String(
                    required=False, load_default=None, validate=validate.OneOf([o.value for o in CronInterval])),
        },
        location='query')
    def get(
        self,
        project_id: int,
        kind: Optional[str],
        uuid: Optional[str],
        participant_id: Optional[int],
        cron_interval: Optional[str],
    ):
        """Get list of participant datasets
        ---
        tags:
          - dataset
        description: get list of participant datasets
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: query
          name: kind
          schema:
            type: string
        - in: query
          name: uuid
          schema:
            type: string
        - in: query
          name: participant_id
          schema:
            type: integer
        - in: query
          name: cron_interval
          schema:
            type: string
        responses:
          200:
            description: list of participant datasets
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.ParticipantDatasetRef'
        """
        if kind is not None:
            try:
                DatasetKindV2(kind)
            except ValueError as err:
                raise InvalidArgumentException(details=f'failed to find dataset kind {kind}') from err
        time_range = None
        if cron_interval:
            if cron_interval == CronInterval.HOURS.value:
                time_range = TimeRange(hours=1)
            else:
                time_range = TimeRange(days=1)

        with db.session_scope() as session:
            if participant_id is None:
                participants = ParticipantService(session).get_platform_participants_by_project(project_id)
            else:
                participant = session.query(Participant).get(participant_id)
                if participant is None:
                    raise NotFoundException(f'particiapnt {participant_id} is not found')
                participants = [participant]
            project = session.query(Project).get(project_id)
            data = []
            for participant in participants:
                # check flag
                system_client = SystemServiceClient.from_participant(domain_name=participant.domain_name)
                flag_resp = system_client.list_flags()
                # if participant supports list dataset rpc, use new rpc
                if flag_resp.get(Flag.LIST_DATASETS_RPC_ENABLED.name):
                    client = ResourceServiceClient.from_project_and_participant(participant.domain_name, project.name)
                    response = client.list_datasets(kind=DatasetKindV2(kind) if kind is not None else None,
                                                    uuid=uuid,
                                                    state=ResourceState.SUCCEEDED,
                                                    time_range=time_range)
                else:
                    client = RpcClient.from_project_and_participant(project.name, project.token,
                                                                    participant.domain_name)
                    response = client.list_participant_datasets(kind=kind, uuid=uuid)
                datasets = response.participant_datasets
                if uuid:
                    datasets = [d for d in datasets if uuid and d.uuid == uuid]
                for dataset in datasets:
                    dataset.participant_id = participant.id
                    dataset.project_id = project_id
                data.extend(datasets)

            return make_flask_response(data=data)


class DatasetPublishApi(Resource):

    @credentials_required
    @use_kwargs({'value': fields.Int(required=False, load_default=0, validate=[validate.Range(min=100, max=10000)])})
    def post(self, dataset_id: int, value: int):
        """Publish the dataset in workspace
        ---
        tags:
          - dataset
        description: Publish the dataset in workspace
        parameters:
        - in: path
          name: dataset_id
          schema:
            type: integer
        requestBody:
          required: true
          content:
            application/json:
              schema:
                type: object
                properties:
                  value:
                    type: integer
                    required: true
        responses:
          200:
            description: published the dataset in workspace
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.Dataset'
        """
        with db.session_scope() as session:
            dataset = DatasetService(session=session).publish_dataset(dataset_id, value)
            session.commit()
            return make_flask_response(data=dataset.to_proto())

    @credentials_required
    def delete(self, dataset_id: int):
        """Revoke publish dataset ops
        ---
        tags:
          - dataset
        description: Revoke publish dataset ops
        parameters:
        - in: path
          name: dataset_id
          schema:
            type: integer
        responses:
          204:
            description: revoked publish dataset successfully
        """
        with db.session_scope() as session:
            DatasetService(session=session).withdraw_dataset(dataset_id)
            session.commit()
            return make_flask_response(data=None, status=HTTPStatus.NO_CONTENT)


class DatasetAuthorizehApi(Resource):

    @credentials_required
    def post(self, dataset_id: int):
        """Authorize target dataset by id
        ---
        tags:
          - dataset
        description: authorize target dataset by id
        parameters:
        - in: path
          name: dataset_id
          schema:
            type: integer
        responses:
          200:
            description: authorize target dataset by id
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.Dataset'
        """
        with db.session_scope() as session:
            dataset: Dataset = session.query(Dataset).get(dataset_id)
            if dataset is None:
                raise NotFoundException(f'Failed to find dataset: {dataset_id}')
            # update local auth_status
            dataset.auth_status = AuthStatus.AUTHORIZED
            if dataset.participants_info is not None:
                # update local auth_status cache
                AuthService(session=session, dataset_job=dataset.parent_dataset_job).update_auth_status(
                    domain_name=SettingService.get_system_info().pure_domain_name, auth_status=AuthStatus.AUTHORIZED)
                # update participants auth_status cache
                DatasetJobController(session=session).inform_auth_status(dataset_job=dataset.parent_dataset_job,
                                                                         auth_status=AuthStatus.AUTHORIZED)
            session.commit()
            return make_flask_response(data=dataset.to_proto())

    @credentials_required
    def delete(self, dataset_id: int):
        """Revoke dataset authorization by id
        ---
        tags:
          - dataset
        description: revoke dataset authorization by id
        parameters:
        - in: path
          name: dataset_id
          schema:
            type: integer
        responses:
          200:
            description: revoke dataset authorization by id successfully
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.Dataset'
        """
        with db.session_scope() as session:
            dataset: Dataset = session.query(Dataset).get(dataset_id)
            if dataset is None:
                raise NotFoundException(f'Failed to find dataset: {dataset_id}')
            # update local auth_status
            dataset.auth_status = AuthStatus.WITHDRAW
            if dataset.participants_info is not None:
                # update local auth_status cache
                AuthService(session=session, dataset_job=dataset.parent_dataset_job).update_auth_status(
                    domain_name=SettingService.get_system_info().pure_domain_name, auth_status=AuthStatus.WITHDRAW)
                # update participants auth_status cache
                DatasetJobController(session=session).inform_auth_status(dataset_job=dataset.parent_dataset_job,
                                                                         auth_status=AuthStatus.WITHDRAW)
            session.commit()
            return make_flask_response(data=dataset.to_proto())


class DatasetFlushAuthStatusApi(Resource):

    @credentials_required
    def post(self, dataset_id: int):
        """flush dataset auth status cache by id
        ---
        tags:
          - dataset
        description: flush dataset auth status cache by id
        parameters:
        - in: path
          name: dataset_id
          schema:
            type: integer
        responses:
          200:
            description: flush dataset auth status cache by id successfully
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.Dataset'
        """
        with db.session_scope() as session:
            dataset: Dataset = session.query(Dataset).get(dataset_id)
            if dataset is None:
                raise NotFoundException(f'Failed to find dataset: {dataset_id}')
            if dataset.participants_info is not None:
                DatasetJobController(session=session).update_auth_status_cache(dataset_job=dataset.parent_dataset_job)
            session.commit()
            return make_flask_response(data=dataset.to_proto())


class TimeRangeParameter(Schema):
    days = fields.Integer(required=False, load_default=0, validate=[validate.Range(min=0, max=1)])
    hours = fields.Integer(required=False, load_default=0, validate=[validate.Range(min=0, max=1)])

    @post_load
    def make_time_range(self, item: Dict[str, Any], **kwargs) -> dataset_pb2.TimeRange:
        days = item['days']
        hours = item['hours']

        return dataset_pb2.TimeRange(days=days, hours=hours)


class DatasetJobDefinitionApi(Resource):

    @credentials_required
    def get(self, dataset_job_kind: str):
        """Get variables of this dataset_job
        ---
        tags:
          - dataset
        description: Get variables of this dataset_job
        parameters:
        - in: path
          name: dataset_job_kind
          schema:
            type: string
        responses:
          200:
            description: variables of this dataset_job
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    variables:
                      type: array
                      items:
                        $ref: '#/definitions/fedlearner_webconsole.proto.Variable'
                    is_federated:
                      type: boolean
        """
        # webargs doesn't support location=path for now
        # reference: webargs/core.py:L285
        try:
            dataset_job_kind = DatasetJobKind(dataset_job_kind)
        except ValueError as err:
            raise InvalidArgumentException(details=f'unkown dataset_job_kind {dataset_job_kind}') from err
        with db.session_scope() as session:
            configer = DatasetJobConfiger.from_kind(dataset_job_kind, session)
            user_variables = configer.user_variables
            is_federated = not DatasetJobService(session).is_local(dataset_job_kind)
        return make_flask_response(data={'variables': user_variables, 'is_federated': is_federated})


class DatasetJobsApi(Resource):
    FILTER_FIELDS = {
        'name': filtering.SupportedField(type=filtering.FieldType.STRING, ops={FilterOp.CONTAIN: None}),
        'kind': filtering.SupportedField(type=filtering.FieldType.STRING, ops={FilterOp.IN: None}),
        'input_dataset_id': filtering.SupportedField(type=filtering.FieldType.NUMBER, ops={FilterOp.EQUAL: None}),
        'coordinator_id': filtering.SupportedField(type=filtering.FieldType.NUMBER, ops={FilterOp.IN: None}),
        'state': filtering.SupportedField(type=filtering.FieldType.STRING, ops={FilterOp.IN: None}),
    }

    SORTER_FIELDS = ['created_at']

    def __init__(self):
        self._filter_builder = filtering.FilterBuilder(model_class=DatasetJob, supported_fields=self.FILTER_FIELDS)
        self._sorter_builder = sorting.SorterBuilder(model_class=DatasetJob, supported_fields=self.SORTER_FIELDS)

    @credentials_required
    @use_kwargs(
        {
            'page': fields.Integer(required=False, load_default=1),
            'page_size': fields.Integer(required=False, load_default=10),
            'filter_exp': FilterExpField(required=False, load_default=None, data_key='filter'),
            'sorter_exp': fields.String(required=False, load_default=None, data_key='order_by'),
        },
        location='query')
    def get(self,
            project_id: int,
            page: int,
            page_size: int,
            filter_exp: Optional[FilterExpression] = None,
            sorter_exp: Optional[str] = None):
        """Get list of this dataset_jobs
        ---
        tags:
          - dataset
        description: Get list of this dataset_jobs
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: query
          name: filter
          schema:
            type: string
        - in: query
          name: order_by
          schema:
            type: string
        responses:
          200:
            description: list of this dataset_jobs
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.DatasetJobRef'
        """
        with db.session_scope() as session:
            query = session.query(DatasetJob).filter(DatasetJob.project_id == project_id)
            if filter_exp is not None:
                try:
                    query = self._filter_builder.build_query(query, filter_exp)
                except ValueError as e:
                    raise InvalidArgumentException(details=f'Invalid filter: {str(e)}') from e
            try:
                if sorter_exp is not None:
                    sorter_exp = sorting.parse_expression(sorter_exp)
                else:
                    sorter_exp = sorting.SortExpression(field='created_at', is_asc=False)
                query = self._sorter_builder.build_query(query, sorter_exp)
            except ValueError as e:
                raise InvalidArgumentException(details=f'Invalid sorter: {str(e)}') from e
            pagination = paginate(query=query, page=page, page_size=page_size)

            return make_flask_response(data=[dataset_job.to_ref() for dataset_job in pagination.get_items()],
                                       page_meta=pagination.get_metadata())

    @credentials_required
    @use_kwargs({
        'dataset_job_parameter': fields.Nested(DatasetJobParameter()),
        'output_dataset_id': fields.Integer(required=False, load_default=None),
        'time_range': fields.Nested(TimeRangeParameter(), required=False, load_default=dataset_pb2.TimeRange())
    })
    def post(self, project_id: int, dataset_job_parameter: dataset_pb2.DatasetJob, output_dataset_id: Optional[int],
             time_range: dataset_pb2.TimeRange):
        """Create new dataset job of the kind
        ---
        tags:
          - dataset
        description: Create new dataset job of the kind
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        requestBody:
          required: true
          content:
            application/json:
              schema:
                type: object
                properties:
                  dataset_job_parameter:
                    $ref: '#/definitions/DatasetJobParameter'
                  time_range:
                    $ref: '#/definitions/TimeRangeParameter'
        responses:
          201:
            description: Create new dataset job of the kind
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.DatasetJob'
        """
        dataset_job_kind = DatasetJobKind(dataset_job_parameter.kind)
        if not Flag.OT_PSI_ENABLED.value and dataset_job_kind == DatasetJobKind.OT_PSI_DATA_JOIN:
            raise NoAccessException(f'dataset job {dataset_job_parameter.kind} is not enabled')
        if not Flag.HASH_DATA_JOIN_ENABLED.value and dataset_job_kind == DatasetJobKind.HASH_DATA_JOIN:
            raise NoAccessException(f'dataset job {dataset_job_parameter.kind} is not enabled')

        global_configs = dataset_job_parameter.global_configs

        with db.session_scope() as session:
            output_dataset = session.query(Dataset).get(output_dataset_id)
            if not output_dataset:
                raise InvalidArgumentException(f'failed to find dataset: {output_dataset_id}')
            time_delta = None
            if output_dataset.dataset_type == DatasetType.STREAMING:
                if not (time_range.days > 0) ^ (time_range.hours > 0):
                    raise InvalidArgumentException('must specify cron by days or hours')
                time_delta = timedelta(days=time_range.days, hours=time_range.hours)
            dataset_job = DatasetJobService(session).create_as_coordinator(project_id=project_id,
                                                                           kind=dataset_job_kind,
                                                                           output_dataset_id=output_dataset.id,
                                                                           global_configs=global_configs,
                                                                           time_range=time_delta)
            session.flush()
            dataset_job_details = dataset_job.to_proto()

            # we set particiapnts_info in dataset_job api as we need get participants from dataset_kind
            particiapnts = DatasetJobService(session=session).get_participants_need_distribute(dataset_job=dataset_job)
            AuthService(session=session,
                        dataset_job=dataset_job).initialize_participants_info_as_coordinator(participants=particiapnts)
            # set need_create_stage to True for non-cron dataset_job,
            # we donot create stage here as we should promise no stage created before all particiapnts authorized
            if not dataset_job.is_cron():
                context = dataset_job.get_context()
                context.need_create_stage = True
                dataset_job.set_context(context)
            session.commit()

        return make_flask_response(dataset_job_details, status=HTTPStatus.CREATED)


class DatasetJobApi(Resource):

    @credentials_required
    def get(self, project_id: int, dataset_job_id: int):
        """Get detail of this dataset_job
        ---
        tags:
          - dataset
        description: Get detail of this dataset_job
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: path
          name: dataset_job_id
          schema:
            type: integer
        responses:
          200:
            description: detail of this dataset_job
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.DatasetJob'
        """
        with db.session_scope() as session:
            # TODO(wangsen.0914): move these logic into service
            dataset_job: DatasetJob = session.query(DatasetJob).filter_by(project_id=project_id).filter_by(
                id=dataset_job_id).first()
            if dataset_job is None:
                raise NotFoundException(f'failed to find datasetjob {dataset_job_id}')
            dataset_job_pb = dataset_job.to_proto()
            if not dataset_job.is_coordinator():
                participant = session.query(Participant).get(dataset_job.coordinator_id)
                client = RpcClient.from_project_and_participant(dataset_job.project.name, dataset_job.project.token,
                                                                participant.domain_name)
                response = client.get_dataset_job(uuid=dataset_job.uuid)
                dataset_job_pb.global_configs.MergeFrom(response.dataset_job.global_configs)
                dataset_job_pb.scheduler_state = response.dataset_job.scheduler_state
            return make_flask_response(dataset_job_pb)

    @credentials_required
    def delete(self, project_id: int, dataset_job_id: int):
        """Delete dataset_job by id
        ---
        tags:
          - dataset
        description: Delete dataset_job by id
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: path
          name: dataset_job_id
          schema:
            type: integer
        responses:
          204:
            description: delete dataset_job successfully
        """
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).filter_by(project_id=project_id).filter_by(
                id=dataset_job_id).first()
            if dataset_job is None:
                message = f'Failed to delete dataset_job: {dataset_job_id}; reason: failed to find dataset_job'
                logging.error(message)
                raise NotFoundException(message)
            DatasetJobService(session).delete_dataset_job(dataset_job=dataset_job)
            session.commit()
            return make_flask_response(status=HTTPStatus.NO_CONTENT)


class DatasetJobStopApi(Resource):

    @credentials_required
    def post(self, project_id: int, dataset_job_id: int):
        """Stop dataset_job by id
        ---
        tags:
          - dataset
        description: Stop dataset_job by id
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: path
          name: dataset_job_id
          schema:
            type: integer
        responses:
          200:
            description: stop dataset_job successfully
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.DatasetJob'
        """
        with db.session_scope() as session:
            dataset_job = session.query(DatasetJob).filter_by(project_id=project_id).filter_by(
                id=dataset_job_id).first()
            if dataset_job is None:
                raise NotFoundException(f'failed to find datasetjob {dataset_job_id}')
            DatasetJobController(session).stop(uuid=dataset_job.uuid)
            session.commit()
            return make_flask_response(data=dataset_job.to_proto())


class DatasetJobStopSchedulerApi(Resource):

    @credentials_required
    def post(self, project_id: int, dataset_job_id: int):
        """Stop scheduler dataset_job by id
        ---
        tags:
          - dataset
        description: Stop scheduler dataset_job by id
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: path
          name: dataset_job_id
          schema:
            type: integer
        responses:
          200:
            description: stop scheduler dataset_job successfully
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.DatasetJob'
        """
        with db.session_scope() as session:
            dataset_job: DatasetJob = session.query(DatasetJob).filter_by(project_id=project_id).filter_by(
                id=dataset_job_id).first()
            if dataset_job is None:
                raise NotFoundException(f'failed to find datasetjob {dataset_job_id}')
            if dataset_job.is_coordinator():
                DatasetJobService(session=session).stop_cron_scheduler(dataset_job=dataset_job)
                dataset_job_pb = dataset_job.to_proto()
            else:
                participant = session.query(Participant).get(dataset_job.coordinator_id)
                client = JobServiceClient.from_project_and_participant(participant.domain_name,
                                                                       dataset_job.project.name)
                client.update_dataset_job_scheduler_state(uuid=dataset_job.uuid,
                                                          scheduler_state=DatasetJobSchedulerState.STOPPED)
                client = RpcClient.from_project_and_participant(dataset_job.project.name, dataset_job.project.token,
                                                                participant.domain_name)
                response = client.get_dataset_job(uuid=dataset_job.uuid)
                dataset_job_pb = dataset_job.to_proto()
                dataset_job_pb.global_configs.MergeFrom(response.dataset_job.global_configs)
                dataset_job_pb.scheduler_state = response.dataset_job.scheduler_state
            session.commit()
        return make_flask_response(data=dataset_job_pb)


class DatasetJobStagesApi(Resource):

    FILTER_FIELDS = {
        'state': filtering.SupportedField(type=filtering.FieldType.STRING, ops={FilterOp.IN: None}),
    }

    SORTER_FIELDS = ['created_at']

    def __init__(self):
        self._filter_builder = filtering.FilterBuilder(model_class=DatasetJobStage, supported_fields=self.FILTER_FIELDS)
        self._sorter_builder = sorting.SorterBuilder(model_class=DatasetJobStage, supported_fields=self.SORTER_FIELDS)

    @credentials_required
    @use_kwargs(
        {
            'page': fields.Integer(required=False, load_default=1),
            'page_size': fields.Integer(required=False, load_default=10),
            'filter_exp': FilterExpField(required=False, load_default=None, data_key='filter'),
            'sorter_exp': fields.String(required=False, load_default=None, data_key='order_by')
        },
        location='query')
    def get(self, project_id: int, dataset_job_id: int, page: int, page_size: int,
            filter_exp: Optional[FilterExpression], sorter_exp: Optional[str]):
        """List dataset job stages
        ---
        tags:
          - dataset
        description: List dataset job stages
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: path
          name: dataset_job_id
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
          name: filter
          schema:
            type: string
        - in: query
          name: order_by
          schema:
            type: string
        responses:
          200:
            description: list of dataset job stages
            content:
              application/json:
                schema:
                  type: array
                  items:
                    $ref: '#/definitions/fedlearner_webconsole.proto.DatasetJobStageRef'
        """
        with db.session_scope() as session:
            query = session.query(DatasetJobStage).filter(DatasetJobStage.project_id == project_id).filter(
                DatasetJobStage.dataset_job_id == dataset_job_id)
            if filter_exp is not None:
                try:
                    query = self._filter_builder.build_query(query, filter_exp)
                except ValueError as e:
                    raise InvalidArgumentException(details=f'Invalid filter: {str(e)}') from e
            try:
                if sorter_exp is not None:
                    sorter_exp = sorting.parse_expression(sorter_exp)
                else:
                    # default sort is created_at desc
                    sorter_exp = sorting.SortExpression(field='created_at', is_asc=False)
                query = self._sorter_builder.build_query(query, sorter_exp)
            except ValueError as e:
                raise InvalidArgumentException(details=f'Invalid sorter: {str(e)}') from e
            pagination = paginate(query=query, page=page, page_size=page_size)
            return make_flask_response(
                data=[dataset_job_stage.to_ref() for dataset_job_stage in pagination.get_items()],
                page_meta=pagination.get_metadata())


class DatasetJobStageApi(Resource):

    @credentials_required
    def get(self, project_id: int, dataset_job_id: int, dataset_job_stage_id: int):
        """Get details of given dataset job stage
        ---
        tags:
          - dataset
        description: Get details of given dataset job stage
        parameters:
        - in: path
          name: project_id
          schema:
            type: integer
        - in: path
          name: dataset_job_id
          schema:
            type: integer
        - in: path
          name: dataset_job_stage_id
          schema:
            type: integer
        responses:
          200:
            description: dataset job stage details
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.DatasetJobStage'
        """
        with db.session_scope() as session:
            dataset_job_stage: DatasetJobStage = session.query(DatasetJobStage).filter(
                DatasetJobStage.project_id == project_id).filter(
                    DatasetJobStage.dataset_job_id == dataset_job_id).filter(
                        DatasetJobStage.id == dataset_job_stage_id).first()
            if not dataset_job_stage:
                raise NotFoundException(f'Failed to find dataset job stage: {dataset_job_stage_id}')
            dataset_job_stage_pb = dataset_job_stage.to_proto()
            if not dataset_job_stage.is_coordinator():
                participant = session.query(Participant).get(dataset_job_stage.coordinator_id)
                client = JobServiceClient.from_project_and_participant(participant.domain_name,
                                                                       dataset_job_stage.project.name)
                response = client.get_dataset_job_stage(dataset_job_stage_uuid=dataset_job_stage.uuid)
                dataset_job_stage_pb.global_configs.MergeFrom(response.dataset_job_stage.global_configs)

            return make_flask_response(dataset_job_stage_pb)


def initialize_dataset_apis(api: Api):
    api.add_resource(DatasetsApi, '/datasets')
    api.add_resource(DatasetApi, '/datasets/<int:dataset_id>')
    api.add_resource(DatasetPublishApi, '/datasets/<int:dataset_id>:publish')
    api.add_resource(DatasetAuthorizehApi, '/datasets/<int:dataset_id>:authorize')
    api.add_resource(DatasetFlushAuthStatusApi, '/datasets/<int:dataset_id>:flush_auth_status')
    api.add_resource(BatchesApi, '/datasets/<int:dataset_id>/batches')
    api.add_resource(BatchApi, '/datasets/<int:dataset_id>/batches/<int:data_batch_id>')
    api.add_resource(ChildrenDatasetsApi, '/datasets/<int:dataset_id>/children_datasets')
    api.add_resource(BatchAnalyzeApi, '/datasets/<int:dataset_id>/batches/<int:data_batch_id>:analyze')
    api.add_resource(BatchMetricsApi, '/datasets/<int:dataset_id>/batches/<int:data_batch_id>/feature_metrics')
    api.add_resource(BatchRerunApi, '/datasets/<int:dataset_id>/batches/<int:data_batch_id>:rerun')
    api.add_resource(DatasetPreviewApi, '/datasets/<int:dataset_id>/preview')
    api.add_resource(DatasetLedgerApi, '/datasets/<int:dataset_id>/ledger')
    api.add_resource(DatasetExportApi, '/datasets/<int:dataset_id>:export')
    api.add_resource(DatasetStateFixtApi, '/datasets/<int:dataset_id>:state_fix')

    api.add_resource(DataSourcesApi, '/data_sources')
    api.add_resource(DataSourceApi, '/data_sources/<int:data_source_id>')
    api.add_resource(DataSourceCheckConnectionApi, '/data_sources:check_connection')
    api.add_resource(DataSourceTreeApi, '/data_sources/<int:data_source_id>/tree')

    api.add_resource(ParticipantDatasetsApi, '/project/<int:project_id>/participant_datasets')

    api.add_resource(DatasetJobDefinitionApi, '/dataset_job_definitions/<string:dataset_job_kind>')
    api.add_resource(DatasetJobsApi, '/projects/<int:project_id>/dataset_jobs')
    api.add_resource(DatasetJobApi, '/projects/<int:project_id>/dataset_jobs/<int:dataset_job_id>')
    api.add_resource(DatasetJobStopApi, '/projects/<int:project_id>/dataset_jobs/<int:dataset_job_id>:stop')
    api.add_resource(DatasetJobStopSchedulerApi,
                     '/projects/<int:project_id>/dataset_jobs/<int:dataset_job_id>:stop_scheduler')

    api.add_resource(DatasetJobStagesApi,
                     '/projects/<int:project_id>/dataset_jobs/<int:dataset_job_id>/dataset_job_stages')
    api.add_resource(
        DatasetJobStageApi,
        '/projects/<int:project_id>/dataset_jobs/<int:dataset_job_id>/dataset_job_stages/<int:dataset_job_stage_id>')

    schema_manager.append(DataSourceParameter)
    schema_manager.append(DatasetJobConfigParameter)
    schema_manager.append(DatasetParameter)
    schema_manager.append(BatchParameter)
    schema_manager.append(DatasetJobParameter)
    schema_manager.append(TimeRangeParameter)
