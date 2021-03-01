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

import copy
import hashlib
import json
import re
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
    RISON_REPLACEMENT = {
        # some URL rules in Kibana's URL encoding
        ' ': '%20',
        '"': '%22',
        '#': '%23',
        '%': '%25',
        '&': '%26',
        '+': '%2B',
        '/': '%2F'
    }
    AGG_TYPE_MAP = {'Average': 'avg',
                    'Sum': 'sum',
                    'Max': 'max',
                    'Min': 'min',
                    'Variance': 'variance',
                    'Std. Deviation': 'std_deviation',
                    'Sum of Squares': 'sum_of_squares'}
    COLORS = ['#DA6E6E', '#FA8080', '#789DFF',
              '#66D4FF', '#6EB518', '#9AF02E']
    VIS_STATE = {
        "aggs": [],
        "params": {
            "axis_formatter": "number",
            "axis_min": "",
            "axis_position": "left",
            "axis_scale": "normal",
            "default_index_pattern": "metrics*",
            "filter": {},
            "index_pattern": "",
            "interval": "",
            "isModelInvalid": False,
            "show_grid": 1,
            "show_legend": 1,
            "time_field": "",
            "type": "timeseries"
        }
    }

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
        parser.add_argument('x_axis_field', type=str, location='args',
                            required=True,
                            help='Time field (X axis) is required.')
        parser.add_argument('earliest_time', type=str, location='args',
                            default='5y',
                            help='Earliest <x_axis_field> time relative to now '
                                 'of all ES logs.')
        parser.add_argument('latest_time', type=str, location='args',
                            default='',
                            help='Latest <x_axis_field> time relative to now '
                                 'of all ES logs.')
        # (Joined) Rate visualization is fixed and only interval and
        # x_axis_field can be modified
        # Ratio visualization
        parser.add_argument('numerator', type=str, location='args',
                            help='Numerator is required in Ratio '
                                 'visualizations.')
        parser.add_argument('denominator', type=str, location='args',
                            help='Denominator is required in Ratio '
                                 'visualizations.')
        # Numeric visualization
        parser.add_argument('aggregator', type=str, location='args',
                            default='Average',
                            choices=('Average', 'Sum', 'Max', 'Min', 'Variance',
                                     'Std. Deviation', 'Sum of Squares'),
                            help='Aggregator type is required in Numeric '
                                 'visualizations.')
        parser.add_argument('value_field', type=str, location='args',
                            help='The field to be aggregated on is required '
                                 'in Numeric visualizations.')
        parser.add_argument('metric_name', type=str, locations='args',
                            help='Name of metric should be provided.')
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
        params['time_field'] = args['x_axis_field']
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
                .format(name=args['metric_name'])
            series = params['series'][0]
            series['metrics'][0]['type'] = \
                KibanaMetricsApi.AGG_TYPE_MAP[args['aggregator']]
            series['metrics'][0]['field'] = args['value_field']
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
        escaped_keys = map(re.escape, KibanaMetricsApi.RISON_REPLACEMENT)
        pattern = re.compile("|".join(escaped_keys), re_mode)
        return pattern.sub(
            lambda match: KibanaMetricsApi.RISON_REPLACEMENT[match.group(0)],
            rison_str
        )

    @staticmethod
    def _create_rate_visualization(job, args):
        vis_state = KibanaMetricsApi._vis_state_preprocess(job, args)
        params = vis_state['params']
        # Total w/ Fake series
        twf = KibanaMetricsApi._create_series(
            'count',
            **{'label': 'Total w/ Fake'}
        )
        # Total w/o Fake series
        twof = KibanaMetricsApi._create_series(
            'count',
            **{'label': 'Total w/o Fake',
               'series_filter': {'query': 'fake:false'}}
        )
        # Joined w/ Fake series
        jwf = KibanaMetricsApi._create_series(
            'count',
            **{'label': 'Joined w/ Fake',
               'series_filter': {'query': 'fake:true or joined:true'}}
        )
        # Joined w/o Fake series
        jwof = KibanaMetricsApi._create_series(
            'count',
            **{'label': 'Joined w/o Fake',
               'series_filter': {'query': 'joined:true'}}
        )
        # Join Rate w/ Fake series
        jrwf = KibanaMetricsApi._create_series(
            'filter_ratio', 'ratio',
            **{'label': 'Join Rate w/ Fake',
               'metrics': {'numerator': 'fake:true or joined:true',
                           'denominator': '*'},
               'line_width': '2',
               'fill': '0'}
        )
        # Join Rate w/o Fake series
        jrwof = KibanaMetricsApi._create_series(
            'filter_ratio', 'ratio',
            **{'label': 'Join Rate w/o Fake',
               'metrics': {'numerator': 'joined:true',
                           'denominator': 'fake:false'},
               'line_width': '2',
               'fill': '0'}
        )
        series = [twf, twof, jwf, jwof, jrwf, jrwof]
        for i, series_ in enumerate(series):
            series_['color'] = KibanaMetricsApi.COLORS[i]
        params['series'] = series
        return vis_state

    @staticmethod
    def _create_ratio_visualization(job, args):
        vis_state = KibanaMetricsApi._vis_state_preprocess(job, args)
        params = vis_state['params']
        # Denominator series
        denominator = KibanaMetricsApi._create_series(
            'count',
            **{'label': args['denominator'],
               'series_filter': {'query': args['denominator']}}
        )
        # Numerator series
        numerator = KibanaMetricsApi._create_series(
            'count',
            **{'label': args['numerator'],
               'series_filter': {'query': args['numerator']}}
        )
        # Ratio series
        ratio = KibanaMetricsApi._create_series(
            'filter_ratio', 'ratio',
            **{'label': 'Ratio',
               'metrics': {'numerator': args['numerator'],
                           'denominator': args['denominator']},
               'line_width': '2',
               'fill': '0'}
        )
        series = [denominator, numerator, ratio]
        for i, series_ in enumerate(series):
            series_['color'] = KibanaMetricsApi.COLORS[i * 2 + 1]
        params['series'] = series
        return vis_state

    @staticmethod
    def _create_numeric_visualization(job, args):
        vis_state = KibanaMetricsApi._vis_state_preprocess(job, args)
        params = vis_state['params']
        params['filter']['query'] += ' and name.keyword:"{name}"' \
            .format(name=args['metric_name'])
        series = KibanaMetricsApi._create_series(
            KibanaMetricsApi.AGG_TYPE_MAP[args['aggregator']],
            **{'label': args['metric_name'],
               'metrics': {'field': args['value_field']},
               'line_width': 2,
               'fill': '0.5'}
        )
        series['color'] = KibanaMetricsApi.COLORS[-2]
        params['series'] = [series]
        return vis_state

    @staticmethod
    def _vis_state_preprocess(job, args):
        vis_state = copy.deepcopy(KibanaMetricsApi.VIS_STATE)
        params = vis_state['params']
        if job.job_type == JobType.DATA_JOIN or \
            job.job_type == JobType.RAW_DATA:
            params['filter'] = KibanaMetricsApi._create_filter(
                'application_id:"{}"'.format(job.name))
        else:
            params['filter'] = KibanaMetricsApi._create_filter(
                'tags.application_id.keyword:"{}"'.format(job.name)
            )
        params['interval'] = args['interval']
        if job.job_type == JobType.DATA_JOIN:
            params['index_pattern'] = 'data_join*'
        elif job.job_type == JobType.RAW_DATA:
            params['index_pattern'] = 'raw_data*'
        else:
            params['index_pattern'] = 'metrics*'
        params['time_field'] = args['x_axis_field']
        return vis_state

    @staticmethod
    def _create_series(agg_type, series_type='normal', **kwargs):
        series_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()
        series = {
            'id': series_id,
            # "color": "rgba(102,212,255,1)",
            'split_mode': 'everything',
            'metrics': [KibanaMetricsApi._create_metrics(
                agg_type, **(kwargs.get('metrics', {}))
            )],
            'separate_axis': 0,
            'axis_position': 'right',
            'formatter': 'number',
            'chart_type': 'line',
            'line_width': kwargs.get('line_width', '0'),
            'point_size': kwargs.get('point_size', '0'),
            'fill': kwargs.get('fill', '1'),
            'stacked': 'none',
            'label': kwargs['label'],
            "type": "timeseries"
        }
        if 'series_filter' in kwargs and 'query' in kwargs['series_filter']:
            series['split_mode'] = 'filter'
            series['filter'] = KibanaMetricsApi._create_filter(
                kwargs['series_filter']['query']
            )
        if series_type == 'ratio':
            series['separate_axis'] = 1
            series['axis_min'] = '0'
            series['axis_max'] = '1'
        return series

    @staticmethod
    def _create_filter(query):
        return {'language': 'kuery',  # Kibana query
                'query': query}

    @staticmethod
    def _create_metrics(agg_type, **kwargs):
        if agg_type == 'filter_ratio':
            return {'numerator': kwargs['numerator'],
                    'denominator': kwargs['denominator'],
                    'type': agg_type}
        elif agg_type in KibanaMetricsApi.AGG_TYPE_MAP.values():
            return {'field': kwargs['field'],
                    'type': agg_type}
        else:
            assert agg_type == 'count'
            return {'field': None,
                    'type': agg_type}


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
