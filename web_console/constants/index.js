const path = require('path');

const DEFAULT_SERVER_CONFIG = {
  SERVER_CIPHER: 'leader',
  SERVER_DECIPHER: 'follower',
  K8S_HOST: '127.0.0.1',
  K8S_PORT: 8000,
  API_VERSION: 'fedlearner.k8s.io/v1alpha1',
  KIND: 'FLApp',
  NAMESPACE: 'default',
  ES_HOST: 'fedlearner-stack-elasticsearch-client',
  ES_PORT: 9200,
  GRPC_HOST: 'localhost',
  GRPC_PORT: 50051,
  GRPC_AUTHORITY: 'FL',
  GRPC_CA: path.resolve(__dirname, 'tests', 'fixtures', 'ca.pem'),
  GRPC_KEY: path.resolve(__dirname, 'tests', 'fixtures', 'server.key'),
  GRPC_CERT: path.resolve(__dirname, 'tests', 'fixtures', 'server.pem'),
};

module.exports = {
  DEFAULT_SERVER_CONFIG,
};
