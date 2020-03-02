# -*- coding: utf-8 -*-

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
from .db.db_model import Job, DataSourceMeta, ModelMeta,\
                         change_job_status, JOBSTATUS, \
                         ModelVersion
from .job import ROLE
from .kubernetes_client import K8sClient
from .job.job_builder import JobConfigBuidler
from .job.job_resource import PSResourceConfig, MasterResourceConfig,\
                             WorkerResourceConfig
from .scheduler_service import SchedulerServer, SchedulerClient


class Scheduler(object):
    def __init__(self,
                 token_path=settings.K8S_TOKEN_PATH,
                 ca_path=settings.K8S_CAS_PATH,
                 service_host=settings.KUBERNETES_SERVICE_HOST,
                 service_port=settings.KUBERNETES_SERVICE_PORT):
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

    def _receive_job(self, request):
        logging.debug(
            "In Platform Scheduler::_receive_job  application_id = %s",
            request.application_id)

        Job.create(name=request.name,
                   description=request.description,
                   role=ROLE.Follower,
                   application_id=request.application_id,
                   status=JOBSTATUS.SUBMMITTED,
                   version=request.model_train_meta.version,
                   model_uri=request.model_train_meta.model_uri,
                   data_source_name=request.data_meta.data_source_name,
                   k8s_status='init',
                   progress=None,
                   create_time=datetime.datetime.now())

    def run(self, listen_port):
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        ss_grpc.add_SchedulerServicer_to_server(
            SchedulerServer(self._receive_job), self._server)
        self._server.add_insecure_port('[::]:%d' % listen_port)
        self._server.start()
        logging.info('Scheduler Server start on port[%d].', listen_port)
        while True:
            all_submitted_job = self._retrieval(
                wanted_status_list=[JOBSTATUS.SUBMMITTED])
            logging.info('[%d] submitted jobs found', len(all_submitted_job))
            for job in all_submitted_job:
                self.schedule_submitted_job(job)

            all_running_job = self._retrieval(
                wanted_status_list=[JOBSTATUS.RUNNING])
            logging.info('[%d] running jobs found', len(all_running_job))
            for job in all_running_job:
                self.schedule_running_job(job)

            all_killing_job = self._retrieval(
                wanted_status_list=[JOBSTATUS.KILLING, JOBSTATUS.FAILING])
            logging.info('[%d] killing/failing jobs found',
                         len(all_killing_job))
            for job in all_killing_job:
                self.schedule_killing_job(job)

            time.sleep(10)

    def send_job_to_follower(self, job):
        try:
            group_list = json.loads(job.group_list)
            request = ss_pb.JobRequest()
            request.name = job.name
            request.application_id = job.application_id

            request.model_train_meta.model_uri = job.model_uri
            request.model_train_meta.version = job.version
            request.data_meta.data_source_name = job.data_source_name
            request.description = job.description

            for group_uuid in group_list:
                scheduler_client = SchedulerClient(group_uuid)
                scheduler_client.send_job_to_follower(request)
        except Exception as e: #pylint: disable=W0703
            logging.error('send job to follower failed. detail is [%s]',
                          repr(e))

    # deal with "submitted" job to start a k8s job
    def schedule_submitted_job(self, job):
        logging.info('process submitted job id[%d]', job.id)
        try:
            if job.role == ROLE.Leader:
                if not self.send_job_to_follower(job):
                    logging.error('job [%d] change status to failed.'
                                  'reason is [fail send job to follower]',
                                  job.id)
                    change_job_status(job, JOBSTATUS.SUBMMITTED,
                                      JOBSTATUS.FAILED)
                    return
            application_id = '{}-{}-{}'.format(
                job.name.replace('_', ''), str(job.id),
                datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
            data_source = DataSourceMeta.select().where(
                DataSourceMeta.id == job.data_source_id).get()
            model = ModelVersion.select().join(ModelMeta).where(
                ModelVersion.id == job.model_version_id).get()

            checkpoint_path = self._get_checkpoint_path(
                model.model_meta_id.name, application_id)
            export_path = self._get_export_path(model.model_meta_id.name,
                                                job.distributed_version)

            if not data_source or not model:
                logging.error(
                    'job [%d] change status to failed.'
                    'reason is [data_source or model is empty]', job.id)
                change_job_status(job, JOBSTATUS.SUBMMITTED, JOBSTATUS.FAILED)
                return

            builder = JobConfigBuidler(name=application_id,
                                       namespace=job.namespace,
                                       role=job.role,
                                       application_id=application_id)
            cluster_spec = json.loads(job.cluster_spec)
            builder.add_crd(
                PSResourceConfig(application_id=application_id,
                                 image=model.model_meta_id.image,
                                 replicas=cluster_spec.get('ps_replicas', 2)))
            builder.add_crd(
                MasterResourceConfig(application_id=application_id,
                                     data_path=data_source.path,
                                     image=model.model_meta_id.image,
                                     role=job.role.lower(),
                                     replicas=cluster_spec.get(
                                         'master_replicas', 1)))
            builder.add_crd(
                WorkerResourceConfig(application_id=application_id,
                                     checkpoint_path=checkpoint_path,
                                     export_path=export_path,
                                     release_pkg='mnist',
                                     release_tag='0.0.2',
                                     image=model.model_meta_id.image,
                                     role=job.role,
                                     replicas=cluster_spec.get(
                                         'worker_replicas', 2)))

            logging.debug('create crd body content: %s', str(builder.build()))
            print(
                self._k8s_client.create_crd(builder.build(),
                                            namespace=job.namespace))

            job.application_id = application_id
            job.save()
            change_job_status(job, JOBSTATUS.SUBMMITTED, JOBSTATUS.RUNNING)
            logging.info('job [%d] change status to running', job.id)
            return
        except Exception: #pylint: disable=W0703
            change_job_status(job, JOBSTATUS.SUBMMITTED, JOBSTATUS.FAILED)
            logging.error('job create failed on %s', traceback.format_exc())

    def schedule_running_job(self, job):
        logging.info('process running job id[%d]', job.id)
        try:
            self._k8s_client.get_crd_object(name=job.application_id,
                                            namespace=job.namespace)
        except Exception as e: #pylint: disable=W0703
            logging.error('query running job failed on %s', repr(e))

    def schedule_killing_job(self, job):
        logging.info('process killing job id[%d]', job.id)
        try:
            self._k8s_client.delete_crd(name=job.application_id,
                                        namespace=job.namespace)
        except Exception as e: #pylint: disable=W0703
            logging.error('delete job failed on %s', repr(e))
