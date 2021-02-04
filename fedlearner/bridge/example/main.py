# -*- coding: utf-8 -*-

import argparse
import time
import logging
import threading
import signal

import greester_pb2, greester_pb2_grpc
from fedlearner.bridge import bridge

class GreesterrHandler(greester_pb2_grpc.GreesterServicer):
    def HelloUnaryUnary(self, request, context):
        #print(f'HelloUnaryUnary receive: {request.name}')
        return greester_pb2.Response(message=f"Hello {request.name}")

    def HelloUnaryStream(self, request, context):
        #print(f'HelloUnaryStream receive: {request.name}')
        for i in range(2):
            yield greester_pb2.Response(message=f"Hello {request.name}")

    def HelloStreamUnary(self, request_iterator, context):
        names = []
        for req in request_iterator:
            #print(f'HelloStreamUnary receive:{req.name}')
            names.append(req.name)

        return greester_pb2.Response(message="Hello {}".format(",".join(names)))

    def HelloStreamStream(self, request_iterator, context):
        for req in request_iterator:
            #print(f'HelloStreamStream receive:{req.name}')
            yield greester_pb2.Response(message=f"Hello {req.name}")

def client_run_fn(bridge):
    client = greester_pb2_grpc.GreesterStub(bridge)
    while not bridge.is_closed():
        res = client.HelloUnaryUnary(greester_pb2.Request(name='UnaryUnary'))
        print("Greeter HelloUnaryUnary return: " + res.message)

        res_iter = client.HelloUnaryStream(greester_pb2.Request(name='UnaryStream'))
        for res in res_iter:
            print("Greeter HelloUnaryStream return: " + res.message)

        def req_iter(name):
            for _ in range(2):
                yield greester_pb2.Request(name=name)

        res = client.HelloStreamUnary(req_iter('StreamUnary'))
        print("Greeter HelloStreamUnary return: " + res.message)

        res_iter = client.HelloStreamStream(req_iter('StreamStream'))
        for res in res_iter:
            print("Greeter HelloStreamStream return: " + res.message)

        time.sleep(5)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] %(asctime)s: %(message)s in %(pathname)s:%(lineno)d")

    parser = argparse.ArgumentParser()
    parser.add_argument('--listen_addr', type=str, default='[::]:50050')
    parser.add_argument('--remote_addr', type=str, default='[::]:50051')
    args = parser.parse_args()

    bridge = bridge.Bridge(args.listen_addr, args.remote_addr)
    greester_pb2_grpc.add_GreesterServicer_to_server(GreesterrHandler(), bridge) 

    def signal_handler(signum, _):
        logging.warn("receiver signal: %d, will close bridge", signum)
        bridge.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)

    thread = threading.Thread(target=client_run_fn, args=(bridge,))
    thread.start()
    bridge.start()
    bridge.wait_for_stopped()
    thread.join()