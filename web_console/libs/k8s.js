// Kubernetes Client
const got = require('got');

class KubernetesClient {
  constructor(options) {
    // TODO: use HTTPs for production
    if (options.proxy) {
      this.client = got.extend({
        prefixUrl: `${options.proxy}/api/v1/`,
        responseType: 'json',
      });
    }
  }

  async getNamespaces() {
    const { body } = await this.client.get('namespaces');
    return body;
  }

  async getFLAppsByNamespace(namespace) {
    const { body } = await this.client.get(`namespaces/${namespace}/fedlearner/v1alpha1/flapps`);
    return body;
  }

  async getFLApps(namespace, name) {
    const { body } = await this.client.get(`namespaces/${namespace}/fedlearner/v1alpha1/flapps/${name}`);
    return body;
  }

  async getFLApps(namespace, name) {
    const { body } = await this.client.get(`namespaces/${namespace}/fedlearner/v1alpha1/flapps/${name}`);
    return body;
  }

  async getFLAppPods(namespace, name) {
    const { body } = await this.client.get(`/namespaces/${namespace}/fedlearner/v1alpha1/flapps/${name}/pods`);
    return body;
  }

  async createFLApp(namespace, fl_app) {
    const { body } = await this.client.post(`/namespaces/${namespace}/fedlearner/v1alpha1/flapps`, { body: fl_app });
    return body;
  }

  async deleteFLApp(namespace) {
    const { body } = await this.client.delete(`/namespaces/${namespace}/fedlearner/v1alpha1/flapps/${name}`);
    return body;
  }

}

module.exports = KubernetesClient;
