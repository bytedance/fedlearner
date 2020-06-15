import argparse

import numpy as np
from fedlearner.common import tree_model_pb2_grpc, tree_model_pb2
import multiprocessing as mp
import logging
import grpc
from concurrent import futures

from fedlearner.model.crypto import paillier
from fedlearner.model.tree.tree import _from_ciphertext, PRECISION, _encode_encrypted_numbers, _decrypt_number, \
    _encrypt_numbers, MAX_MESSAGE_LENGTH


def _compute_histogram_helper(args):
    base, values, binned_features, num_bins, zero = args
    hists = []
    for i, num in enumerate(num_bins):
        logging.debug('Computing histogram for feature %d', base + i)
        hist = np.asarray([zero for _ in range(num)])
        np.add.at(hist, binned_features[:, i], values)
        hists.append(hist)
    return hists


def _decrypt_histogram_helper(args):
    base, public_key, private_key, hists = args
    rets = []
    for i, hist in enumerate(hists):
        logging.debug('Decrypting histogram for feature %d', base + i)
        hist = _from_ciphertext(public_key, hist.ciphertext)
        rets.append(np.asarray(_decrypt_number(private_key, hist)))
    return rets


# base,values,binned_features,thresholds,zero
def _leader_compute_histogram_server(msg):
    def protp_to_array(msg):
        array = np.frombuffer(msg.values, dtype=np.dtype(msg.dtype))
        array = np.reshape(array, newshape=msg.shape)
        return array

    base = msg.base
    values = protp_to_array(msg.values)
    binned_features = protp_to_array(msg.binned_features)
    thresholds = msg.thresholds
    zero = 0.
    args = [base, values, binned_features, thresholds, zero]
    return _compute_histogram_helper(args)


def _leader_reply(hists):
    def ndarrattomsg(array, msg):
        msg.values = array.tobytes()
        msg.shape.extend(list(array.shape))
        msg.dtype = str(array.dtype)

    msg = tree_model_pb2.histogram_leader()
    for array in hists:
        msg_arr = msg.hists.add()
        ndarrattomsg(array, msg_arr)
    return msg


def _leader_decrypt_histogram_server(msg):
    def bytes_to_n(bytes):
        return int.from_bytes(bytes, 'little')

    base = msg.base
    keys = [bytes_to_n(i) for i in msg.keys]
    public_key = paillier.PaillierPublicKey(keys[0])
    private_key = paillier.PaillierPrivateKey(public_key, keys[1], keys[2])
    hists = msg.hists
    args = (base, public_key, private_key, hists)
    return _decrypt_histogram_helper(args)


def _follower_server(msg):
    def normal_to_array(msg):
        array = np.frombuffer(msg.values, dtype=np.dtype(msg.dtype))
        array = np.reshape(array, newshape=msg.shape)
        return array

    def paillier_to_arr(msg):
        arr = np.array(_from_ciphertext(pulic_key, msg.values))
        arr = np.reshape(arr, newshape=msg.shape)
        return arr

    # 得到key
    pulic_key = paillier.PaillierPublicKey(
        int.from_bytes(msg.public_key, 'little'))
    # values 需要特殊处理
    values = paillier_to_arr(msg.values)

    base = msg.base
    binned_features = normal_to_array(msg.binned_features)
    thresholds = msg.thresholds
    zero = pulic_key.encrypt(0, precision=PRECISION)
    args = [base, values, binned_features, thresholds, zero]
    return _compute_histogram_helper(args)


def _follower_reply(hists):
    def ndarrattomsg(array, msg):
        msg.shape.extend(list(array.shape))
        msg.values.extend(_encode_encrypted_numbers(array.flatten()))

    msg = tree_model_pb2.histogram_follower()
    for array in hists:
        msg_arr = msg.hists.add()
        ndarrattomsg(array, msg_arr)
    return msg


def _leader_encrypt_numbers_server(msg):
    public_key = paillier.PaillierPublicKey(
        int.from_bytes(msg.public_key, 'little'))
    numbers = _encrypt_numbers(public_key, msg.numbers)
    return numbers


class HistsServer(tree_model_pb2_grpc.HistsServiceServicer):
    def ComputeHists_leader(self, request, context):
        hists = _leader_compute_histogram_server(request)
        return _leader_reply(hists)

    def ComputeHists_follower(self, request, context):
        hists = _follower_server(request)
        return _follower_reply(hists)

    def Decrypt_histogram(self, request, context):
        hists = _leader_decrypt_histogram_server(request)
        return _leader_reply(hists)

    def Encrypt_numbers(self, request, context):
        msg = tree_model_pb2.EncryptedNumbers()
        msg.ciphertext.extend(_leader_encrypt_numbers_server(request))
        return msg


def sever_service(args):
    addr, timeout = args.address, args.timeout
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10),
                         options=[("grpc.max_send_message_length", MAX_MESSAGE_LENGTH),
                                  ("grpc.max_receive_message_length", MAX_MESSAGE_LENGTH)])
    tree_model_pb2_grpc.add_HistsServiceServicer_to_server(HistsServer(), server)
    server.add_insecure_port(addr)
    server.start()
    server.wait_for_termination(timeout=timeout)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='FedLearner Parameter Server.')
    parser.add_argument('--address', type=str,
                        help='Listen address of the parameter server, ' \
                             'with format [IP]:[PORT],' \
                             'split by ,')
    parser.add_argument('--timeout', type=int,
                        default=None,
                        help='An optional float-valued number of seconds ' \
                             'after which the wait should cease.' \
                             'Set this number as possible')
    args = parser.parse_args()
    sever_service(args)
