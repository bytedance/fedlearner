import hashlib
import re
from datetime import datetime

import prison
import pytz
from config import Config
from fedlearner_webconsole import envs
from fedlearner_webconsole.job.models import JobType


class KibanaUtils(object):
    """
    WARNING:
        This class is deeply coupled with
        fedlearner_webconsole.job.apis.KibanaMetricsApi
    """
    KIBANA_ADDRESS = Config.KIBANA_INGRESS_HOST
    if Config.KIBANA_INGRESS_PORT is not None:
        KIBANA_ADDRESS += ':{}'.format(Config.KIBANA_INGRESS_PORT)
    TSVB = ('Rate', 'Ratio', 'Numeric')
    TIMELION = ('Time', 'Timer')
    RISON_REPLACEMENT = {' ': '%20',
                         '"': '%22',
                         '#': '%23',
                         '%': '%25',
                         '&': '%26',
                         '+': '%2B',
                         '/': '%2F',
                         '=': '%3D'}
    TIMELION_QUERY_REPLACEMENT = {' and ': ' AND ',
                                  ' or ': ' OR '}
    TSVB_AGG_TYPE = {'Average': 'avg',
                     'Sum': 'sum',
                     'Max': 'max',
                     'Min': 'min',
                     'Variance': 'variance',
                     'Std. Deviation': 'std_deviation',
                     'Sum of Squares': 'sum_of_squares'}
    TIMELION_AGG_TYPE = {'Average': 'avg',
                         'Sum': 'sum',
                         'Max': 'max',
                         'Min': 'min'}
    COLORS = ['#DA6E6E', '#FA8080', '#789DFF',
              '#66D4FF', '#6EB518', '#9AF02E']
    # metrics_v2* for all other job types
    JOB_INDEX = {JobType.RAW_DATA: 'raw_data',
                 JobType.DATA_JOIN: 'data_join',
                 JobType.PSI_DATA_JOIN: 'data_join'}

    @staticmethod
    def create_tsvb(job, args):
        """
        Create a Kibana TSVB Visualization based on args from reqparse

        """
        assert args['type'] in ('Rate', 'Ratio', 'Numeric')
        vis_state = getattr(KibanaUtils,
                            '_create_{}_visualization'
                            .format(args['type'].lower()))(job, args)
        # additional global filter on data if provided.
        if args['query'] is not None and args['query'] != '':
            vis_state['params']['filter']['query'] += \
                ' and ({})'.format(args['query'])
        # rison-ify and replace
        vis_state = KibanaUtils._regex_process(
            prison.dumps(vis_state), KibanaUtils.RISON_REPLACEMENT
        )
        start_time, end_time = KibanaUtils._parse_start_end_time(args)

        return [
            "{kbn_addr}/app/kibana#/visualize/create"
            "?type=metrics&embed=true&"
            "_g=(refreshInterval:(pause:!t,value:0),"
            "time:(from:'{start_time}',to:'{end_time}'))&"
            "_a=(filters:!(),linked:!f,"
            "query:(language:kuery,query:''),uiState:(),"
            "vis:{vis_state})".format(kbn_addr=KibanaUtils.KIBANA_ADDRESS,
                                      start_time=start_time,
                                      end_time=end_time,
                                      vis_state=vis_state)
        ]

    @staticmethod
    def create_timelion(job, args):
        """
        Create a Kibana Timelion Visualization based on args from reqparse

        """
        assert args['type'] in ('Time', 'Timer')
        # (start time, end time, vis state)
        vis_states, durations = getattr(
            KibanaUtils,
            '_create_{}_visualization'
            .format(args['type'].lower()))(job, args)
        # rison-ify and replace
        vis_states = list(
            KibanaUtils._regex_process(vs, KibanaUtils.RISON_REPLACEMENT)
            for vs in map(prison.dumps, vis_states)
        )

        return [
            "{kbn_addr}/app/kibana#/visualize/create"
            "?embed=true&type=timelion&"
            "_g=(refreshInterval:(pause:!t,value:0),"
            "time:(from:'{start_time}',to:'{end_time}'))&"
            "_a=(filters:!(),linked:!f,"
            "query:(language:kuery,query:''),uiState:(),"
            "vis:{vis_state})".format(kbn_addr=KibanaUtils.KIBANA_ADDRESS,
                                      start_time=start, end_time=end,
                                      vis_state=vis_state)
            for (start, end), vis_state in zip(durations, vis_states)
        ]

    @staticmethod
    def _parse_start_end_time(args):
        st = 'now-5y' if args['start_time'] < 0 \
            else datetime.fromtimestamp(args['start_time'], tz=pytz.utc) \
                     .isoformat(timespec='seconds')[:-6] + 'Z'
        et = 'now' if args['end_time'] < 0 \
            else datetime.fromtimestamp(args['end_time'], tz=pytz.utc) \
                     .isoformat(timespec='seconds')[:-6] + 'Z'
        return st, et

    @staticmethod
    def _regex_process(string, replacement):
        """
        Replace matches from replacement.keys() in string to
            replacement.values()

        """
        re_mode = re.IGNORECASE
        escaped_keys = map(re.escape, replacement)
        pattern = re.compile("|".join(escaped_keys), re_mode)
        return pattern.sub(
            lambda match: replacement[match.group(0).lower()],
            string
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
        vis_state = KibanaUtils._basic_tsvb_vis_state(job, args)
        params = vis_state['params']
        # Total w/ Fake series
        twf = KibanaUtils._tsvb_series(
            label='Total w/ Fake',
            metrics={'type': 'count'}
        )
        # Total w/o Fake series
        twof = KibanaUtils._tsvb_series(
            labele='Total w/o Fake',
            metrics={'type': 'count'},
            # unjoined and normally joined
            series_filter={'query': 'joined: "-1" or joined: 1'}
        )
        # Joined w/ Fake series
        jwf = KibanaUtils._tsvb_series(
            label='Joined w/ Fake',
            metrics={'type': 'count'},
            # faked joined and normally joined
            series_filter={'query': 'joined: 0 or joined: 1'}
        )
        # Joined w/o Fake series
        jwof = KibanaUtils._tsvb_series(
            label='Joined w/o Fake',
            metrics={'type': 'count'},
            # normally joined
            series_filter={'query': 'joined: 1'}
        )
        # Join Rate w/ Fake series
        jrwf = KibanaUtils._tsvb_series(
            series_type='ratio',
            label='Join Rate w/ Fake',
            metrics={'numerator': 'joined: 1 or joined: 0',
                     'denominator': '*',  # joined -1 or 0 or 1
                     'type': 'filter_ratio'},
            line_width='2',
            fill='0'
        )
        # Join Rate w/o Fake series
        jrwof = KibanaUtils._tsvb_series(
            series_type='ratio',
            label='Join Rate w/o Fake',
            metrics={'numerator': 'joined: 1',
                     'denominator': 'joined: 1 or joined: "-1"',
                     'type': 'filter_ratio'},
            line_width='2',
            fill='0'
        )
        series = [twf, twof, jwf, jwof, jrwf, jrwof]
        for i, series_ in enumerate(series):
            series_['color'] = KibanaUtils.COLORS[i]
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
            if k not in args or args[k] is None:
                raise ValueError(
                    '[{}] should be provided in Ratio visualization'.format(k)
                )
        vis_state = KibanaUtils._basic_tsvb_vis_state(job, args)
        params = vis_state['params']
        # Denominator series
        denominator = KibanaUtils._tsvb_series(
            label=args['denominator'],
            metrics={'type': 'count'},
            series_filter={'query': args['denominator']}
        )
        # Numerator series
        numerator = KibanaUtils._tsvb_series(
            label=args['numerator'],
            metrics={'type': 'count'},
            series_filter={'query': args['numerator']}
        )
        # Ratio series
        ratio = KibanaUtils._tsvb_series(
            series_type='ratio',
            label='Ratio',
            metrics={'numerator': args['numerator'],
                     'denominator': args['denominator'],
                     'type': 'filter_ratio'},
            line_width='2',
            fill='0'
        )
        series = [denominator, numerator, ratio]
        for i, series_ in enumerate(series):
            series_['color'] = KibanaUtils.COLORS[i * 2 + 1]
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
            further by `name: args['metric_name']`. Aggregation will be
            applied on data's `args['value_field']` field. Aggregation types
            in `AGG_TYPE_MAP.keys()` are supported.
        """
        for k in ('aggregator', 'value_field'):
            if k not in args or args[k] is None:
                raise ValueError(
                    '[{}] should be provided in Numeric visualization.'
                    .format(k))
        assert args['aggregator'] in KibanaUtils.TSVB_AGG_TYPE
        vis_state = KibanaUtils._basic_tsvb_vis_state(job, args)
        params = vis_state['params']
        series = KibanaUtils._tsvb_series(
            label='{} of {}'.format(args['aggregator'],
                                    args['value_field']),
            metrics={'type': KibanaUtils.TSVB_AGG_TYPE[args['aggregator']],
                     'field': args['value_field']},
            line_width=2,
            fill='0.5'
        )
        series['color'] = KibanaUtils.COLORS[-2]
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
        if job.job_type in KibanaUtils.JOB_INDEX:
            query = 'application_id:{} AND ({})'.format(job.name, args['query'])
            index = KibanaUtils.JOB_INDEX[job.job_type] + '*'
            et = 'event_time'
            pt = 'process_time'
        else:
            query = 'tags.application_id:{} AND ({})'.format(
                job.name, args['query']
            )
            index = 'metrics_v2*'
            et = 'tags.event_time'
            pt = 'date_time'
        interval = args['interval'] if args['interval'] != '' else 'auto'
        vis_states = []
        # first by process time, then by event time
        for t1, t2 in ((et, pt), (pt, et)):
            # process_time vs event_time, max/min/median of pt and et
            # aggregate on t1 and histogram on t2
            max_series = KibanaUtils._timelion_series(
                query=query, index=index,
                metric='max:' + t1, timefield=t2
            )
            min_series = KibanaUtils._timelion_series(
                query=query, index=index,
                metric='min:' + t1, timefield=t2
            )
            median_series = KibanaUtils._timelion_series(
                query=query, index=index,
                metric='percentiles:' + t1 + ':50', timefield=t2
            )
            series = ','.join((max_series, min_series, median_series))
            vis_state = {"type": "timelion",
                         "params": {"expression": series,
                                    "interval": interval},
                         "aggs": []}
            vis_states.append(vis_state)

        by_pt_start = pytz.utc.normalize(envs.TZ.localize(job.created_at)) \
            .isoformat(timespec='seconds')[:-6] + 'Z'
        by_pt_end = 'now'
        by_et_start, by_et_end = KibanaUtils._parse_start_end_time(args)
        return vis_states, [(by_pt_start, by_pt_end), (by_et_start, by_et_end)]

    @staticmethod
    def _create_timer_visualization(job, args):
        if not args['timer_names']:
            return [], []
        if args['aggregator'] not in KibanaUtils.TIMELION_AGG_TYPE:
            raise TypeError('{} is not supported in Timer visualization.'
                            .format(args['aggregator']))
        query = 'tags.application_id:{} AND ({})'.format(
            job.name, args['query']
        )
        index = 'metrics_v2*'
        metric = '{}:value'.format(
            KibanaUtils.TIMELION_AGG_TYPE[args['aggregator']]
        )
        interval = args['interval'] if args['interval'] != '' else 'auto'
        series = []
        for timer in args['timer_names']:
            timer_query = query + ' AND name:{}'.format(timer)
            s = KibanaUtils._timelion_series(
                query=timer_query, index=index,
                metric=metric, timefield='date_time'
            )
            series.append(s)
        vis_state = {"type": "timelion",
                     "params": {"expression": ','.join(series),
                                "interval": interval},
                     "aggs": []}
        start = pytz.utc.normalize(envs.TZ.localize(job.created_at)) \
                    .isoformat(timespec='seconds')[:-6] + 'Z'
        end = 'now'
        return [vis_state], [(start, end)]

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
        assert 'x_axis_field' in args and args['x_axis_field'] is not None
        vis_state = {"aggs": [],
                     "params": {"axis_formatter": "number",
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
                                "type": "timeseries"}}
        params = vis_state['params']
        params['interval'] = args.get('interval', '')
        if job.job_type in KibanaUtils.JOB_INDEX:
            params['index_pattern'] = KibanaUtils.JOB_INDEX[job.job_type] + '*'
            params['filter'] = KibanaUtils._filter_query(
                'application_id:"{}"'.format(job.name))
        else:
            params['index_pattern'] = 'metrics_v2*'
            params['filter'] = KibanaUtils._filter_query(
                'tags.application_id:"{}"'.format(job.name)
            )
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

        Returns: dict, a Kibana TSVB visualization time series definition

        """
        # series_id is useless but necessary
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
            series['filter'] = KibanaUtils._filter_query(
                kwargs['series_filter']['query']
            )
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
        query = KibanaUtils._regex_process(
            kwargs.get('query', '*'), KibanaUtils.TIMELION_QUERY_REPLACEMENT)
        return ".es(q=\"{query}\", index={index}, " \
               "metric={metric}, timefield={timefield})" \
               ".legend(showTime=true)" \
            .format(query=query, index=kwargs.get('index', '_all'),
                    metric=kwargs['metric'], timefield=kwargs['timefield'])

    @staticmethod
    def _filter_query(query):
        return {'language': 'kuery',  # Kibana query
                'query': query}
