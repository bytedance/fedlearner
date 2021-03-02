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
import copy
import hashlib
import re
import time
import json
from google.protobuf.json_format import MessageToDict

import prison
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
    # some URL rules in Kibana's URL encoding
    RISON_REPLACEMENT = {' ': '%20',
                         '"': '%22',
                         '#': '%23',
                         '%': '%25',
                         '&': '%26',
                         '+': '%2B',
                         '/': '%2F'}
    AGG_TYPE_MAP = {'Average': 'avg',
                    'Sum': 'sum',
                    'Max': 'max',
                    'Min': 'min',
                    'Variance': 'variance',
                    'Std. Deviation': 'std_deviation',
                    'Sum of Squares': 'sum_of_squares'}
    COLORS = ['#DA6E6E', '#FA8080', '#789DFF',
              '#66D4FF', '#6EB518', '#9AF02E']
    VIS_STATE = {"aggs": [],
                 "params": {"axis_formatter": "number",
                            "axis_min": "",
                            "axis_position": "left",  # default axis position
                            "axis_scale": "normal",
                            "default_index_pattern": "metrics*",
                            "filter": {},
                            "index_pattern": "",
                            "interval": "",
                            "isModelInvalid": False,
                            "show_grid": 1,
                            "show_legend": 1,
                            "time_field": "",
                            "type": "timeseries"}}

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
        parser.add_argument('query', type=str, location='args',
                            help='Additional query string to the graph.')
        parser.add_argument('start_time', type=str, location='args',
                            default='3y',
                            help='Earliest <x_axis_field> time relative to now '
                                 'of all ES logs.')
        parser.add_argument('end_time', type=str, location='args',
                            default='0d',
                            help='Latest <x_axis_field> time relative to now '
                                 'of all ES logs.')
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
                            help='Aggregator type is required in Numeric '
                                 'visualization.')
        parser.add_argument('value_field', type=str, location='args',
                            help='The field to be aggregated on is required '
                                 'in Numeric visualization.')
        parser.add_argument('metric_name', type=str, locations='args',
                            help='Name of metric should be provided.')
        args = parser.parse_args()
        assert args['type'] in ('Rate', 'Ratio', 'Numeric')
        # get corresponding create method and call it with (job, args)
        vis_state = getattr(KibanaMetricsApi,
                            '_create_{}_visualization'
                            .format(args['type'].lower()))(job, args)
        # addition global filter on data if provided.
        if args['query'] is not None and args['query'] != '':
            vis_state['params']['filter']['query'] += \
                ' and ({})'.format(args['query'])
        rison_str = prison.dumps(vis_state)
        suffix = KibanaMetricsApi._rison_postprocess(rison_str)

        iframe_src = "{kbn_addr}/app/kibana#/visualize/create" \
                     "?type=metrics&embed=true&" \
                     "_g=(refreshInterval:(pause:!t,value:0)," \
                     "time:(from:now-{start_time},to:now-{end_time}))&" \
                     "_a=(filters:!(),linked:!f," \
                     "query:(language:kuery,query:''),uiState:()," \
                     "vis:{vis_state})" \
            .format(kbn_addr=Config.KIBANA_ADDRESS,
                    start_time=args['start_time'],
                    end_time=args['end_time'],
                    vis_state=suffix)
        return iframe_src

    @staticmethod
    def _rison_postprocess(rison_str):
        """
        After `prison.dumps`, some characters are still left to be encoded.

        """
        re_mode = re.IGNORECASE
        escaped_keys = map(re.escape, KibanaMetricsApi.RISON_REPLACEMENT)
        pattern = re.compile("|".join(escaped_keys), re_mode)
        return pattern.sub(
            lambda match: KibanaMetricsApi.RISON_REPLACEMENT[match.group(0)],
            rison_str
        )

    @staticmethod
    def _create_rate_visualization(job, args):
        """
        Args:
            job: fedlearner_webconsole.job.models.Job. Current job to plot
            args: dict. reqparse args, only used in vis state preprocess

        Returns:
            dict. A Kibana vis state dict

            This method will create 6 time series and stack them in vis state.
        """
        vis_state = KibanaMetricsApi._vis_state_preprocess(job, args)
        params = vis_state['params']
        # Total w/ Fake series
        twf = KibanaMetricsApi._create_series(
            **{'label': 'Total w/ Fake',
               'metrics': {'type': 'count'}}
        )
        # Total w/o Fake series
        twof = KibanaMetricsApi._create_series(
            **{'label': 'Total w/o Fake',
               'metrics': {'type': 'count'},
               'series_filter': {'query': 'fake:false'}}
        )
        # Joined w/ Fake series
        jwf = KibanaMetricsApi._create_series(
            **{'label': 'Joined w/ Fake',
               'metrics': {'type': 'count'},
               'series_filter': {'query': 'fake:true or joined:true'}}
        )
        # Joined w/o Fake series
        jwof = KibanaMetricsApi._create_series(
            **{'label': 'Joined w/o Fake',
               'metrics': {'type': 'count'},
               'series_filter': {'query': 'joined:true'}}
        )
        # Join Rate w/ Fake series
        jrwf = KibanaMetricsApi._create_series(
            series_type='ratio',
            **{'label': 'Join Rate w/ Fake',
               'metrics': {'numerator': 'fake:true or joined:true',
                           'denominator': '*',
                           'type': 'filter_ratio'},
               'line_width': '2',
               'fill': '0'}
        )
        # Join Rate w/o Fake series
        jrwof = KibanaMetricsApi._create_series(
            series_type='ratio',
            **{'label': 'Join Rate w/o Fake',
               'metrics': {'numerator': 'joined:true',
                           'denominator': 'fake:false',
                           'type': 'filter_ratio'},
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
        """
        Args:
            job: fedlearner_webconsole.job.models.Job. Current job to plot.
            args: dict. reqparse args, must contain 'numerator' and
                'denominator' entries, and the values must not be None.
                args['numerator'] and args['denominator'] should respectively be
                a valid Lucene query string.

        Returns:
            dict. A Kibana vis state dict

        This method will create 3 time series and stack them in vis state.
        """
        for k in ('numerator', 'denominator'):
            if not (k in args and args[k] is not None):
                raise ValueError(
                    '[%s] should be provided in Ratio visualization', k
                )
        vis_state = KibanaMetricsApi._vis_state_preprocess(job, args)
        params = vis_state['params']
        # Denominator series
        denominator = KibanaMetricsApi._create_series(
            **{'label': args['denominator'],
               'metrics': {'type': 'count'},
               'series_filter': {'query': args['denominator']}}
        )
        # Numerator series
        numerator = KibanaMetricsApi._create_series(
            **{'label': args['numerator'],
               'metrics': {'type': 'count'},
               'series_filter': {'query': args['numerator']}}
        )
        # Ratio series
        ratio = KibanaMetricsApi._create_series(
            series_type='ratio',
            **{'label': 'Ratio',
               'metrics': {'numerator': args['numerator'],
                           'denominator': args['denominator'],
                           'type': 'filter_ratio'},
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
        """
        Args:
            job: fedlearner_webconsole.job.models.Job. Current job to plot.
            args: dict. reqparse args, must contain 'aggregator', 'value_field'
                and 'metric_name' entries, and the values must not be None.

        Returns:
            dict. A Kibana vis state dict

        This method will create 1 time series. The series will filter data
            further by `name.keyword: args['metric_name']`. Aggregation will be
            applied on data's `args['value_field']` field. Aggregation types
            in `KibanaMetricsApi.AGG_TYPE_MAP.keys()` are supported.
        """
        for k in ('aggregator', 'value_field', 'metric_name'):
            if not (k in args and args[k] is not None):
                raise ValueError(
                    '[%s] should be provided in Numeric visualization.', k
                )
        if args['aggregator'] not in KibanaMetricsApi.AGG_TYPE_MAP:
            raise ValueError(
                'Aggregator type [%s] is not supported. Supported types: %s.',
                args['aggregator'], list(KibanaMetricsApi.AGG_TYPE_MAP.keys())
            )
        vis_state = KibanaMetricsApi._vis_state_preprocess(job, args)
        params = vis_state['params']
        params['filter']['query'] += ' and name.keyword:"{name}"' \
            .format(name=args['metric_name'])
        series = KibanaMetricsApi._create_series(
            **{'label': '{} of {}'.format(args['aggregator'],
                                          args['metric_name']),
               'metrics': {'type': KibanaMetricsApi
                                  .AGG_TYPE_MAP[args['aggregator']],
                           'field': args['value_field']},
               'line_width': 2,
               'fill': '0.5'}
        )
        series['color'] = KibanaMetricsApi.COLORS[-2]
        params['series'] = [series]
        return vis_state

    @staticmethod
    def _vis_state_preprocess(job, args):
        """
        Args:
            job: fedlearner_webconsole.job.models.Job. Current job to plot.
            args: dict. reqparse args, must contain 'x_axis_field' entry,
                and the value must not be None. vis_state['interval'] will
                default to ''(automated by Kibana in TSVB visualization) if
                'interval' is not provided in args.

        Returns:
            dict. A Kibana vis state dict without any time series.

        This method will create basic vis state withou any time series

        """
        assert 'x_axis_field' in args and args['x_axis_field'] is not None
        vis_state = copy.deepcopy(KibanaMetricsApi.VIS_STATE)
        params = vis_state['params']
        params['interval'] = args.get('interval', '')
        if job.job_type == JobType.DATA_JOIN:
            params['index_pattern'] = 'data_join*'
            params['filter'] = KibanaMetricsApi._create_filter(
                'application_id:"{}"'.format(job.name))
        elif job.job_type == JobType.RAW_DATA:
            params['index_pattern'] = 'raw_data*'
            params['filter'] = KibanaMetricsApi._create_filter(
                'application_id:"{}"'.format(job.name))
        else:
            params['index_pattern'] = 'metrics*'
            # metrics* index has a different mapping which is not optimized due
            # to compatibility issues, thus 'filter' is different from above.
            params['filter'] = KibanaMetricsApi._create_filter(
                'tags.application_id.keyword:"{}"'.format(job.name)
            )
        params['time_field'] = args['x_axis_field']
        return vis_state

    @staticmethod
    def _create_series(series_type='normal', **kwargs):
        """
        Args:
            series_type: str, 'normal' or 'ratio', will only change the
                appearance of the time series.
            **kwargs: keywords that will be used if provided:
                'metrics': dict, metrics of time series.
                'line_width': str, time series line appearance.
                'point_size': str, time series line appearance.
                'fill': str, time series line appearance.
                'label': str, the name of the time series.
                'series_filter': dict, additional filter on data,
                                 only applied on this series.

        Returns: dict, a time series definition

        """
        series_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()
        series_metrics = kwargs.get('metrics', {})
        assert isinstance(series_metrics, dict)
        if 'type' in series_metrics and series_metrics['type'] == 'count':
            series_metrics['field'] = None
        series = {
            'id': series_id,
            'split_mode': 'everything',
            # metrics field is a list of metrics,
            # but a single metrics is enough currently
            'metrics': [series_metrics],
            'separate_axis': 0,
            'axis_position': 'right',  # axis position if split axis
            'formatter': 'number',
            'chart_type': 'line',
            'line_width': str(kwargs.get('line_width', '0')),
            'point_size': str(kwargs.get('point_size', '1')),
            'fill': str(kwargs.get('fill', '1')),
            'stacked': 'none',
            'label': kwargs.get('label', ''),
            "type": "timeseries"
        }
        if 'series_filter' in kwargs and 'query' in kwargs['series_filter']:
            series['split_mode'] = 'filter'
            series['filter'] = KibanaMetricsApi._create_filter(
                kwargs['series_filter']['query']
            )
        if series_type == 'ratio':
            # if this is a ratio series, split axis and set axis range
            series['separate_axis'] = 1
            series['axis_min'] = '0'
            series['axis_max'] = '1'
        return series

    @staticmethod
    def _create_filter(query):
        return {'language': 'kuery',  # Kibana query
                'query': query}


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
