import etcd3
from fedlearner.common.mysql_client import DBClient
from fedlearner.data_join.common import get_kvstore_config

database, addr, username, password, base_dir = \
    get_kvstore_config('mysql')
MySQL_client = DBClient(database, addr, username, password, base_dir)
database, addr, username, password, base_dir = \
    get_kvstore_config('etcd')
(host, port) = addr.split(':')
options = [('grpc.max_send_message_length', 2**31-1),
    ('grpc.max_receive_message_length', 2**31-1)]
clnt = etcd3.client(host=host, port=port,
    grpc_options=options)
for (data, key) in clnt.get_prefix('/', sort_order='ascend'):
    if not isinstance(key.key, str):
        key = key.key.decoder()
    if not isinstance(data, str):
        data = data.decoder()
    MySQL_client.set_data(key, data)


