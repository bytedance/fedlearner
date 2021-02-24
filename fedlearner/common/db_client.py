import os

from fedlearner.common.etcd_client import EtcdClient
from fedlearner.common.dfs_client import DFSClient
from fedlearner.common.mysql_client import MySQLClient


def get_kvstore_config(kvstore_type):
    if kvstore_type == 'mysql':
        database = os.environ.get('DB_DATABASE', 'fedlearner')
        host = os.environ.get('DB_HOST', '127.0.0.1')
        port = os.environ.get('DB_PORT', '3306')
        addr = host + ':' + port
        username = os.environ.get('DB_USERNAME', 'fedlearner')
        password = os.environ.get('DB_PASSWORD', 'fedlearner')
        base_dir = os.environ.get('DB_BASE_DIR', 'fedlearner')
        return database, addr, username, password, base_dir
    name = os.environ.get('ETCD_NAME', 'fedlearner')
    addr = os.environ.get('ETCD_ADDR', 'localhost:2379')
    base_dir = os.environ.get('ETCD_BASE_DIR', 'fedlearner')
    return name, addr, None, None, base_dir


class DBClient(object):
    def __init__(self, kvstore_type, use_mock_etcd=False):
        if kvstore_type == 'dfs':
            base_dir = os.path.join(
                os.environ.get('STORAGE_ROOT_PATH', '/fedlearner'),
                'metadata')
            self._client = DFSClient(base_dir)
        else:
            database, addr, username, password, base_dir = \
                get_kvstore_config(kvstore_type)
            self._client = EtcdClient(database, addr, base_dir,
                                      use_mock_etcd)
            if username is not None and not use_mock_etcd:
                self._client = MySQLClient(database, addr, username,
                                           password, base_dir)

    def __getattr__(self, attr):
        return getattr(self._client, attr)


