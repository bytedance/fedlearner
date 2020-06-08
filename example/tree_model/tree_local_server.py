import numpy as np
from fedlearner.common import compute_histogram_pb2_grpc,compute_histogram_pb2
import multiprocessing as mp
import logging
import grpc
from concurrent import futures

from fedlearner.model.crypto import paillier
from fedlearner.model.tree.tree import _from_ciphertext,PRECISION,_encode_encrypted_numbers


def _compute_histogram_helper(args):
    print("server is working")
    base, values, binned_features, thresholds, zero = args
    hists = []
    for i, threshold_size in enumerate(thresholds):
        logging.debug('Computing histogram for feature %d', base + i)
        num_bins = threshold_size + 2
        hist = np.asarray([zero for _ in range(num_bins)])
        np.add.at(hist, binned_features[:, i], values)
        hists.append(hist)
    return hists

# base,values,binned_features,thresholds,zero
def _leader_server(msg):
    def protp_to_array(msg):
        array = np.frombuffer(msg.values,dtype=np.dtype(msg.dtype))
        array = np.reshape(array,newshape=msg.shape)
        return array
    base = msg.base
    values = protp_to_array(msg.values)
    binned_features = protp_to_array(msg.binned_features)
    thresholds = msg.thresholds
    zero = 0.
    args = [base,values,binned_features,thresholds,zero]
    return _compute_histogram_helper(args)

def _leader_reply(hists):
    def ndarrattomsg(array, msg):
        msg.values = array.tobytes()
        msg.shape.extend(list(array.shape))
        msg.dtype = str(array.dtype)
    msg = compute_histogram_pb2.histogram_leader()
    for array in hists:
        msg_arr = msg.hists.add()
        ndarrattomsg(array, msg_arr)
    return msg


def _follower_server(msg):
    def normal_to_array(msg):
        array = np.frombuffer(msg.values,dtype=np.dtype(msg.dtype))
        array = np.reshape(array,newshape=msg.shape)
        return array
    def paillier_to_arr(msg):
        arr = np.array(_from_ciphertext(pulic_key,msg.values))
        arr = np.reshape(arr,newshape=msg.shape)
        return arr
    # 得到key
    pulic_key = paillier.PaillierPublicKey(
        int.from_bytes(msg.public_key, 'little'))
    # values 需要特殊处理
    values = paillier_to_arr(msg.values)

    base = msg.base
    binned_features = normal_to_array(msg.binned_features)
    thresholds = msg.thresholds
    zero = pulic_key.encrypt(0,precision=PRECISION)
    args = [base,values,binned_features,thresholds,zero]
    return _compute_histogram_helper(args)

def _follower_reply(hists):
    def ndarrattomsg(array, msg):
        msg.shape.extend(list(array.shape))
        msg.values.extend(_encode_encrypted_numbers(array.flatten()))

    msg = compute_histogram_pb2.histogram_follower()
    for array in hists:
        msg_arr = msg.hists.add()
        ndarrattomsg(array, msg_arr)
    return msg

class HistsServer(compute_histogram_pb2_grpc.HistsServiceServicer):
    def ComputeHists_leader(self, request, context):
        hists = _leader_server(request)
        return _leader_reply(hists)
    def ComputeHists_follower(self, request, context):
        hists = _follower_server(request)
        return _follower_reply(hists)

def sever_service(addr):
    addr = addr
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    compute_histogram_pb2_grpc.add_HistsServiceServicer_to_server(HistsServer(), server)
    server.add_insecure_port(addr)
    server.start()
    server.wait_for_termination(timeout=10)

server_addrs = ['localhost:60061','localhost:60062','localhost:60063','localhost:60064']
num_leader_server = len(server_addrs)
server_pool = mp.Pool(num_leader_server)
server_pool.map(sever_service, server_addrs)
