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

import argparse
import logging
from concurrent import futures

import grpc

from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common import data_join_service_pb2_grpc as dj_grpc

from fedlearner.common.etcd_client import EtcdClient

from fedlearner.data_join.common import retrieve_portal_manifest
from fedlearner.data_join.portal_repartitioner import PortalRepartitioner
from fedlearner.data_join.portal_raw_data_notifier import PortalRawDataNotifier

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
        if len(self._portal_options.downstream_data_source_masters) > 0:
            self._portal_raw_data_notifier = PortalRawDataNotifier(
                    self._etcd,
                    self._portal_name,
                    self._portal_options.downstream_data_source_masters
                )
            logging.info("launch data join portal with raw data notifier "\
                         "for following downstream data source masters:")
            for master_addr in \
                    self._portal_options.downstream_data_source_masters:
                logging.info(master_addr)
        else:
            self._portal_raw_data_notifier = None
            logging.info("launch data join portal without raw data notifier")

    def Ping(self, request, context):
        return common_pb.Status(code=0)

    def start(self):
        self._portal_repartitioner.start_routine_workers()
        if self._portal_raw_data_notifier is not None:
            self._portal_raw_data_notifier.start_notify_worker()

    def stop(self):
        self._portal_repartitioner.stop_routine_workers()
        if self._portal_raw_data_notifier is not None:
            self._portal_raw_data_notifier.stop_notify_worker()

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

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    parser = argparse.ArgumentParser(description='DataJointPortal cmd.')
    parser.add_argument('data_join_portal_name', type=str,
                        help='the name of data join portal')
    parser.add_argument('--etcd_name', type=str,
                        default='test_etcd', help='the name of etcd')
    parser.add_argument('--etcd_addrs', type=str,
                        default='localhost:2379', help='the addrs of etcd')
    parser.add_argument('--etcd_base_dir', type=str,
                        default='fedlearner_protal_test',
                        help='the namespace of etcd key for data join portal')
    parser.add_argument('--downstream_data_source_masters', type=str,
                        nargs='*', help='the addrs of downstream data '\
                                         'source to notify new raw data')
    parser.add_argument('--use_mock_etcd', action='store_true',
                        help='use to mock etcd for test')
    parser.add_argument('--input_data_file_iter', type=str, default='TF_RECORD',
                        help='the type for iter of input data file')
    parser.add_argument('--compressed_type', type=str, default='',
                        choices=['', 'ZLIB', 'GZIP'],
                        help='the compressed type of input data file')
    parser.add_argument('--portal_reducer_buffer_size', type=int,
                        default=4096, help='the buffer size of portal reducer')
    parser.add_argument('--example_validator', type=str,
                        default='EXAMPLE_VALIDATOR',
                        help='the name of example validator')
    parser.add_argument('--validate_event_time', action='store_true',
                        help='validate the example has event time')
    args = parser.parse_args()
    options = dj_pb.DataJoinPotralOptions(
            example_validator=dj_pb.ExampleValidatorOptions(
                example_validator=args.example_validator,
                validate_event_time=args.validate_event_time
            ),
            reducer_buffer_size=args.portal_reducer_buffer_size,
            raw_data_options=dj_pb.RawDataOptions(
                raw_data_iter=args.input_data_file_iter,
                compressed_type=args.compressed_type
            ),
            downstream_data_source_masters=args.downstream_data_source_masters,
            use_mock_etcd=args.use_mock_etcd
        )
    portal_srv = DataJoinPortalService(
            args.listen_port, args.data_join_portal_name,
            args.etcd_name, args.etcd_addrs,
            args.etcd_base_dir, options,
        )
    portal_srv.run()
