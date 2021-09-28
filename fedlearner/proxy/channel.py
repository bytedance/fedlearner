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
# pylint: disable=super-init-not-called

from enum import Enum
import os
import socket
import logging
import collections
import grpc
import json

from fedlearner.common import common

EGRESS_URL = os.environ.get('EGRESS_URL', None)
EGRESS_HOST = os.environ.get('EGRESS_HOST', None)
EGRESS_DOMAIN = os.environ.get('EGRESS_DOMAIN', None)

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


def make_insecure_channel(address,
                          mode=ChannelType.INTERNAL,
                          options=None,
                          compression=None):
    if check_address_valid(address):
        return grpc.insecure_channel(address, options, compression)

    if mode == ChannelType.REMOTE:
        if not EGRESS_URL:
            logging.error("EGRESS_URL is invalid,"
                          "not found in environment variable.")
            return grpc.insecure_channel(address, options, compression)

        options = list(options) if options else list()

        logging.debug("EGRESS_URL is [%s]", EGRESS_URL)
        if EGRESS_HOST:
            options.append(('grpc.default_authority', EGRESS_HOST))
            if EGRESS_DOMAIN:
                address = address + '.' + EGRESS_DOMAIN
            header_adder = header_adder_interceptor('x-host', address)
            channel = grpc.insecure_channel(
                EGRESS_URL, options, compression)
            return grpc.intercept_channel(channel, header_adder)

        options.append(('grpc.default_authority', address))
        return grpc.insecure_channel(EGRESS_URL, options, compression)

    if mode == ChannelType.INTERNAL:
        return grpc.insecure_channel(address, options, compression)

    raise Exception("UNKNOWN Channel by uuid %s" % address)

def make_secure_channel(address,
                        mode=ChannelType.INTERNAL,
                        options=None,
                        compression=None):
    use_tls, creds = common.use_tls()
    assert use_tls, "In-consistant TLS enabling"
    with open("dynamic_config.json", "r", encoding='utf-8') as fp:
        MEASUREMENTS = json.load(fp)["sgx_mrs"][0]
        MR_ENCLAVE = MEASUREMENTS["MR_ENCLAVE"]
        MR_SIGNER = MEASUREMENTS["MR_SIGNER"]
        ISV_PROD_ID = MEASUREMENTS["ISV_PROD_ID"]
        ISV_SVN = MEASUREMENTS["ISV_SVN"]
    tls_creds =  grpc.sgxratls_channel_credentials(MR_ENCLAVE, MR_SIGNER, ISV_PROD_ID, ISV_SVN)
    if check_address_valid(address):
        return grpc.secure_channel(address, tls_creds, options, compression)

    if mode == ChannelType.REMOTE:
        if not EGRESS_URL:
            logging.error("EGRESS_URL is invalid,"
                          "not found in environment variable.")
            return grpc.secure_channel(address, tls_creds, options, compression)

        options = list(options) if options else list()

        logging.debug("EGRESS_URL is [%s]", EGRESS_URL)
        if EGRESS_HOST:
            options.append(('grpc.default_authority', EGRESS_HOST))
            if EGRESS_DOMAIN:
                address = address + '.' + EGRESS_DOMAIN
            header_adder = header_adder_interceptor('x-host', address)
            channel = grpc.secure_channel(
                EGRESS_URL, tls_creds, options, compression)
            return grpc.intercept_channel(channel, header_adder)

        options.append(('grpc.default_authority', address))
        return grpc.secure_channel(EGRESS_URL, tls_creds, options, compression)

    if mode == ChannelType.INTERNAL:
        return grpc.secure_channel(address, tls_creds, options, compression)

    raise Exception("UNKNOWN Channel by uuid %s" % address)
