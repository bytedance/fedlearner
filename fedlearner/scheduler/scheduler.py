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
import traceback
import json
import logging
import datetime
from concurrent import futures

import grpc
from fedlearner import settings
from fedlearner.common import scheduler_service_pb2 as ss_pb
from fedlearner.common import scheduler_service_pb2_grpc as ss_grpc
from fedlearner.common import common_pb2 as common_pb
from .db.db_model import Job, DataSourceMeta, ModelMeta,\
                         change_job_status, JOBSTATUS, \
                         ModelVersion, APPSTATUS
from .kubernetes_client import K8sClient
from .job.job_builder import JobConfigBuidler
from .job.job_resource import PSResourceConfig, MasterResourceConfig,\
                             WorkerResourceConfig
from .scheduler_service import SchedulerServer, SchedulerClient


def receive_job(request):
    logging.debug("In Platform Scheduler::_receive_job  application_id = %s",
                  request.application_id)
    response = common_pb.Status()
    try:
        model_meta = ModelMeta.get(ModelMeta.name == request.model_uri)
    except Exception:  #pylint: disable=W0703
        response.code = common_pb.StatusCode.STATUS_UNKNOWN_ERROR
        response.error_message = 'model_uri [%s] was not authorized.' \
                                 % request.model_uri
        return response

    try:
        model_version = ModelVersion.get(
            (ModelVersion.commit == request.model_commit)
            and (ModelVersion.model_meta_id == model_meta.id))
    except Exception:  #pylint: disable=W0703
        response.code = common_pb.StatusCode.STATUS_UNKNOWN_ERROR
        response.error_message = 'model_uri [%s] model_version [%s] ' \
                                 'was not authorized.' % \
                                 (request.model_uri, request.model_commit)
        return response

    try:
        data_source = DataSourceMeta.get(
            DataSourceMeta.name == request.data_meta.data_source_name)
    except Exception:  #pylint: disable=W0703
        response.code = common_pb.StatusCode.STATUS_UNKNOWN_ERROR
        response.error_message = 'data_source [%s] was not authorized.' \
                                 % (request.data_meta.data_source_name)
        return response

    job = Job.create(name=request.name,
                     description=request.description,
                     role='Follower',
                     application_id=request.application_id,
                     status=JOBSTATUS.SUBMMITTED.value,
                     model_version_id=model_version.id,
                     serving_version=request.serving_version,
                     data_source_id=data_source.id,
                     cluster_spec=json.dumps(
                         {'worker_replicas': request.pair_num}),
                     group_list=json.dumps([]),
                     create_time=datetime.datetime.now())
    if not job:
        response.code = common_pb.StatusCode.STATUS_UNKNOWN_ERROR
        response.error_message = 'job [%s] create failed.' % request.name
        return response
    response.code = common_pb.StatusCode.STATUS_SUCCESS
    return response


def send_job_to_follower(job):
    try:
        job = Job.select(Job, ModelMeta, ModelVersion, DataSourceMeta).\
                   join(ModelVersion).join(ModelMeta).\
                   join(DataSourceMeta,
                        on=(Job.data_source_id == DataSourceMeta.id)).\
                    where(Job.id == job.id).get()

        group_list = json.loads(job.group_list)
        cluster_spec = json.loads(job.cluster_spec)
        request = ss_pb.TrainJobRequest()
        request.name = job.name
        request.application_id = job.application_id
        request.model_uri = job.model_version_id.model_meta_id.name
        request.model_commit = job.model_version_id.commit
        request.serving_version = job.serving_version
        request.data_meta.data_source_name = job.data_source_id.name
        request.pair_num = cluster_spec['worker_replicas']
        request.description = job.description

        for group_uuid in group_list:
            scheduler_client = SchedulerClient(group_uuid)
            scheduler_client.submit_train(request)
            logging.info(
                'send job application_id[%s] model_uri [%s]'
                'data_source[%s] pair_num[%d] to follower[%s]',
                request.application_id, request.model_uri,
                request.data_meta.data_source_name, request.pair_num,
                group_uuid)
        return True

    except Exception as e:  #pylint: disable=W0703
        logging.error('send job to follower failed. detail is [%s]', repr(e))
        return False


class Scheduler(object):
    def __init__(self,
                 token_path=settings.K8S_TOKEN_PATH,
                 ca_path=settings.K8S_CAS_PATH,
                 service_host=settings.KUBERNETES_SERVICE_HOST,
                 service_port=settings.KUBERNETES_SERVICE_PORT):
        logging.info('KUBERNETES_SERVICE_HOST: [%s]', service_host)
        logging.info('KUBERNETES_SERVICE_PORT: [%s]', service_port)
        self._k8s_client = K8sClient(token_path=token_path,
                                     ca_path=ca_path,
                                     service_host=service_host,
                                     service_port=service_port)

    def _retrieval(self, wanted_status_list):
        retrieval_job = Job.select().where(Job.status << wanted_status_list)
        return retrieval_job

    def _get_checkpoint_path(self, model_uri, application_id):
        return settings.CHECKPOINT_PATH_PREFIX + '/' + model_uri\
                 + '/'+ application_id

    def _get_export_path(self, model_uri, version):
        return settings.EXPORT_PATH_PREFIX + '/' + model_uri + '/' + version

    def run(self, listen_port):
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        ss_grpc.add_SchedulerServicer_to_server(SchedulerServer(receive_job),
                                                self._server)
        self._server.add_insecure_port('[::]:%d' % listen_port)
        self._server.start()
        logging.info('Scheduler Server start on port[%d].', listen_port)
        while True:
            all_submitted_job = self._retrieval(
                wanted_status_list=[JOBSTATUS.SUBMMITTED.value])
            logging.info('[%d] submitted jobs found', len(all_submitted_job))
            for job in all_submitted_job:
                self.schedule_submitted_job(job)

            all_running_job = self._retrieval(
                wanted_status_list=[JOBSTATUS.RUNNING.value])
            logging.info('[%d] running jobs found', len(all_running_job))
            for job in all_running_job:
                self.schedule_running_job(job)

            all_killing_job = self._retrieval(wanted_status_list=[
                JOBSTATUS.KILLING.value, JOBSTATUS.FAILING.value
            ])
            logging.info('[%d] killing/failing jobs found',
                         len(all_killing_job))
            for job in all_killing_job:
                self.schedule_killing_job(job)

            time.sleep(10)

    # deal with "submitted" job to start a k8s job
    def schedule_submitted_job(self, job):
        logging.info('process submitted job id[%d]', job.id)
        if not job.application_id:
            job.application_id = '{}-{}-{}'.format(
                job.name.replace('_', ''), str(job.id),
                datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
            job.save()

        logging.info(job.role)
        try:
            if job.role == 'Leader':
                if not send_job_to_follower(job):
                    logging.error(
                        'job [%d] change status to failed.'
                        'reason is [fail send job to follower]', job.id)
                    change_job_status(job, JOBSTATUS.SUBMMITTED.value,
                                      JOBSTATUS.FAILED.value)
                    return

            data_source = DataSourceMeta.select().where(
                DataSourceMeta.id == job.data_source_id).get()
            model = ModelVersion.select().join(ModelMeta).where(
                ModelVersion.id == job.model_version_id).get()

            checkpoint_path = self._get_checkpoint_path(
                model.model_meta_id.name, job.application_id)
            export_path = self._get_export_path(model.model_meta_id.name,
                                                job.serving_version)

            if not data_source or not model:
                logging.error(
                    'job [%d] change status to failed.'
                    'reason is [data_source or model is empty]', job.id)
                change_job_status(job, JOBSTATUS.SUBMMITTED.value,
                                  JOBSTATUS.FAILED.value)
                return

            builder = JobConfigBuidler(name=job.application_id,
                                       role=job.role,
                                       application_id=job.application_id)
            cluster_spec = json.loads(job.cluster_spec)
            builder.add_crd(
                PSResourceConfig(application_id=job.application_id,
                                 image=model.model_meta_id.image,
                                 replicas=cluster_spec.get('ps_replicas', 2)))
            builder.add_crd(
                MasterResourceConfig(application_id=job.application_id,
                                     data_path=data_source.path,
                                     image=model.model_meta_id.image,
                                     role=job.role.lower(),
                                     replicas=cluster_spec.get(
                                         'master_replicas', 1)))
            builder.add_crd(
                WorkerResourceConfig(application_id=job.application_id,
                                     checkpoint_path=checkpoint_path,
                                     export_path=export_path,
                                     release_pkg='mnist',
                                     release_tag='0.0.2',
                                     image=model.model_meta_id.image,
                                     role=job.role.lower(),
                                     replicas=cluster_spec.get(
                                         'worker_replicas', 2)))

            logging.info('create crd body content: %s namespace: %s',
                         str(builder.build()), settings.K8S_NAMESPACE)
            self._k8s_client.create_crd(builder.build(),
                                              namespace=settings.K8S_NAMESPACE)
            change_job_status(job, JOBSTATUS.SUBMMITTED.value,
                              JOBSTATUS.RUNNING.value)
            logging.info('job [%d] change status to running', job.id)
            return
        except Exception:  #pylint: disable=W0703
            change_job_status(job, JOBSTATUS.SUBMMITTED.value,
                              JOBSTATUS.FAILED.value)
            logging.error('job create failed on %s', traceback.format_exc())

    def schedule_running_job(self, job):
        logging.info('process running job id[%d]', job.id)
        try:
            response = self._k8s_client.get_crd_object(
                name=job.application_id, namespace=settings.K8S_NAMESPACE)
            if not response:
                logging.error('kubernetes get crd object failed.')
                change_job_status(job, JOBSTATUS.RUNNING.value,
                                  JOBSTATUS.FAILED.value)
            if response:
                app_state = response.get('status', {}).get('appState', None)
                if not app_state:
                    logging.error(
                        'kubernetes get crd object app [%d] status failed.',
                        job.id)
                    return

                job.k8s_status = app_state
                logging.info('job [%d] get kubernetes applicaiton status [%s]',
                             job.id, app_state)
                job.save()
                if job.k8s_status == APPSTATUS.FAILED.value:
                    change_job_status(job, JOBSTATUS.RUNNING.value,
                                      JOBSTATUS.FAILED.value)
                elif job.k8s_status == APPSTATUS.SHUTDOWN.value:
                    change_job_status(job, JOBSTATUS.RUNNING.value,
                                      JOBSTATUS.KILLED.value)
                elif job.k8s_status == APPSTATUS.COMPELTE.value:
                    change_job_status(job, JOBSTATUS.RUNNING.value,
                                      JOBSTATUS.SUCCESS.value)

        except Exception as e:  #pylint: disable=W0703
            logging.error('query running job failed on %s',
                          traceback.format_exc())

    def schedule_killing_job(self, job):
        logging.info('process killing job id[%d]', job.id)
        try:
            self._k8s_client.delete_crd(name=job.application_id,
                                        namespace=settings.K8S_NAMESPACE)
            change_job_status(job, JOBSTATUS.KILLING.value,
                              JOBSTATUS.KILLED.value)
        except Exception as e:  #pylint: disable=W0703
            logging.error('delete job failed on %s', repr(e))
