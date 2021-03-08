import copy
import hashlib
import re
from datetime import datetime

from config import Config
from fedlearner_webconsole.job.models import JobType


class KibanaUtils(object):
    KIBANA_ADDRESS = Config.KIBANA_HOST
    if Config.KIBANA_PORT is not None:
        KIBANA_ADDRESS += ':{}'.format(Config.KIBANA_PORT)
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

    @staticmethod
    def rison_postprocess(rison_str):
        """
        After `prison.dumps`, some characters are still left to be encoded.

        """
        re_mode = re.IGNORECASE
        escaped_keys = map(re.escape, KibanaUtils.RISON_REPLACEMENT)
        pattern = re.compile("|".join(escaped_keys), re_mode)
        return pattern.sub(
            lambda match: KibanaUtils.RISON_REPLACEMENT[match.group(0)],
            rison_str
        )

    @staticmethod
    def create_rate_visualization(job, args):
        """
        Args:
            job: fedlearner_webconsole.job.models.Job. Current job to plot
            args: dict. reqparse args, only used in vis state preprocess

        Returns:
            dict. A Kibana vis state dict

            This method will create 6 time series and stack them in vis state.
        """
        vis_state = KibanaUtils._vis_state_preprocess(job, args)
        params = vis_state['params']
        # Total w/ Fake series
        twf = KibanaUtils._create_series(
            **{'label': 'Total w/ Fake',
               'metrics': {'type': 'count'}}
        )
        # Total w/o Fake series
        twof = KibanaUtils._create_series(
            **{'label': 'Total w/o Fake',
               'metrics': {'type': 'count'},
               # unjoined and normally joined
               'series_filter': {'query': 'joined: "-1" or joined: 1'}}
        )
        # Joined w/ Fake series
        jwf = KibanaUtils._create_series(
            **{'label': 'Joined w/ Fake',
               'metrics': {'type': 'count'},
               # faked joined and normally joined
               'series_filter': {'query': 'joined: 0 or joined: 1'}}
        )
        # Joined w/o Fake series
        jwof = KibanaUtils._create_series(
            **{'label': 'Joined w/o Fake',
               'metrics': {'type': 'count'},
               # normally joined
               'series_filter': {'query': 'joined: 1'}}
        )
        # Join Rate w/ Fake series
        jrwf = KibanaUtils._create_series(
            series_type='ratio',
            **{'label': 'Join Rate w/ Fake',
               'metrics': {'numerator': 'joined: 1 or joined: 0',
                           'denominator': '*',  # joined -1 or 0 or 1
                           'type': 'filter_ratio'},
               'line_width': '2',
               'fill': '0'}
        )
        # Join Rate w/o Fake series
        jrwof = KibanaUtils._create_series(
            series_type='ratio',
            **{'label': 'Join Rate w/o Fake',
               'metrics': {'numerator': 'joined: 1',
                           'denominator': 'joined: 1 or joined: "-1"',
                           'type': 'filter_ratio'},
               'line_width': '2',
               'fill': '0'}
        )
        series = [twf, twof, jwf, jwof, jrwf, jrwof]
        for i, series_ in enumerate(series):
            series_['color'] = KibanaUtils.COLORS[i]
        params['series'] = series
        return vis_state

    @staticmethod
    def create_ratio_visualization(job, args):
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
                    '[{}] should be provided in Ratio visualization'.format(k)
                )
        vis_state = KibanaUtils._vis_state_preprocess(job, args)
        params = vis_state['params']
        # Denominator series
        denominator = KibanaUtils._create_series(
            **{'label': args['denominator'],
               'metrics': {'type': 'count'},
               'series_filter': {'query': args['denominator']}}
        )
        # Numerator series
        numerator = KibanaUtils._create_series(
            **{'label': args['numerator'],
               'metrics': {'type': 'count'},
               'series_filter': {'query': args['numerator']}}
        )
        # Ratio series
        ratio = KibanaUtils._create_series(
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
            series_['color'] = KibanaUtils.COLORS[i * 2 + 1]
        params['series'] = series
        return vis_state

    @staticmethod
    def create_numeric_visualization(job, args):
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
            in `AGG_TYPE_MAP.keys()` are supported.
        """
        for k in ('aggregator', 'value_field', 'metric_name'):
            if not (k in args and args[k] is not None):
                raise ValueError(
                    '[{}] should be provided in Numeric visualization.'
                    .format(k))
        assert args['aggregator'] in KibanaUtils.AGG_TYPE_MAP
        vis_state = KibanaUtils._vis_state_preprocess(job, args)
        params = vis_state['params']
        params['filter']['query'] += ' and name.keyword:"{name}"' \
            .format(name=args['metric_name'])
        series = KibanaUtils._create_series(
            **{'label': '{} of {}'.format(args['aggregator'],
                                          args['metric_name']),
               'metrics': {'type': KibanaUtils.AGG_TYPE_MAP[args['aggregator']],
                           'field': args['value_field']},
               'line_width': 2,
               'fill': '0.5'}
        )
        series['color'] = KibanaUtils.COLORS[-2]
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
        vis_state = copy.deepcopy(KibanaUtils.VIS_STATE)
        params = vis_state['params']
        params['interval'] = args.get('interval', '')
        if job.job_type == JobType.DATA_JOIN:
            params['index_pattern'] = 'data_join*'
            params['filter'] = KibanaUtils._create_filter(
                'application_id:"{}"'.format(job.name))
        elif job.job_type == JobType.RAW_DATA:
            params['index_pattern'] = 'raw_data*'
            params['filter'] = KibanaUtils._create_filter(
                'application_id:"{}"'.format(job.name))
        else:
            params['index_pattern'] = 'metrics*'
            # metrics* index has a different mapping which is not optimized due
            # to compatibility issues, thus 'filter' is different from above.
            params['filter'] = KibanaUtils._create_filter(
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
            series['filter'] = KibanaUtils._create_filter(
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
