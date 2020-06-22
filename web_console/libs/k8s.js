/**
 * Kubernetes Client
 */

const ky = require('ky-universal');

const getConfig = require('../utils/get_confg');

const config = getConfig({
  K8S_HOST: process.env.K8S_HOST,
  K8S_PORT: process.env.K8S_PORT,
});

class KubernetesClient {
  constructor() {
    // TODO: use HTTPs for production
    const prefixUrl = `http://${config.K8S_HOST}:${config.K8S_PORT}`;
    this.prefixUrl = prefixUrl;
    this.client = ky.create({ prefixUrl });
  }

  getBaseUrl() {
    return this.prefixUrl;
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

  async getWebshellSession(namespace, name, container) {
    return this.client.get(`namespaces/${namespace}/pods/${name}/shell/${container}`).json();
  }
}

module.exports = KubernetesClient;
