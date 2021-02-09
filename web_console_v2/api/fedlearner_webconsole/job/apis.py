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
from datetime import datetime
import mpld3
from matplotlib.figure import Figure

from flask_restful import Resource, reqparse
from fedlearner_webconsole.job.models import Job, JobType
from fedlearner_webconsole.job.es import es
from fedlearner_webconsole.exceptions import NotFoundException
from fedlearner_webconsole.k8s_client import get_client


class JobApi(Resource):
    def get(self, job_id):
        job = Job.query.filter_by(id=job_id).first()
        if job is None:
            raise NotFoundException()
        return {'data': job.to_dict()}

    # TODO: manual start jobs


class PodLogApi(Resource):
    def get(self, pod_name):
        parser = reqparse.RequestParser()
        parser.add_argument('start_time', type=int, location='args',
                            required=True,
                            help='start_time is required and must be timestamp')
        parser.add_argument('max_lines', type=int, location='args',
                    required=True,
                    help='max_lines is required')
        data = parser.parse_args()
        start_time = data['start_time']
        max_lines = data['max_lines']
        return {'data': es.query_log('filebeat-*', '', pod_name,
                                     start_time,
                                     int(time.time() * 1000))[:max_lines][::-1]}


class JobLogApi(Resource):
    def get(self, job_name):
        parser = reqparse.RequestParser()
        parser.add_argument('start_time', type=int, location='args',
                            required=True,
                            help='project_id is required and must be timestamp')
        parser.add_argument('max_lines', type=int, location='args',
                            required=True,
                            help='max_lines is required')
        data = parser.parse_args()
        start_time = data['start_time']
        max_lines = data['max_lines']
        return {'data': es.query_log('filebeat-*', job_name,
                                     'fedlearner-operator',
                                     start_time,
                                     int(time.time() * 1000))[:max_lines][::-1]}


class PodContainerApi(Resource):
    def get(self, job_id, pod_name):
        job = Job.query.filter_by(id=job_id).first()
        if job is None:
            raise NotFoundException()
        k8s = get_client()
        base = k8s.get_base_url()
        container_id = k8s.get_webshell_session(job.project.get_namespace(),
                                                pod_name,
                                                'tensorflow')
        return {'data': {'id': container_id, 'base': base}}

def to_datetime(timestamp):
    return datetime.fromtimestamp(timestamp/1000.0)

class JobMetricsApi(Resource):
    def get(self, job_id):
        job = Job.query.filter_by(id=job_id).first()
        if job is None:
            raise NotFoundException()
        if job.job_type == JobType.DATA_JOIN:
            metrics = self._get_data_join_metrics(job)
        else:
            metrics = []

        # Metrics is a list of dict. Each dict can be rendered by frontend with
        #   mpld3.draw_figure('figure1', json)
        return {'data': metrics}

    def _get_data_join_metrics(self, job):
        num_buckets = 30
        STAT_AGG = {
            "JOINED": {
                "sum": {
                    "field": "tags.joined"
                }
            },
            "FAKED": {
                "sum": {
                    "field": "tags.negative"
                }
            },
            "TOTAL": {
                "sum": {
                    "field": "tags.original"
                }
            },
            "UNJOINED": {
                "bucket_script": {
                    "buckets_path": {
                        "JOINED": "JOINED",
                        "TOTAL": "TOTAL"
                    },
                    "script": "params.TOTAL - params.JOINED"
                }
            },
            "JOIN_RATE": {
                "bucket_script": {
                    "buckets_path": {
                        "JOINED": "JOINED",
                        "TOTAL": "TOTAL",
                        "FAKED": "FAKED"
                    },
                    "script": "params.JOINED / (params.TOTAL + params.FAKED)"
                }
            }
        }

        query = {
            "size": 0,
            "query": {
                "bool": {
                    "must": [
                        {"term": {"tags.application_id.keyword": job.name}},
                        {"term": {"name.keyword": "datajoin"}},
                    ]
                }
            },
            "aggs": {
                "OVERALL": {
                    "terms": {
                        "field": "value"
                    },
                    "aggs": STAT_AGG
                },
                "EVENT_TIME": {
                    "auto_date_histogram": {
                        "field": "tags.event_time_iso",
                        "format": "yyyy-MM-dd'T'HH:mm:ss.SSSSSSZ",
                        "buckets": num_buckets
                    },
                    "aggs": STAT_AGG
                },
                "PROCESS_TIME": {
                    "auto_date_histogram": {
                        "field": "date_time",
                        "format": "yyyy-MM-dd'T'HH:mm:ss.SSSSSSZ",
                        "buckets": num_buckets
                    },
                    "aggs": {
                        "MAX_EVENT_TIME": {
                            "max": {
                                "field": "tags.event_time_iso",
                                "format": "yyyy-MM-dd'T'HH:mm:ss.SSSSSSZ"
                            }
                        },
                        "MIN_EVENT_TIME": {
                            "min": {
                                "field": "tags.event_time_iso",
                                "format": "yyyy-MM-dd'T'HH:mm:ss.SSSSSSZ"
                            }
                        }
                    }
                }
            }
        }

        res = es.search(index='metrics', body=query)

        metrics = []

        # plot pie chart for overall join rate
        overall = res['aggregations']['OVERALL']['buckets'][0]
        labels = ['joined', 'faked', 'unjoined']
        sizes = [
            overall['JOINED']['value'], overall['FAKED']['value'],
            overall['UNJOINED']['value']]
        fig = Figure()
        ax = fig.add_subplot(111)
        ax.pie(sizes, labels=labels, autopct='%1.1f%%')
        metrics.append(mpld3.fig_to_dict(fig))

        # plot stackplot for event time
        by_et = res['aggregations']['EVENT_TIME']['buckets']
        et_index = [to_datetime(buck['key']) for buck in by_et]
        et_joined = [buck['JOINED']['value'] for buck in by_et]
        et_faked = [buck['FAKED']['value'] for buck in by_et]
        et_unjoined = [buck['UNJOINED']['value'] for buck in by_et]
        fig = Figure()
        ax = fig.add_subplot(111)
        ax.stackplot(
            et_index, et_joined, et_faked, et_unjoined, labels=labels)

        twin_ax = ax.twinx()
        twin_ax.patch.set_alpha(0.0)
        et_rate = [buck['JOIN_RATE']['value'] for buck in by_et]
        twin_ax.plot(et_index, et_rate, label='join rate', color='black')

        ax.xaxis_date()
        ax.legend()
        metrics.append(mpld3.fig_to_dict(fig))

        # plot processing time vs event time
        by_pt = res['aggregations']['PROCESS_TIME']['buckets']
        pt_index = [to_datetime(buck['key']) for buck in by_pt]
        pt_min = [
            to_datetime(buck['MIN_EVENT_TIME']['value']) for buck in by_pt]
        pt_max = [
            to_datetime(buck['MAX_EVENT_TIME']['value']) for buck in by_pt]
        fig = Figure()
        ax = fig.add_subplot(111)
        ax.plot(pt_index, pt_min, label='min event time')
        ax.plot(pt_index, pt_max, label='max event time')

        ax.xaxis_date()
        ax.yaxis_date()
        ax.legend()
        metrics.append(mpld3.fig_to_dict(fig))

        return metrics


def initialize_job_apis(api):
    api.add_resource(JobApi, '/jobs/<int:job_id>')
    api.add_resource(PodLogApi,
                     '/pods/<string:pod_name>/log')
    api.add_resource(JobLogApi,
                     '/jobs/<string:job_name>/log')
    api.add_resource(JobMetricsApi,
                     '/jobs/<int:job_id>/metrics')
    api.add_resource(PodContainerApi,
                     '/jobs/<int:job_id>/pods/<string:pod_name>/container')
