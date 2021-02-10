# -*- coding: utf-8 -*-

import argparse
import time
import logging
import threading
import signal


import greeter_pb2, greeter_pb2_grpc
from fedlearner.bridge import bridge

class GreeterrHandler(greeter_pb2_grpc.GreeterServicer):
    def HelloUnaryUnary(self, request, context):
        #print(f'HelloUnaryUnary receive: {request.name}')
        return greeter_pb2.Response(message=f"Hello {request.name}")

    def HelloUnaryStream(self, request, context):
        #print(f'HelloUnaryStream receive: {request.name}')
        for i in range(2):
            yield greeter_pb2.Response(message=f"Hello {request.name}")

    def HelloStreamUnary(self, request_iterator, context):
        names = []
        for req in request_iterator:
            #print(f'HelloStreamUnary receive:{req.name}')
            names.append(req.name)

        return greeter_pb2.Response(message="Hello {}".format(",".join(names)))

    def HelloStreamStream(self, request_iterator, context):
        for req in request_iterator:
            #print(f'HelloStreamStream receive:{req.name}')
            yield greeter_pb2.Response(message=f"Hello {req.name}")
            time.sleep(1)

def client_run_fn(bridge):
    client = greeter_pb2_grpc.GreeterStub(bridge)
    #while not bridge.is_closed:
#        res = client.HelloUnaryUnary(greeter_pb2.Request(name='UnaryUnary'))
#        print("Greeter HelloUnaryUnary return: " + res.message)
#
#        res_iter = client.HelloUnaryStream(greeter_pb2.Request(name='UnaryStream'))
#        for res in res_iter:
#            print("Greeter HelloUnaryStream return: " + res.message)
#
    def req_iter(name):
        for i in range(100):
            yield greeter_pb2.Request(name=str(i))
            time.sleep(0.5)
#
#    res = client.HelloStreamUnary(req_iter('StreamUnary'))
#    print("Greeter HelloStreamUnary return: " + res.message)
#
    res_iter = client.HelloStreamStream(req_iter('StreamStream'))
    for res in res_iter:
        print("Greeter HelloStreamStream return: " + res.message)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] %(asctime)s: %(message)s in %(pathname)s:%(lineno)d")

    parser = argparse.ArgumentParser()
    parser.add_argument('--listen_addr', type=str, default='[::]:50050')
    parser.add_argument('--remote_addr', type=str, default='[::]:50051')
    parser.add_argument('--client', action='store_true')
    args = parser.parse_args()

    def callback(bridge, event):
        print("callback event: ", event.name)

    def closed_callback(bridge, event):
        bridge.stop()

    bridge = bridge.Bridge(args.listen_addr, args.remote_addr)
    bridge.subscribe(callback)
    bridge.subscribe_event(bridge.Event.PEER_CLOSED, closed_callback)
    greeter_pb2_grpc.add_GreeterServicer_to_server(GreeterrHandler(), bridge) 

    def signal_handler(signum, _):
        logging.warn("receiver signal: %d, will close bridge", signum)
        bridge.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)

    if args.client:
        thread = threading.Thread(target=client_run_fn,
            args=(bridge,), daemon=True)
        thread.start()

    bridge.start()
    bridge.wait_for_termination()