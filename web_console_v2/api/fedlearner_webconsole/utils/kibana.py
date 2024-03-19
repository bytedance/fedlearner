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
# pylint: disable=invalid-string-quote,missing-type-doc,missing-return-type-doc,consider-using-f-string
import hashlib
import os
import re
from datetime import datetime, timedelta

import prison
import pytz
import requests

from envs import Envs
from fedlearner_webconsole.exceptions import UnauthorizedException, \
    InvalidArgumentException, InternalException
from fedlearner_webconsole.job.models import JobType


class Kibana(object):
    """
    WARNING:
        This class is deeply coupled with
        fedlearner_webconsole.job.apis.KibanaMetricsApi
    """
    TSVB = ('Rate', 'Ratio', 'Numeric')
    TIMELION = ('Time', 'Timer')
    RISON_REPLACEMENT = {' ': '%20', '"': '%22', '#': '%23', '%': '%25', '&': '%26', '+': '%2B', '/': '%2F', '=': '%3D'}
    TIMELION_QUERY_REPLACEMENT = {' and ': ' AND ', ' or ': ' OR '}
    LOGICAL_PATTERN = re.compile(' and | or ', re.IGNORECASE)
    TSVB_AGG_TYPE = {
        'Average': 'avg',
        'Sum': 'sum',
        'Max': 'max',
        'Min': 'min',
        'Variance': 'variance',
        'Std. Deviation': 'std_deviation',
        'Sum of Squares': 'sum_of_squares'
    }
    TIMELION_AGG_TYPE = {'Average': 'avg', 'Sum': 'sum', 'Max': 'max', 'Min': 'min'}
    COLORS = ['#DA6E6E', '#FA8080', '#789DFF', '#66D4FF', '#6EB518', '#9AF02E']
    # metrics* for all other job types
    JOB_INDEX = {JobType.RAW_DATA: 'raw_data', JobType.DATA_JOIN: 'data_join', JobType.PSI_DATA_JOIN: 'data_join'}
    BASIC_QUERY = "app/kibana#/visualize/create" \
                  "?type={type}&_g=(refreshInterval:(pause:!t,value:0)," \
                  "time:(from:'{start_time}',to:'{end_time}'))&" \
                  "_a=(filters:!(),linked:!f,query:(language:kuery,query:'')," \
                  "uiState:(),vis:{vis_state})"

    @staticmethod
    def remote_query(job, args):
        Kibana._check_remote_args(args)
        if args['type'] == 'Ratio':
            panel = Kibana._create_ratio_visualization(job, args)['params']
        else:
            assert args['type'] == 'Numeric'
            panel = Kibana._create_numeric_visualization(job, args)['params']

        if 'query' in args and args['query']:
            panel['filter']['query'] += ' and ({})'.format(args['query'])
        st, et = Kibana._parse_start_end_time(args, use_now=False)
        req = {'timerange': {'timezone': Envs.TZ.zone, 'min': st, 'max': et}, 'panels': [panel]}
        res = requests.post(os.path.join(Envs.KIBANA_SERVICE_ADDRESS, 'api/metrics/vis/data'),
                            json=req,
                            headers={'kbn-xsrf': 'true'})

        try:
            res.raise_for_status()
            res = res.json()
            data = res['undefined']['series'][0]['data']
            data = list(map(lambda x: [x[0], x[1] or 0], data))
            return data
        except Exception as e:  # pylint: disable=broad-except
            raise InternalException(repr(e)) from e

    @staticmethod
    def _check_remote_args(args):
        for arg in ('type', 'interval', 'x_axis_field', 'start_time', 'end_time'):
            Kibana._check_present(args, arg)

        Kibana._check_authorization(args.get('query'))
        Kibana._check_authorization(args['x_axis_field'], extra_allowed={'tags.event_time', 'tags.process_time'})

        if args['type'] == 'Ratio':
            for arg in ('numerator', 'denominator'):
                Kibana._check_present(args, arg)
                Kibana._check_authorization(args[arg])
        else:
            assert args['type'] == 'Numeric'
            for arg in ('aggregator', 'value_field'):
                Kibana._check_present(args, arg)
            Kibana._check_authorization(args['value_field'])

    @staticmethod
    def _check_present(args, arg_name):
        if arg_name not in args or args[arg_name] is None:
            raise InvalidArgumentException('Missing required argument [{}].'.format(arg_name))

    @staticmethod
    def _check_authorization(arg, extra_allowed: set = None):
        if not arg:
            return
        allowed_fields = Envs.KIBANA_ALLOWED_FIELDS | (extra_allowed or set())
        for query in Kibana.LOGICAL_PATTERN.split(arg):
            if not query:
                continue
            if query.split(':')[0] not in allowed_fields:
                raise UnauthorizedException('Query [{}] is not authorized.'.format(query))

    @staticmethod
    def create_tsvb(job, args):
        """
        Create a Kibana TSVB Visualization based on args from reqparse

        """
        assert args['type'] in Kibana.TSVB
        if args['type'] == 'Rate':
            vis_state = Kibana._create_rate_visualization(job, args)
        elif args['type'] == 'Ratio':
            vis_state = Kibana._create_ratio_visualization(job, args)
        else:
            assert args['type'] == 'Numeric'
            vis_state = Kibana._create_numeric_visualization(job, args)

        # additional global filter on data if provided.
        if 'query' in args and args['query']:
            vis_state['params']['filter']['query'] += \
                ' and ({})'.format(args['query'])
        # rison-ify and replace
        vis_state = Kibana._regex_process(prison.dumps(vis_state), Kibana.RISON_REPLACEMENT)
        start_time, end_time = Kibana._parse_start_end_time(args)
        # a single-item list
        return [
            os.path.join(
                Envs.KIBANA_ADDRESS,
                Kibana.BASIC_QUERY.format(type='metrics', start_time=start_time, end_time=end_time,
                                          vis_state=vis_state))
        ]

    @staticmethod
    def create_timelion(job, args):
        """
        Create a Kibana Timelion Visualization based on args from reqparse

        """
        assert args['type'] in Kibana.TIMELION
        if args['type'] == 'Time':
            vis_states, times = Kibana._create_time_visualization(job, args)
        else:
            assert args['type'] == 'Timer'
            vis_states, times = Kibana._create_timer_visualization(job, args)

        # a generator, rison-ify and replace
        vis_states = (Kibana._regex_process(vs, Kibana.RISON_REPLACEMENT) for vs in map(prison.dumps, vis_states))
        return [
            os.path.join(
                Envs.KIBANA_ADDRESS,
                Kibana.BASIC_QUERY.format(type='timelion', start_time=start, end_time=end, vis_state=vis_state))
            for (start, end), vis_state in zip(times, vis_states)
        ]

    @staticmethod
    def _parse_start_end_time(args, use_now=True):
        if args['start_time'] < 0:
            st = 'now-5y' if use_now \
                else Kibana._normalize_datetime(
                    datetime.now(tz=pytz.utc) - timedelta(days=365 * 5))
        else:
            st = Kibana._normalize_datetime(datetime.fromtimestamp(args['start_time'], tz=pytz.utc))

        if args['end_time'] < 0:
            et = 'now' if use_now \
                else Kibana._normalize_datetime(datetime.now(tz=pytz.utc))
        else:
            et = Kibana._normalize_datetime(datetime.fromtimestamp(args['end_time'], tz=pytz.utc))
        return st, et

    @staticmethod
    def _normalize_datetime(dt: datetime):
        # Normalizes datetime to UTC timezone in iso format,
        # e.g. 2021-01-01T12:00:00Z
        assert dt.tzinfo
        return dt.isoformat(timespec='seconds')[:-6] + 'Z'

    @staticmethod
    def _regex_process(string, replacement):
        """
        Replace matches from replacement.keys() in string to
            replacement.values()

        """
        re_mode = re.IGNORECASE
        escaped_keys = map(re.escape, replacement)
        pattern = re.compile("|".join(escaped_keys), re_mode)
        return pattern.sub(lambda match: replacement[match.group(0).lower()], string)

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
        vis_state = Kibana._basic_tsvb_vis_state(job, args)
        params = vis_state['params']
        # `w/`, `w/o` = `with`, `without`
        # Total w/ Fake series
        twf = Kibana._tsvb_series(label='Total w/ Fake', metrics={'type': 'count'})
        # Total w/o Fake series
        twof = Kibana._tsvb_series(
            labele='Total w/o Fake',
            metrics={'type': 'count'},
            # unjoined and normal joined
            series_filter={'query': 'tags.joined: "-1" or tags.joined: 1'})
        # Joined w/ Fake series
        jwf = Kibana._tsvb_series(
            label='Joined w/ Fake',
            metrics={'type': 'count'},
            # faked joined and normal joined
            series_filter={'query': 'tags.joined: 0 or tags.joined: 1'})
        # Joined w/o Fake series
        jwof = Kibana._tsvb_series(
            label='Joined w/o Fake',
            metrics={'type': 'count'},
            # normal joined
            series_filter={'query': 'tags.joined: 1'})
        # Join Rate w/ Fake series
        jrwf = Kibana._tsvb_series(
            series_type='ratio',
            label='Join Rate w/ Fake',
            metrics={
                'numerator': 'tags.joined: 1 or tags.joined: 0',
                'denominator': '*',  # joined == -1 or 0 or 1
                'type': 'filter_ratio'
            },
            line_width='2',
            fill='0')
        # Join Rate w/o Fake series
        jrwof = Kibana._tsvb_series(series_type='ratio',
                                    label='Join Rate w/o Fake',
                                    metrics={
                                        'numerator': 'tags.joined: 1',
                                        'denominator': 'tags.joined: 1 or tags.joined: "-1"',
                                        'type': 'filter_ratio'
                                    },
                                    line_width='2',
                                    fill='0')
        series = [twf, twof, jwf, jwof, jrwf, jrwof]
        for series_, color in zip(series, Kibana.COLORS):
            series_['color'] = color
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

        Raises:
            ValueError: if some args not exist

        This method will create 3 time series and stack them in vis state.
        """
        for k in ('numerator', 'denominator'):
            if k not in args or args[k] is None:
                raise ValueError('[{}] should be provided in Ratio visualization'.format(k))
        vis_state = Kibana._basic_tsvb_vis_state(job, args)
        params = vis_state['params']
        # Denominator series
        denominator = Kibana._tsvb_series(label=args['denominator'],
                                          metrics={'type': 'count'},
                                          series_filter={'query': args['denominator']})
        # Numerator series
        numerator = Kibana._tsvb_series(label=args['numerator'],
                                        metrics={'type': 'count'},
                                        series_filter={'query': args['numerator']})
        # Ratio series
        ratio = Kibana._tsvb_series(series_type='ratio',
                                    label='Ratio',
                                    metrics={
                                        'numerator': args['numerator'],
                                        'denominator': args['denominator'],
                                        'type': 'filter_ratio'
                                    },
                                    line_width='2',
                                    fill='0')
        series = [denominator, numerator, ratio]
        for series_, color in zip(series, Kibana.COLORS[1::2]):
            series_['color'] = color
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

        Raises:
            ValueError: if some args not exist

        This method will create 1 time series. The series will filter data
            further by `name: args['metric_name']`. Aggregation will be
            applied on data's `args['value_field']` field. Aggregation types
            in `AGG_TYPE_MAP.keys()` are supported.
        """
        for k in ('aggregator', 'value_field'):
            if k not in args or args[k] is None:
                raise ValueError('[{}] should be provided in Numeric visualization.'.format(k))
        assert args['aggregator'] in Kibana.TSVB_AGG_TYPE
        vis_state = Kibana._basic_tsvb_vis_state(job, args)
        params = vis_state['params']
        series = Kibana._tsvb_series(label='{} of {}'.format(args['aggregator'], args['value_field']),
                                     metrics={
                                         'type': Kibana.TSVB_AGG_TYPE[args['aggregator']],
                                         'field': args['value_field']
                                     },
                                     line_width=2,
                                     fill='0.5')
        series['color'] = Kibana.COLORS[-2]
        params['series'] = [series]
        return vis_state

    @staticmethod
    def _create_time_visualization(job, args):
        """
        Args:
            job: fedlearner_webconsole.job.models.Job. Current job to plot.
            args: dict. reqparse args, must contain 'aggregator', 'value_field'
                and 'metric_name' entries, and the values must not be None.

        Returns:
            list of dict and tuple. A list of Timelion vis states and
            (start time, end time) of visualization.

        """
        query = 'tags.application_id:{}'.format(job.name)
        if args['query']:
            query += ' AND ({})'.format(args['query'])
        index = Kibana.JOB_INDEX.get(job.job_type, 'metrics') + '*'
        et = 'tags.event_time'
        pt = 'tags.process_time'
        interval = args['interval'] if args['interval'] != '' else 'auto'
        vis_states = []
        # first by process time, then by event time
        for t1, t2 in ((et, pt), (pt, et)):
            # t1 vs t2, max/min/median of t1 as Y axis, t2 as X axis
            # aggregate on t1 and histogram on t2
            max_series = Kibana._timelion_series(query=query, index=index, metric='max:' + t1, timefield=t2)
            min_series = Kibana._timelion_series(query=query, index=index, metric='min:' + t1, timefield=t2)
            median_series = Kibana._timelion_series(query=query,
                                                    index=index,
                                                    metric='percentiles:' + t1 + ':50',
                                                    timefield=t2)
            series = ','.join((max_series, min_series, median_series))
            vis_state = {"type": "timelion", "params": {"expression": series, "interval": interval}, "aggs": []}
            vis_states.append(vis_state)
        by_pt_start = Kibana._get_start_from_job(job)
        by_pt_end = 'now'
        by_et_start, by_et_end = Kibana._parse_start_end_time(args)
        return vis_states, [(by_pt_start, by_pt_end), (by_et_start, by_et_end)]

    @staticmethod
    def _create_timer_visualization(job, args):
        names = args['timer_names']
        if not names:
            return [], []
        # split by comma, strip whitespaces of each name, filter out empty ones
        args['timer_names'] = [name for name in map(str.strip, names.split(',')) if name]

        if args['aggregator'] not in Kibana.TIMELION_AGG_TYPE:
            raise TypeError('Aggregator [{}] is not supported in Timer ' 'visualization.'.format(args['aggregator']))
        metric = '{}:value'.format(Kibana.TIMELION_AGG_TYPE[args['aggregator']])

        query = 'tags.application_id:{}'.format(job.name)
        if args['query']:
            query += ' AND ({})'.format(args['query'])
        interval = args['interval'] if args['interval'] != '' else 'auto'
        series = []
        for timer in args['timer_names']:
            s = Kibana._timelion_series(query=query + ' AND name:{}'.format(timer),
                                        index='metrics*',
                                        metric=metric,
                                        timefield='tags.process_time')
            series.append(s)
        if args['split']:
            # split series to different plots
            vis_states = [{
                "type": "timelion",
                "params": {
                    "expression": s,
                    "interval": interval
                },
                "aggs": []
            } for s in series]
        else:
            # multiple series in one plot, a single-item list
            vis_states = [{
                "type": "timelion",
                "params": {
                    "expression": ','.join(series),
                    "interval": interval
                },
                "aggs": []
            }]
        start = Kibana._get_start_from_job(job)
        end = 'now'
        # len(return1) == len(return2) should be assured
        return vis_states, [(start, end) for _ in range(len(vis_states))]

    @staticmethod
    def _basic_tsvb_vis_state(job, args):
        """
        Args:
            job: fedlearner_webconsole.job.models.Job. Current job to plot.
            args: dict. reqparse args, must contain 'x_axis_field' entry,
                and the value must not be None. vis_state['interval'] will
                default to ''(automated by Kibana in TSVB visualization) if
                'interval' is not provided in args.

        Returns:
            dict. A Kibana TSVB vis state dict without any time series.

        This method will create basic TSVB vis state without any time series

        """
        assert 'x_axis_field' in args and args['x_axis_field']
        vis_state = {
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
        params = vis_state['params']
        params['interval'] = args.get('interval', '')
        params['index_pattern'] = Kibana.JOB_INDEX \
                                      .get(job.job_type, 'metrics') + '*'
        params['filter'] = Kibana._filter_query('tags.application_id:"{}"'.format(job.name))
        params['time_field'] = args['x_axis_field']
        return vis_state

    @staticmethod
    def _tsvb_series(series_type='normal', **kwargs):
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

        Returns:
            dict, a Kibana TSVB visualization time series definition

        """
        # series_id is meaningless and arbitrary to us but necessary
        series_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()
        series_metrics = kwargs.get('metrics', {})
        assert isinstance(series_metrics, dict)
        if 'type' in series_metrics and series_metrics['type'] == 'count':
            series_metrics['field'] = None

        series = {
            'id': series_id,
            'split_mode': 'everything',
            # `metrics` field is a list of metrics,
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
            series['filter'] = Kibana._filter_query(kwargs['series_filter']['query'])
        if series_type == 'ratio':
            # if this is a ratio series, split axis and set axis range
            series['separate_axis'] = 1
            series['axis_min'] = '0'
            series['axis_max'] = '1'
        return series

    @staticmethod
    def _timelion_series(**kwargs):
        assert 'metric' in kwargs
        assert 'timefield' in kwargs
        # convert all logical `and` and `or` to `AND` and `OR`
        query = Kibana._regex_process(kwargs.get('query', '*'), Kibana.TIMELION_QUERY_REPLACEMENT)
        return ".es(q=\"{query}\", index={index}, " \
               "metric={metric}, timefield={timefield})" \
               ".legend(showTime=true)" \
            .format(query=query, index=kwargs.get('index', '_all'),
                    metric=kwargs['metric'], timefield=kwargs['timefield'])

    @staticmethod
    def _filter_query(query):
        return {
            'language': 'kuery',  # Kibana query
            'query': query
        }

    @staticmethod
    def _get_start_from_job(job):
        """
        :param: fedlearner_webconsole.job.models.Job
        :return: An iso format datetime string in UTC
        """
        if job.created_at.tzinfo:
            start = pytz.utc.normalize(job.created_at)
        else:
            start = pytz.utc.normalize(Envs.TZ.localize(job.created_at))
        # e.g., 2021-01-01T12:00:00Z, which is equivalent to 20:00:00 on the
        # same day in UTC+08:00 (BJT)
        start = start.isoformat(timespec='seconds')[:-6] + 'Z'
        return start
