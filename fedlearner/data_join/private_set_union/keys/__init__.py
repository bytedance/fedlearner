import fedlearner.common.private_set_union_pb2 as psu_pb
from fedlearner.data_join.private_set_union.keys.base_keys import BaseKeys
from fedlearner.data_join.private_set_union.keys.dh_keys import DHKeys
from fedlearner.data_join.private_set_union.keys.ecc_keys import ECCKeys


def get_keys(key_info: psu_pb.KeyInfo):
    for cls in BaseKeys.__subclasses__():
        if cls.key_type() == key_info.type:
            return cls(key_info)
    raise ValueError(f'Key type {key_info.type} not registered.')
