/**
 * Kubernetes Client
 */

const ky = require('ky-universal');

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
    this.client = ky.create({ prefixUrl });
  }

  async getNamespaces() {
    return this.client.get('namespaces').json();
  }

  async getFLAppsByNamespace(namespace) {
    return this.client.get(`namespaces/${namespace}/fedlearner/v1alpha1/flapps`).json();
  }

  async getFLApp(namespace, name) {
    return this.client.get(`namespaces/${namespace}/fedlearner/v1alpha1/flapps/${name}`).json();
  }

  async getFLAppPods(namespace, name) {
    return this.client.get(`namespaces/${namespace}/fedlearner/v1alpha1/flapps/${name}/pods`).json();
  }

  async createFLApp(namespace, fl_app) {
    return this.client.post(`namespaces/${namespace}/fedlearner/v1alpha1/flapps`, {
      json: fl_app
    }).json();
  }

  async deleteFLApp(namespace, name) {
    return this.client.delete(`namespaces/${namespace}/fedlearner/v1alpha1/flapps/${name}`).json();
  }

}

module.exports = KubernetesClient;
