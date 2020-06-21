const DEFAULT_SERVER_CONFIG = {
  SERVER_CIPHER: 'leader',
  SERVER_DECIPHER: 'follower',
  K8S_HOST: '127.0.0.1',
  K8S_PORT: 8000,
  API_VERSION: 'fedlearner.k8s.io/v1alpha1',
  KIND: 'FLApp',
  NAMESPACE: 'default',
};

module.exports = {
  DEFAULT_SERVER_CONFIG,
};
