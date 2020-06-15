// Kubernetes Client
const got = require('got');

let config;
try {
  config = require('../server.config');
} catch (err) {
  config = require('../constants').DEFAULT_SERVER_CONFIG;
}

class KubernetesClient {
  constructor() {
    // TODO: use HTTPs for production
    const prefixUrl = `http://${process.env.K8S_HOST || config.K8S_HOST}:${process.env.K8S_PORT || config.K8S_PORT}`;
    this.client = got.extend({
      prefixUrl,
      responseType: 'json',
    });
  }

  async getNamespaces() {
    const { body } = await this.client.get('namespaces');
    return body;
  }

  async getFLAppsByNamespace(namespace) {
    const { body } = await this.client.get(`namespaces/${namespace}/fedlearner/v1alpha1/flapps`);
    return body;
  }
}

module.exports = KubernetesClient;
