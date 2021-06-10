from fedlearner.data_join.private_set_union.keys.base_keys import BaseKeys
from fedlearner.data_join.private_set_union.keys.dh_keys import DHKeys
from fedlearner.data_join.private_set_union.keys.ecc_keys import ECCKeys


KEYS = {'DH': DHKeys,
        'ECC': ECCKeys}
