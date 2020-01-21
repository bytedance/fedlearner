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

from enum import Enum
import os
import socket
import logging
import collections
import grpc
from fedlearner.common.etcd_client import EtcdClient

INTERNAL_PROXY = os.environ.get('INTERNAL_PROXY', None)
ETCD_CLUSTER = os.environ.get('ETCD_CLUSTER', None)
ETCD_ADDRESS = os.environ.get('ETCD_ADDRESS', None)
ETCD_PATH = '/service_discovery'


class ChannelType(Enum):
    UNKNOWN = 0
    INTERNAL = 1
    REMOTE = 2


class _GenericClientInterceptor(grpc.UnaryUnaryClientInterceptor,
                                grpc.UnaryStreamClientInterceptor,
                                grpc.StreamUnaryClientInterceptor,
                                grpc.StreamStreamClientInterceptor):
    def __init__(self, interceptor_function):
        self._fn = interceptor_function

    def intercept_unary_unary(self, continuation, client_call_details,
                              request):
        new_details, new_request_iterator, postprocess = self._fn(
            client_call_details, iter((request, )), False, False)
        response = continuation(new_details, next(new_request_iterator))
        return postprocess(response) if postprocess else response

    def intercept_unary_stream(self, continuation, client_call_details,
                               request):
        new_details, new_request_iterator, postprocess = self._fn(
            client_call_details, iter((request, )), False, True)
        response_it = continuation(new_details, next(new_request_iterator))
        return postprocess(response_it) if postprocess else response_it

    def intercept_stream_unary(self, continuation, client_call_details,
                               request_iterator):
        new_details, new_request_iterator, postprocess = self._fn(
            client_call_details, request_iterator, True, False)
        response = continuation(new_details, new_request_iterator)
        return postprocess(response) if postprocess else response

    def intercept_stream_stream(self, continuation, client_call_details,
                                request_iterator):
        new_details, new_request_iterator, postprocess = self._fn(
            client_call_details, request_iterator, True, True)
        response_it = continuation(new_details, new_request_iterator)
        return postprocess(response_it) if postprocess else response_it


class _ClientCallDetails(
        collections.namedtuple(
            '_ClientCallDetails',
            ('method', 'timeout', 'metadata', 'credentials')),
        grpc.ClientCallDetails):
    pass


def header_adder_interceptor(header, value):
    def intercept_call(client_call_details, request_iterator,
                       request_streaming, response_streaming):
        metadata = []
        if client_call_details.metadata is not None:
            metadata = list(client_call_details.metadata)
        metadata.append((
            header,
            value,
        ))
        client_call_details = _ClientCallDetails(
            client_call_details.method, client_call_details.timeout, metadata,
            client_call_details.credentials)
        return client_call_details, request_iterator, None

    return _GenericClientInterceptor(intercept_call)


def check_address_valid(address):
    try:
        (ip, port_str) = address.split(':')
        if ip == 'localhost' or (socket.inet_aton(ip) and ip.count('.') == 3):
            port = int(port_str)
            if 0 <= port <= 65535:
                return True
        return False
    except Exception as e:  # pylint: disable=broad-except
        logging.debug('%s is not valid address. detail is %s.', address,
                      repr(e))
    return False


def make_insecure_channel(uuid,
                          mode=ChannelType.INTERNAL,
                          options=None,
                          compression=None):
    if check_address_valid(uuid):
        return grpc.insecure_channel(uuid, options, compression)

    if mode == ChannelType.REMOTE:
        header_adder = header_adder_interceptor('uuid', uuid)
        if not INTERNAL_PROXY:
            raise Exception("INTERNAL_PROXY is invalid,"
                            "not found in environment variable.")
        logging.debug("INTERNAL_PROXY is [%s]", INTERNAL_PROXY)
        channel = grpc.insecure_channel(INTERNAL_PROXY, options, compression)
        return grpc.intercept_channel(channel, header_adder)

    if mode == ChannelType.INTERNAL:
        if not ETCD_CLUSTER or not ETCD_ADDRESS:
            raise Exception(
                "ETCD_CLUSTER or ETCD_ADDRESS is invalid, not found in"
                " environment variable.")
        etcd_client = EtcdClient(ETCD_CLUSTER, ETCD_ADDRESS, ETCD_PATH)
        target_addr = etcd_client.get_data(uuid)
        if not target_addr:
            raise Exception(
                "Target service address cant discover by uuid [{}]".format(
                    uuid))
        return grpc.insecure_channel(target_addr, options, compression)

    raise Exception("UNKNOWN Channel by uuid %s" % uuid)
