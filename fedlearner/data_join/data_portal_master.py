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

import logging
from concurrent import futures

import grpc
from google.protobuf import empty_pb2

from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_portal_service_pb2 as dp_pb
from fedlearner.common import data_portal_service_pb2_grpc as dp_grpc

from fedlearner.common.db_client import DBClient

from fedlearner.data_join.data_portal_job_manager import DataPortalJobManager
from fedlearner.data_join.routine_worker import RoutineWorker

class DataPortalMaster(dp_grpc.DataPortalMasterServiceServicer):
    def __init__(self, portal_name, kvstore, portal_options):
        super(DataPortalMaster, self).__init__()
        self._portal_name = portal_name
        self._kvstore = kvstore
        self._portal_options = portal_options
        self._data_portal_job_manager = DataPortalJobManager(
                self._kvstore, self._portal_name,
                self._portal_options.long_running,
                self._portal_options.check_success_tag,
                self._portal_options.single_subfolder,
                self._portal_options.files_per_job_limit,
                start_date=self._portal_options.start_date,
                end_date=self._portal_options.end_date
            )
        self._bg_worker = None

    def GetDataPortalManifest(self, request, context):
        return self._data_portal_job_manager.get_portal_manifest()

    def RequestNewTask(self, request, context):
        response = dp_pb.NewTaskResponse()
        finished, task = \
            self._data_portal_job_manager.alloc_task(request.rank_id)
        if task is not None:
            if isinstance(task, dp_pb.MapTask):
                response.map_task.MergeFrom(task)
            else:
                assert isinstance(task, dp_pb.ReduceTask)
                response.reduce_task.MergeFrom(task)
        elif not finished:
            response.pending.MergeFrom(empty_pb2.Empty())
        else:
            response.finished.MergeFrom(empty_pb2.Empty())
        return response

    def FinishTask(self, request, context):
        self._data_portal_job_manager.finish_task(request.rank_id,
                                                  request.partition_id,
                                                  request.part_state)
        return common_pb.Status()

    def start(self):
        self._bg_worker = RoutineWorker(
                'portal_master_bg_worker',
                self._data_portal_job_manager.backgroup_task,
                lambda: True, 30
            )
        self._bg_worker.start_routine()

    def stop(self):
        if self._bg_worker is not None:
            self._bg_worker.stop_routine()
        self._bg_worker = None

class DataPortalMasterService(object):
    def __init__(self, listen_port, portal_name,
                 kvstore_type, portal_options):
        self._portal_name = portal_name
        self._listen_port = listen_port
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        kvstore = DBClient(kvstore_type, portal_options.use_mock_etcd)
        self._data_portal_master = DataPortalMaster(portal_name, kvstore,
                                                    portal_options)
        dp_grpc.add_DataPortalMasterServiceServicer_to_server(
                self._data_portal_master, self._server
            )
        self._server.add_insecure_port('[::]:%d'%listen_port)
        self._server_started = False

    def start(self):
        if not self._server_started:
            self._server.start()
            self._data_portal_master.start()
            self._server_started = True
            logging.warning("DataPortalMasterService name as %s start " \
                            "on port[%d]:",
                            self._portal_name, self._listen_port)

    def stop(self):
        if self._server_started:
            self._data_portal_master.stop()
            self._server.stop(None)
            self._server_started = False
            logging.warning("DataPortalMasterService name as %s"\
                            "stopped ", self._portal_name)

    def run(self):
        self.start()
        self._server.wait_for_termination()
        self.stop()
