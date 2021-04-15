# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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
import time
import logging

from flask_restful import Resource, reqparse, abort
from google.protobuf.json_format import MessageToDict

from fedlearner_webconsole.exceptions import (
    NotFoundException, InternalException
)
from fedlearner_webconsole.job.metrics import JobMetricsBuilder
from fedlearner_webconsole.job.models import Job
from fedlearner_webconsole.proto import common_pb2
from fedlearner_webconsole.rpc.client import RpcClient
from fedlearner_webconsole.utils.es import es
from fedlearner_webconsole.utils.kibana import KibanaUtils
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.envs import Envs


def _get_job(job_id):
    result = Job.query.filter_by(id=job_id).first()
    if result is None:
        raise NotFoundException()
    return result

class JobApi(Resource):
    def get(self, job_id):
        job = _get_job(job_id)
        return {'data': job.to_dict()}

    # TODO: manual start jobs


class PodLogApi(Resource):
    def get(self, job_id, pod_name):
        parser = reqparse.RequestParser()
        parser.add_argument('start_time', type=int, location='args',
                            required=False,
                            help='start_time must be timestamp')
        parser.add_argument('max_lines', type=int, location='args',
                    required=True,
                    help='max_lines is required')
        data = parser.parse_args()
        start_time = data['start_time']
        max_lines = data['max_lines']
        job = _get_job(job_id)
        if start_time is None:
            start_time = job.workflow.start_at
        return {'data': es.query_log(Envs.ES_INDEX, '', pod_name,
                                     start_time * 1000,
                                     int(time.time() * 1000))[:max_lines][::-1]}


class JobLogApi(Resource):
    def get(self, job_id):
        parser = reqparse.RequestParser()
        parser.add_argument('start_time', type=int, location='args',
                            required=False,
                            help='project_id must be timestamp')
        parser.add_argument('max_lines', type=int, location='args',
                            required=True,
                            help='max_lines is required')
        data = parser.parse_args()
        start_time = data['start_time']
        max_lines = data['max_lines']
        job = _get_job(job_id)
        if start_time is None:
            start_time = job.workflow.start_at
        return {
            'data': es.query_log(
                Envs.ES_INDEX, job.name,
                'fedlearner-operator',
                start_time * 1000,
                int(time.time() * 1000),
                Envs.OPERATOR_LOG_MATCH_PHRASE)[:max_lines][::-1]
        }


class JobMetricsApi(Resource):
    def get(self, job_id):
        job = _get_job(job_id)
        try:
            metrics = JobMetricsBuilder(job).plot_metrics()
            # Metrics is a list of dict. Each dict can be rendered by frontend
            # with mpld3.draw_figure('figure1', json)
            return {'data': metrics}
        except Exception as e:  # pylint: disable=broad-except
            logging.warning('Error building metrics: %s', repr(e))
            abort(400, message=repr(e))


class PeerJobMetricsApi(Resource):
    def get(self, workflow_uuid, participant_id, job_name):
        workflow = Workflow.query.filter_by(uuid=workflow_uuid).first()
        if workflow is None:
            raise NotFoundException()
        project_config = workflow.project.get_config()
        party = project_config.participants[participant_id]
        client = RpcClient(project_config, party)
        resp = client.get_job_metrics(job_name)
        if resp.status.code != common_pb2.STATUS_SUCCESS:
            raise InternalException(resp.status.msg)

        metrics = json.loads(resp.metrics)

        # Metrics is a list of dict. Each dict can be rendered by frontend with
        #   mpld3.draw_figure('figure1', json)
        return {'data': metrics}


class JobEventApi(Resource):
    # TODO(xiangyuxuan): need test
    def get(self, job_id):
        parser = reqparse.RequestParser()
        parser.add_argument('start_time', type=int, location='args',
                            required=False,
                            help='start_time must be timestamp')
        parser.add_argument('max_lines', type=int, location='args',
                            required=True,
                            help='max_lines is required')
        data = parser.parse_args()
        start_time = data['start_time']
        max_lines = data['max_lines']
        job = _get_job(job_id)
        if start_time is None:
            start_time = job.workflow.start_at
        return {'data': es.query_events('filebeat-*', job.name,
                                        'fedlearner-operator',
                                        start_time,
                                        int(time.time() * 1000
                                            ),
                                        json.loads(
                                            Envs.OPERATOR_LOG_MATCH_PHRASE)
                                        )[:max_lines][::-1]}


class PeerJobEventsApi(Resource):
    def get(self, workflow_uuid, participant_id, job_name):
        parser = reqparse.RequestParser()
        parser.add_argument('start_time', type=int, location='args',
                            required=False,
                            help='project_id must be timestamp')
        parser.add_argument('max_lines', type=int, location='args',
                            required=True,
                            help='max_lines is required')
        data = parser.parse_args()
        start_time = data['start_time']
        max_lines = data['max_lines']
        workflow = Workflow.query.filter_by(uuid=workflow_uuid).first()
        if workflow is None:
            raise NotFoundException()
        if start_time is None:
            start_time = workflow.start_at
        project_config = workflow.project.get_config()
        party = project_config.participants[participant_id]
        client = RpcClient(project_config, party)
        resp = client.get_job_events(job_name=job_name,
                                     start_time=start_time,
                                     max_lines=max_lines)
        if resp.status.code != common_pb2.STATUS_SUCCESS:
            raise InternalException(resp.status.msg)
        peer_events = MessageToDict(
            resp,
            preserving_proto_field_name=True,
            including_default_value_fields=True)['logs']
        return {'data': peer_events}


class KibanaMetricsApi(Resource):
    def get(self, job_id):
        job = _get_job(job_id)
        parser = reqparse.RequestParser()
        parser.add_argument('type', type=str, location='args',
                            required=True,
                            choices=('Rate', 'Ratio', 'Numeric',
                                     'Time', 'Timer'),
                            help='Visualization type is required. Choices: '
                                 'Rate, Ratio, Numeric, Time, Timer')
        parser.add_argument('interval', type=str, location='args',
                            default='',
                            help='Time bucket interval length, '
                                 'defaults to automated by Kibana.')
        parser.add_argument('x_axis_field', type=str, location='args',
                            default='tags.event_time',
                            help='Time field (X axis) is required.')
        parser.add_argument('query', type=str, location='args',
                            help='Additional query string to the graph.')
        parser.add_argument('start_time', type=int, location='args',
                            default=-1,
                            help='Earliest <x_axis_field> time of data.'
                                 'Unix timestamp.')
        parser.add_argument('end_time', type=int, location='args',
                            default=-1,
                            help='Latest <x_axis_field> time of data.'
                                 'Unix timestamp.')
        # (Joined) Rate visualization is fixed and only interval, query and
        # x_axis_field can be modified
        # Ratio visualization
        parser.add_argument('numerator', type=str, location='args',
                            help='Numerator is required in Ratio '
                                 'visualization.')
        parser.add_argument('denominator', type=str, location='args',
                            help='Denominator is required in Ratio '
                                 'visualization.')
        # Numeric visualization
        parser.add_argument('aggregator', type=str, location='args',
                            default='Average',
                            choices=('Average', 'Sum', 'Max', 'Min', 'Variance',
                                     'Std. Deviation', 'Sum of Squares'),
                            help='Aggregator type is required in Numeric and '
                                 'Timer visualization.')
        parser.add_argument('value_field', type=str, location='args',
                            help='The field to be aggregated on is required '
                                 'in Numeric visualization.')
        # No additional arguments in Time visualization
        #
        # Timer visualization
        parser.add_argument('timer_names', type=str, location='args',
                            action='append',
                            help='Names of timers is required in '
                                 'Timer visualization.')
        args = parser.parse_args()
        try:
            if args['type'] in KibanaUtils.TSVB:
                return {'data': KibanaUtils.create_tsvb(job, args)}
            if args['type'] in KibanaUtils.TIMELION:
                return {'data': KibanaUtils.create_timelion(job, args)}
            return {'data': []}
        except Exception as e:  # pylint: disable=broad-except
            abort(400, message=repr(e))


def initialize_job_apis(api):
    api.add_resource(JobApi, '/jobs/<int:job_id>')
    api.add_resource(PodLogApi,
                     '/jobs/<int:job_id>/pods/<string:pod_name>/log')
    api.add_resource(JobLogApi,
                     '/jobs/<int:job_id>/log')
    api.add_resource(JobMetricsApi,
                     '/jobs/<int:job_id>/metrics')
    api.add_resource(KibanaMetricsApi,
                     '/jobs/<int:job_id>/kibana_metrics')
    api.add_resource(PeerJobMetricsApi,
                     '/workflows/<string:workflow_uuid>/peer_workflows'
                     '/<int:participant_id>/jobs/<string:job_name>/metrics')
    api.add_resource(JobEventApi, '/jobs/<int:job_id>/events')
    api.add_resource(PeerJobEventsApi,
                     '/workflows/<string:workflow_uuid>/peer_workflows'
                     '/<int:participant_id>/jobs/<string:job_name>/events')
