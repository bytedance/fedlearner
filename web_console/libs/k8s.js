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
    const prefixUrl = `http://${config.K8S_HOST}:${config.K8S_PORT}`;
    this.prefixUrl = prefixUrl;
    this.client = ky.create({ prefixUrl });
  }

  getBaseUrl() {
    return this.prefixUrl;
  }

  async getNamespaces() {
    const response = await this.client.get('namespaces');
    return response.json();
  }

  async getFLAppsByNamespace(namespace) {
    const response = await this.client.get(`namespaces/${namespace}/fedlearner/v1alpha1/flapps`);
    return response.json();
  }

  async getFLApp(namespace, name) {
    const response = await this.client.get(`namespaces/${namespace}/fedlearner/v1alpha1/flapps/${name}`);
    return response.json();
  }

  async getFLAppPods(namespace, name) {
    const response = await this.client.get(`namespaces/${namespace}/fedlearner/v1alpha1/flapps/${name}/pods`);
    return response.json();
  }

  async createFLApp(namespace, fl_app) {
    const response = await this.client.post(`namespaces/${namespace}/fedlearner/v1alpha1/flapps`, {
      json: fl_app
    });
    return response.json();
  }

  async deleteFLApp(namespace, name) {
    const response = await this.client.delete(`namespaces/${namespace}/fedlearner/v1alpha1/flapps/${name}`);
    return response.json();
  }

  async getWebshellSession(namespace, name, container) {
    const response = await this.client.get(`namespaces/${namespace}/pods/${name}/shell/${container}`);
    return response.json();
  }
}

module.exports = new KubernetesClient();
