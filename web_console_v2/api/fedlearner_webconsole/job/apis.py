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
import json
import logging
import time
from typing import Optional

from flask_restful import Resource, reqparse
from google.protobuf.json_format import MessageToDict
from webargs.flaskparser import use_kwargs
from marshmallow import fields

from sqlalchemy.orm.session import Session
from envs import Envs
from fedlearner_webconsole.db import db
from fedlearner_webconsole.exceptions import (NotFoundException, InternalException, InvalidArgumentException)
from fedlearner_webconsole.job.metrics import JobMetricsBuilder
from fedlearner_webconsole.job.models import Job
from fedlearner_webconsole.job.service import JobService
from fedlearner_webconsole.participant.models import Participant
from fedlearner_webconsole.proto import common_pb2
from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.auth.third_party_sso import credentials_required
from fedlearner_webconsole.utils.es import es
from fedlearner_webconsole.utils.kibana import Kibana
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.utils.flask_utils import make_flask_response


def _get_job(job_id, session: Session):
    result = session.query(Job).filter_by(id=job_id).first()
    if result is None:
        raise NotFoundException(f'Failed to find job_id: {job_id}')
    return result


class JobApi(Resource):

    @credentials_required
    def get(self, job_id):
        """Get job details.
        ---
        tags:
          - job
        description: Get job details.
        parameters:
          - in: path
            name: job_id
            schema:
              type: integer
        responses:
          200:
            description: Detail of job
            content:
              application/json:
                schema:
                  $ref: '#/definitions/fedlearner_webconsole.proto.JobPb'
        """
        with db.session_scope() as session:
            job = _get_job(job_id, session)
            result = job.to_proto()
            result.pods.extend(JobService.get_pods(job))
            result.snapshot = JobService.get_job_yaml(job)
            return make_flask_response(result)


class PodLogApi(Resource):

    @credentials_required
    @use_kwargs({
        'start_time': fields.Int(required=False, load_default=None),
        'max_lines': fields.Int(required=True)
    },
                location='query')
    def get(self, start_time: Optional[int], max_lines: int, job_id: int, pod_name: str):
        """Get pod logs.
        ---
        tags:
          - job
        description: Get pod logs.
        parameters:
          - in: path
            name: job_id
            schema:
              type: integer
          - in: path
            name: pod_name
            schema:
              type: string
          - in: query
            description: timestamp in seconds
            name: start_time
            schema:
              type: integer
          - in: query
            name: max_lines
            schema:
              type: integer
            required: true
        responses:
          200:
            description: List of pod logs
            content:
              application/json:
                schema:
                  type: array
                  items:
                    type: string

        """
        with db.session_scope() as session:
            job = _get_job(job_id, session)
            if start_time is None and job.workflow:
                start_time = job.workflow.start_at
        return make_flask_response(
            es.query_log(Envs.ES_INDEX, '', pod_name, (start_time or 0) * 1000)[:max_lines][::-1])


class JobLogApi(Resource):

    @credentials_required
    @use_kwargs({
        'start_time': fields.Int(required=False, load_default=None),
        'max_lines': fields.Int(required=True)
    },
                location='query')
    def get(self, start_time: Optional[int], max_lines: int, job_id: int):
        """Get job logs.
        ---
        tags:
          - job
        description: Get job logs.
        parameters:
          - in: path
            name: job_id
            schema:
              type: integer
          - in: query
            description: timestamp in seconds
            name: start_time
            schema:
              type: integer
          - in: query
            name: max_lines
            schema:
              type: integer
            required: true
        responses:
          200:
            description: List of job logs
            content:
              application/json:
                schema:
                  type: array
                  items:
                    type: string
        """
        with db.session_scope() as session:
            job = _get_job(job_id, session)
            if start_time is None and job.workflow:
                start_time = job.workflow.start_at
        return make_flask_response(
            es.query_log(Envs.ES_INDEX,
                         job.name,
                         'fedlearner-operator', (start_time or 0) * 1000,
                         match_phrase=Envs.OPERATOR_LOG_MATCH_PHRASE)[:max_lines][::-1])


class JobMetricsApi(Resource):

    @credentials_required
    @use_kwargs({
        'raw': fields.Bool(required=False, load_default=False),
    }, location='query')
    def get(self, job_id: int, raw: bool):
        """Get job Metrics.
        ---
        tags:
          - job
        description: Get job metrics.
        parameters:
          - in: path
            name: job_id
            schema:
              type: integer
          - in: query
            name: raw
            schema:
              type: boolean
        responses:
          200:
            description: List of job metrics
            content:
              application/json:
                schema:
                  type: array
                  items:
                    type: object
        """
        with db.session_scope() as session:
            job = _get_job(job_id, session)
            try:
                builder = JobMetricsBuilder(job)
                if raw:
                    return make_flask_response(data=builder.query_metrics())
                # Metrics is a list of dict. Each dict can be rendered by frontend
                # with mpld3.draw_figure('figure1', json)
                return make_flask_response(data=builder.plot_metrics())
            except Exception as e:  # pylint: disable=broad-except
                logging.warning('Error building metrics: %s', repr(e))
                raise InvalidArgumentException(details=repr(e)) from e


class PeerJobMetricsApi(Resource):

    @credentials_required
    def get(self, workflow_uuid: str, participant_id: int, job_name: str):
        """Get peer job metrics.
        ---
        tags:
          - job
        description: Get peer Job metrics.
        parameters:
          - in: path
            name: workflow_uuid
            schema:
              type: string
          - in: path
            name: participant_id
            schema:
              type: integer
          - in: path
            name: job_name
            schema:
              type: string
        responses:
          200:
            description: List of job metrics
            content:
              application/json:
                schema:
                  type: array
                  items:
                    type: object
        """
        with db.session_scope() as session:
            workflow = session.query(Workflow).filter_by(uuid=workflow_uuid).first()
            if workflow is None:
                raise NotFoundException(f'Failed to find workflow: {workflow_uuid}')
            participant = session.query(Participant).filter_by(id=participant_id).first()
            client = RpcClient.from_project_and_participant(workflow.project.name, workflow.project.token,
                                                            participant.domain_name)
            resp = client.get_job_metrics(job_name)
            if resp.status.code != common_pb2.STATUS_SUCCESS:
                raise InternalException(resp.status.msg)

            metrics = json.loads(resp.metrics)

            # Metrics is a list of dict. Each dict can be rendered by frontend with
            #   mpld3.draw_figure('figure1', json)
            return make_flask_response(metrics)


class JobEventApi(Resource):
    # TODO(xiangyuxuan): need test
    @credentials_required
    @use_kwargs({
        'start_time': fields.Int(required=False, load_default=None),
        'max_lines': fields.Int(required=True)
    },
                location='query')
    def get(self, start_time: Optional[int], max_lines: int, job_id: int):
        """Get job events.
        ---
        tags:
          - job
        description: Get job events.
        parameters:
          - in: path
            name: job_id
            schema:
              type: integer
          - in: query
            description: timestamp in seconds
            name: start_time
            schema:
              type: integer
          - in: query
            name: max_lines
            schema:
              type: integer
            required: true
        responses:
          200:
            description: List of job events
            content:
              application/json:
                schema:
                  type: array
                  items:
                    type: string
        """
        with db.session_scope() as session:
            job = _get_job(job_id, session)
            if start_time is None and job.workflow:
                start_time = job.workflow.start_at
        return make_flask_response(
            es.query_events(Envs.ES_INDEX, job.name, 'fedlearner-operator', start_time, int(time.time() * 1000),
                            Envs.OPERATOR_LOG_MATCH_PHRASE)[:max_lines][::-1])


class PeerJobEventsApi(Resource):

    @credentials_required
    @use_kwargs({
        'start_time': fields.Int(required=False, load_default=None),
        'max_lines': fields.Int(required=True)
    },
                location='query')
    def get(self, start_time: Optional[int], max_lines: int, workflow_uuid: str, participant_id: int, job_name: str):
        """Get peer job events.
        ---
        tags:
          - job
        description: Get peer job events.
        parameters:
          - in: path
            name: workflow_uuid
            schema:
              type: string
          - in: path
            name: participant_id
            schema:
              type: integer
          - in: path
            name: job_name
            schema:
              type: string
        responses:
          200:
            description: List of peer job events
            content:
              application/json:
                schema:
                  type: array
                  items:
                    type: string
        """
        with db.session_scope() as session:
            workflow = session.query(Workflow).filter_by(uuid=workflow_uuid).first()
            if workflow is None:
                raise NotFoundException(f'Failed to find workflow: {workflow_uuid}')
            if start_time is None:
                start_time = workflow.start_at
            participant = session.query(Participant).filter_by(id=participant_id).first()
            client = RpcClient.from_project_and_participant(workflow.project.name, workflow.project.token,
                                                            participant.domain_name)
            resp = client.get_job_events(job_name=job_name, start_time=start_time, max_lines=max_lines)
            if resp.status.code != common_pb2.STATUS_SUCCESS:
                raise InternalException(resp.status.msg)
            peer_events = MessageToDict(resp, preserving_proto_field_name=True,
                                        including_default_value_fields=True)['logs']
            return make_flask_response(peer_events)


class KibanaMetricsApi(Resource):

    @credentials_required
    def get(self, job_id):
        parser = reqparse.RequestParser()
        parser.add_argument('type',
                            type=str,
                            location='args',
                            required=True,
                            choices=('Rate', 'Ratio', 'Numeric', 'Time', 'Timer'),
                            help='Visualization type is required. Choices: '
                            'Rate, Ratio, Numeric, Time, Timer')
        parser.add_argument('interval',
                            type=str,
                            location='args',
                            default='',
                            help='Time bucket interval length, '
                            'defaults to be automated by Kibana.')
        parser.add_argument('x_axis_field',
                            type=str,
                            location='args',
                            default='tags.event_time',
                            help='Time field (X axis) is required.')
        parser.add_argument('query', type=str, location='args', help='Additional query string to the graph.')
        parser.add_argument('start_time',
                            type=int,
                            location='args',
                            default=-1,
                            help='Earliest <x_axis_field> time of data.'
                            'Unix timestamp in secs.')
        parser.add_argument('end_time',
                            type=int,
                            location='args',
                            default=-1,
                            help='Latest <x_axis_field> time of data.'
                            'Unix timestamp in secs.')
        # (Joined) Rate visualization is fixed and only interval, query and
        # x_axis_field can be modified
        # Ratio visualization
        parser.add_argument('numerator',
                            type=str,
                            location='args',
                            help='Numerator is required in Ratio '
                            'visualization. '
                            'A query string similar to args::query.')
        parser.add_argument('denominator',
                            type=str,
                            location='args',
                            help='Denominator is required in Ratio '
                            'visualization. '
                            'A query string similar to args::query.')
        # Numeric visualization
        parser.add_argument('aggregator',
                            type=str,
                            location='args',
                            default='Average',
                            choices=('Average', 'Sum', 'Max', 'Min', 'Variance', 'Std. Deviation', 'Sum of Squares'),
                            help='Aggregator type is required in Numeric and '
                            'Timer visualization.')
        parser.add_argument('value_field',
                            type=str,
                            location='args',
                            help='The field to be aggregated on is required '
                            'in Numeric visualization.')
        # No additional arguments in Time visualization
        #
        # Timer visualization
        parser.add_argument('timer_names',
                            type=str,
                            location='args',
                            help='Names of timers is required in '
                            'Timer visualization.')
        parser.add_argument('split', type=int, location='args', default=0, help='Whether to plot timers individually.')
        args = parser.parse_args()
        with db.session_scope() as session:
            job = _get_job(job_id, session)
            try:
                if args['type'] in Kibana.TSVB:
                    return {'data': Kibana.create_tsvb(job, args)}
                if args['type'] in Kibana.TIMELION:
                    return {'data': Kibana.create_timelion(job, args)}
                return {'data': []}
            except Exception as e:  # pylint: disable=broad-except
                raise InvalidArgumentException(details=repr(e)) from e


class PeerKibanaMetricsApi(Resource):

    @credentials_required
    def get(self, workflow_uuid, participant_id, job_name):
        parser = reqparse.RequestParser()
        parser.add_argument('type',
                            type=str,
                            location='args',
                            required=True,
                            choices=('Ratio', 'Numeric'),
                            help='Visualization type is required. Choices: '
                            'Rate, Ratio, Numeric, Time, Timer')
        parser.add_argument('interval',
                            type=str,
                            location='args',
                            default='',
                            help='Time bucket interval length, '
                            'defaults to be automated by Kibana.')
        parser.add_argument('x_axis_field',
                            type=str,
                            location='args',
                            default='tags.event_time',
                            help='Time field (X axis) is required.')
        parser.add_argument('query', type=str, location='args', help='Additional query string to the graph.')
        parser.add_argument('start_time',
                            type=int,
                            location='args',
                            default=-1,
                            help='Earliest <x_axis_field> time of data.'
                            'Unix timestamp in secs.')
        parser.add_argument('end_time',
                            type=int,
                            location='args',
                            default=-1,
                            help='Latest <x_axis_field> time of data.'
                            'Unix timestamp in secs.')
        # Ratio visualization
        parser.add_argument('numerator',
                            type=str,
                            location='args',
                            help='Numerator is required in Ratio '
                            'visualization. '
                            'A query string similar to args::query.')
        parser.add_argument('denominator',
                            type=str,
                            location='args',
                            help='Denominator is required in Ratio '
                            'visualization. '
                            'A query string similar to args::query.')
        # Numeric visualization
        parser.add_argument('aggregator',
                            type=str,
                            location='args',
                            default='Average',
                            choices=('Average', 'Sum', 'Max', 'Min', 'Variance', 'Std. Deviation', 'Sum of Squares'),
                            help='Aggregator type is required in Numeric and '
                            'Timer visualization.')
        parser.add_argument('value_field',
                            type=str,
                            location='args',
                            help='The field to be aggregated on is required '
                            'in Numeric visualization.')
        args = parser.parse_args()
        with db.session_scope() as session:
            workflow = session.query(Workflow).filter_by(uuid=workflow_uuid).first()
            if workflow is None:
                raise NotFoundException(f'Failed to find workflow: {workflow_uuid}')
            participant = session.query(Participant).filter_by(id=participant_id).first()
            client = RpcClient.from_project_and_participant(workflow.project.name, workflow.project.token,
                                                            participant.domain_name)
            resp = client.get_job_kibana(job_name, json.dumps(args))
            if resp.status.code != common_pb2.STATUS_SUCCESS:
                raise InternalException(resp.status.msg)
            metrics = json.loads(resp.metrics)
            # metrics is a list of 2-element lists,
            #   each 2-element list is a [x, y] pair.
            return {'data': metrics}


def initialize_job_apis(api):
    api.add_resource(JobApi, '/jobs/<int:job_id>')
    api.add_resource(PodLogApi, '/jobs/<int:job_id>/pods/<string:pod_name>/log')
    api.add_resource(JobLogApi, '/jobs/<int:job_id>/log')
    api.add_resource(JobMetricsApi, '/jobs/<int:job_id>/metrics')
    api.add_resource(KibanaMetricsApi, '/jobs/<int:job_id>/kibana_metrics')
    api.add_resource(
        PeerJobMetricsApi, '/workflows/<string:workflow_uuid>/peer_workflows'
        '/<int:participant_id>/jobs/<string:job_name>/metrics')
    api.add_resource(
        PeerKibanaMetricsApi, '/workflows/<string:workflow_uuid>/peer_workflows'
        '/<int:participant_id>/jobs/<string:job_name>'
        '/kibana_metrics')
    api.add_resource(JobEventApi, '/jobs/<int:job_id>/events')
    api.add_resource(
        PeerJobEventsApi, '/workflows/<string:workflow_uuid>/peer_workflows'
        '/<int:participant_id>/jobs/<string:job_name>/events')
