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

# -*- coding: utf-8 -*-

import time
import argparse
import logging
import signal
import threading
from test.channel import greeter_pb2, greeter_pb2_grpc 

from fedlearner.channel import Channel

class _Server(greeter_pb2_grpc.GreeterServicer):
    def HelloUnaryUnary(self, request, context):
        return greeter_pb2.Response(
            message="[HelloUnaryUnary]: Hello " + request.name)

    def HelloUnaryStream(self, request, context):
        def response_iterator():
            for i in range (5):
                yield greeter_pb2.Response(
                    message="[HelloUnaryStream]: Hello " + request.name)

        return response_iterator()

    def HelloStreamUnary(self, request_iterator, context):
        response = "[HelloStreamUnary]: Hello"
        for request in request_iterator:
            response += " " + request.name

        return greeter_pb2.Response(message=response)

    def HelloStreamStream(self, request_iterator, context):
        def response_iterator():
            for request in request_iterator:
                yield greeter_pb2.Response(
                    message="[HelloStreamStream]: Hello " + request.name)

        return response_iterator()

terminate_event = threading.Event()

def _client_run_fn(client):
    while not terminate_event.is_set():
        # unary_unary
        response = client.HelloUnaryUnary(
            greeter_pb2.Request(name="example"))
        print(response.message)

        ## unary_stream
        #response_iterator = \
        #    client.HelloUnaryStream(request)
        #for response in response_iterator:
        #    print(response.message)
    
        # stream_unary
        def request_iteartor(times):
            for i in range(times):
                if terminate_event.is_set():
                    return
                yield greeter_pb2.Request(name="example"+str(i))
                terminate_event.wait(0.5)

        #response = client.HelloStreamUnary(request_iteartor(5))
        #print(response.message)

        # stream_stream
        response_iterator = \
            client.HelloStreamStream(request_iteartor(10))
        for response in response_iterator:
            print(response.message)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s]"
        " %(asctime)s: %(message)s in %(pathname)s:%(lineno)d")
    parser = argparse.ArgumentParser() 
    parser.add_argument('--listen-addr', type=str,
                        help='Listen address of the local channel, ' \
                             'in [IP]:[PORT] format')
    parser.add_argument('--peer-addr', type=str,
                        help='Address of peer\'s channel, ' \
                             'in [IP]:[PORT] format')
    parser.add_argument('--token', type=str,
                        help='channel token', default='test_token')
    args = parser.parse_args()

    def signal_handler(signum, frame):
        print('Signal handler called with signal ', signum)
        terminate_event.set()

    def channel_handler(channel, event):
        print("channel event callback: ", event)
        if event == Channel.Event.PEER_CLOSED:
            print("channel peer closed")
            terminate_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)

    channel = Channel(args.listen_addr, args.peer_addr, token=args.token)
    channel.subscribe(channel_handler)

    client = greeter_pb2_grpc.GreeterStub(channel)
    greeter_pb2_grpc.add_GreeterServicer_to_server(
        _Server(), channel)
    channel.connect(wait=False)
    thread = threading.Thread(target=_client_run_fn,
                               args=(client,),
                               daemon=True)
    thread.start()
    thread.join()
    channel.close()