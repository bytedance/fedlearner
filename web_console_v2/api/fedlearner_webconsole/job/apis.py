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
import time
import json
from google.protobuf.json_format import MessageToDict
from flask_restful import Resource, reqparse
from fedlearner_webconsole.proto import common_pb2
from fedlearner_webconsole.workflow.models import Workflow
from fedlearner_webconsole.job.models import Job
from fedlearner_webconsole.job.metrics import JobMetricsBuilder
from fedlearner_webconsole.utils.es import es
from fedlearner_webconsole.exceptions import (
    NotFoundException, InternalException
)
from fedlearner_webconsole.rpc.client import RpcClient


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
        return {'data': es.query_log('filebeat-*', '', pod_name,
                                     start_time,
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
        return {'data': es.query_log('filebeat-*', job.name,
                                     'fedlearner-operator',
                                     start_time,
                                     int(time.time() * 1000))[:max_lines][::-1]}


class JobMetricsApi(Resource):
    def get(self, job_id):
        job = _get_job(job_id)

        metrics = JobMetricsBuilder(job).plot_metrics()

        # Metrics is a list of dict. Each dict can be rendered by frontend with
        #   mpld3.draw_figure('figure1', json)
        return {'data': metrics}


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
                                            ))[:max_lines][::-1]}


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
            resp.logs,
            preserving_proto_field_name=True,
            including_default_value_fields=True)
        return {'data': peer_events}


class KibanaMetricsApi(Resource):
    def get(self, job_id):
        job = Job.query.filter_by(id=job_id).first()
        parser = reqparse.RequestParser()
        parser.add_argument('type', type=str, location='args',
                            required=True,
                            choices=('Rate', 'Ratio', 'Numeric'),
                            help='Visualization type is required.')
        parser.add_argument('interval', type=str, location='args',
                            default='',
                            help='Time bucket interval length, '
                                 'defaults to automated by Kibana.')
        parser.add_argument('time_field', type=str, location='args',
                            required=True,
                            help='Time field (X axis) is required.')
        parser.add_argument('earliest_time', type=str, location='args',
                            default='5y',
                            help='Earliest <time_field> time relative to now '
                                 'of all ES logs.')
        parser.add_argument('latest_time', type=str, location='args',
                            default='',
                            help='Latest <time_field> time relative to now of '
                                 'all ES logs.')
        # (Joined) Rate visualization is fixed and only interval and time_field
        # can be modified
        # Ratio visualization
        parser.add_argument('numerator', type=str, location='args',
                            help='Numerator is required in Ratio '
                                 'visualizations.')
        parser.add_argument('denominator', type=str, location='args',
                            help='Denominator is required in Ratio '
                                 'visualizations.')
        # Numeric visualization
        parser.add_argument('aggregation', type=str, location='args',
                            default='Average',
                            choices=('Average', 'Sum', 'Max', 'Min', 'Variance',
                                     'Std. Deviation', 'Sum of Squares'),
                            help='Aggregation type is required in Numeric '
                                 'visualizations.')
        parser.add_argument('field', type=str, location='args',
                            default='value',
                            help='The field to be aggregated is required '
                                 'in Numeric visualizations.')
        parser.add_argument('metrics', type=str, locations='args',
                            default='auc',
                            help='Name of the metrics should be provided, '
                                 'e.g., auc.')
        args = parser.parse_args()

        auth = (Config.ES_USERNAME, Config.ES_PASSWORD) \
            if Config.ES_USERNAME is not None else None
        objects_found = requests.get(
            '{kbn_addr}/api/saved_objects/_find?type=visualization'
            '&search_fields=title&search={type}-template-DO-NOT-MODIFY'
            .format(kbn_addr=Config.KIBANA_ADDRESS, type=args['type']),
            auth=auth
        ).json()
        assert objects_found['total'] > 0, \
            'Visualization type {} not set yet.'.format(args['type'])
        object_id = objects_found['saved_objects'][0]['id']
        object_vis_state = json.loads(
            objects_found['saved_objects'][0]['attributes']['visState']
        )
        params = object_vis_state['params']
        params['interval'] = args['interval']
        params['time_field'] = args['time_field']
        if job.job_type == JobType.DATA_JOIN \
                or job.job_type == JobType.RAW_DATA:
            params['filter']['query'] = 'application_id:"{}"'.format(job.name)
        else:
            params['filter']['query'] = 'tags.application_id.keyword:' \
                                        '"{}"'.format(job.name)
        # (Join) Rate visualization is fixed and no need to process
        if args['type'] == 'Ratio':
            for series in params['series']:
                series_type = series['label'].lower()
                if series_type == 'ratio':
                    series['metrics'][0]['numerator'] = args['numerator']
                    series['metrics'][0]['denominator'] = args['denominator']
                else:
                    assert series_type in ('denominator', 'numerator')
                    series['filter']['query'] = args[series_type]
        elif args['type'] == 'Numeric':
            params['filter']['query'] += ' and name.keyword: "{name}"' \
                .format(name=args['metrics'])
            series = params['series'][0]
            series['metrics'][0]['type'] = AGG_TYPE_MAP[args['aggregation']]
            series['metrics'][0]['field'] = args['field']
        rison_str = prison.dumps(object_vis_state)
        suffix = self._rison_postprocess(rison_str)

        iframe_src = "{kbn_addr}/app/kibana#/visualize/edit/" \
                     "{object_id}?embed=true&" \
                     "_g=(refreshInterval:(pause:!t,value:0)," \
                     "time:(from:now-{earliest},to:now-{latest}))&" \
                     "_a=(filters:!(),linked:!f," \
                     "query:(language:kuery,query:''),uiState:()," \
                     "vis:{vis_state})" \
            .format(kbn_addr=Config.KIBANA_ADDRESS,
                    earliest=args['earliest_time'],
                    latest=args['latest_time'],
                    object_id=object_id, vis_state=suffix)
        return iframe_src

    @staticmethod
    def _rison_postprocess(rison_str):
        re_mode = re.IGNORECASE
        escaped_keys = map(re.escape, RISON_REPLACEMENT)
        pattern = re.compile("|".join(escaped_keys), re_mode)
        return pattern.sub(
            lambda match: RISON_REPLACEMENT[match.group(0)], rison_str)


def initialize_job_apis(api):
    api.add_resource(JobApi, '/jobs/<int:job_id>')
    api.add_resource(PodLogApi,
                     '/jobs/<int:job_id>/pods/<string:pod_name>/log')
    api.add_resource(JobLogApi,
                     '/jobs/<int:job_id>/log')
    api.add_resource(JobMetricsApi,
                     '/jobs/<int:job_id>/metrics')
    api.add_resource(PodContainerApi,
                     '/jobs/<int:job_id>/pods/<string:pod_name>/container')
    api.add_resource(JobMetricsApi,
                     '/jobs/<int:job_id>/metrics')
    api.add_resource(PeerJobMetricsApi,
                     '/workflows/<string:workflow_uuid>/peer_workflows'
                     '/<int:participant_id>/jobs/<string:job_name>/metrics')
    api.add_resource(JobEventApi, '/jobs/<int:job_id>/events')
    api.add_resource(PeerJobEventsApi,
                     '/workflows/<string:workflow_uuid>/peer_workflows'
                     '/<int:participant_id>/jobs/<string:job_name>/events')
    api.add_resource(KibanaMetricsApi,
                     '/jobs/<int:job_id>/kibana')
