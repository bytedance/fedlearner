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

from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2_grpc as dj_grpc

from fedlearner.common.etcd_client import EtcdClient

from fedlearner.data_join.common import retrieve_portal_manifest
from fedlearner.data_join.portal_repartitioner import PortalRepartitioner

class DataJoinPortal(dj_grpc.DataJoinPotralServiceServicer):
    def __init__(self, portal_name, etcd_name, etcd_addrs,
                 etcd_base_dir, portal_options):
        super(DataJoinPortal, self).__init__()
        self._portal_name = portal_name
        self._etcd = EtcdClient(etcd_name, etcd_addrs, etcd_base_dir,
                                portal_options.use_mock_etcd)
        self._portal_manifest = retrieve_portal_manifest(
                self._etcd, self._portal_name
            )
        self._portal_options = portal_options
        self._portal_repartitioner = PortalRepartitioner(
                self._etcd, self._portal_manifest,
                self._portal_options
            )

    def Ping(self, request, context):
        return common_pb.Status(code=0)

    def start(self):
        self._portal_repartitioner.start_routine_workers()

    def stop(self):
        self._portal_repartitioner.stop_routine_workers()

class DataJoinPortalService(object):
    def __init__(self, listen_port, portal_name, etcd_name,
                 etcd_base_dir, etcd_addrs, portal_options):
        self._portal_name = portal_name
        self._listen_port = listen_port
        self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        self._data_join_portal = DataJoinPortal(portal_name,
                                                etcd_name, etcd_addrs,
                                                etcd_base_dir, portal_options)
        dj_grpc.add_DataJoinPortalServiceServicer_to_server(
                self._data_join_portal, self._server
            )
        self._server.add_insecure_port('[::]:%d'%listen_port)
        self._server_started = False

    def start(self):
        if not self._server_started:
            self._server.start()
            self._data_join_portal.start()
            self._server_started = True
            logging.warning("DataJoinPortalService name as %s start " \
                            "on port[%d]:",
                            self._portal_name, self._listen_port)

    def stop(self):
        if self._server_started:
            self._data_join_portal.stop()
            self._server.stop(None)
            self._server_started = False
            logging.warning("DataJoinPortalService name as %s"\
                            "stopped ", self._portal_name)

    def run(self):
        self.start()
        self._server.wait_for_termination()
        self.stop()
