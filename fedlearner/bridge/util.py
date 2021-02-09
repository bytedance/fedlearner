# -*- coding: utf-8 -*-

import fedlearner.bridge.const as const

maxint = 2**32-1

def _method_encode(s):
    if isinstance(s, bytes):
        return s
    else:
        return s.encode('utf8')

def _method_decode(b):
    if isinstance(b, bytes):
        return b.decode('utf-8', 'replace')
    return b

def _abridge_metadata(self, metadata):
    identifier = None
    peer_identifier = None
    token = None
    method = None
    #abridged_metadata = list()
    for pair in metadata:
        if pair[0] == const._grpc_metadata_bridge_id:
            identifier = pair[1]
        elif pair[0] == const._grpc_metadata_bridge_peer_id:
            peer_identifier = pair[1]
        elif pair[0] == const._grpc_metadata_bridge_token:
            token = pair[1]
        elif pair[0] == const._grpc_metadata_bridge_method:
            method = _method_decode(pair[1])
        #else:
            #abridged_metadata.append(pair)

    return identifier, peer_identifier, token, method
