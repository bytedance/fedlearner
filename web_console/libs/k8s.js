/**
 * Kubernetes Client
 */

const ky = require('ky-universal');

const getConfig = require('../utils/get_confg');
const parseStream = require('../utils/parse_stream');

const config = getConfig({
  K8S_HOST: process.env.K8S_HOST,
  K8S_PORT: process.env.K8S_PORT,
});

const parseErrorResponse = async (e) => {
  if (e && e.response && e.response.body) {
    const body = await parseStream(e.response.body);
    if (body && body.error) {
      const error = new Error(body.error);
      error.status = e.response.status;
      throw error;
    }
  }
  throw e;
}

class KubernetesClient {
  constructor() {
    const prefixUrl = `http://${config.K8S_HOST}:${config.K8S_PORT}`;
    this.prefixUrl = prefixUrl;
    this.client = ky.create({
      prefixUrl,
    });
  }

  getBaseUrl() {
    return this.prefixUrl;
  }

  async getNamespaces() {
    const response = await this.client.get('namespaces').catch(parseErrorResponse);
    return response.json();
  }

  async getFLAppsByNamespace(namespace) {
    const response = await this.client.get(`namespaces/${namespace}/fedlearner/v1alpha1/flapps`)
      .catch(parseErrorResponse);
    return response.json();
  }

  async getFLApp(namespace, name) {
    const response = await this.client.get(`namespaces/${namespace}/fedlearner/v1alpha1/flapps/${name}`)
      .catch(parseErrorResponse);
    return response.json();
  }

  async getFLAppPods(namespace, name) {
    const response = await this.client.get(`namespaces/${namespace}/fedlearner/v1alpha1/flapps/${name}/pods`)
      .catch(parseErrorResponse);
    return response.json();
  }

  async createFLApp(namespace, fl_app) {
    const response = await this.client.post(`namespaces/${namespace}/fedlearner/v1alpha1/flapps`, {
      json: fl_app
    }).catch(parseErrorResponse);
    return response.json();
  }

  async deleteFLApp(namespace, name) {
    const response = await this.client.delete(`namespaces/${namespace}/fedlearner/v1alpha1/flapps/${name}`)
      .catch(parseErrorResponse);
    return response.json();
  }

  async getWebshellSession(namespace, name, container) {
    const response = await this.client.get(`namespaces/${namespace}/pods/${name}/shell/${container}`)
      .catch(parseErrorResponse);
    return response.json();
  }
}

module.exports = new KubernetesClient();
