// Kubernetes Client
const got = require('got');

class KubernetesClient {
  constructor(options) {
    // TODO: use HTTPs for production
    if (options.proxy) {
      this.client = got.extend({
        prefixUrl: `${options.proxy}/api/v1`,
        responseType: 'json',
      });
    }
  }

  // TODO: apply filters
  async getNamespaces() {
    const { body } = await this.client.get('namespaces');
    return body;
  }

  // TODO: apply filters
  async getPods() {
    const { body } = await this.client.get('pods');
    return body;
  }
}

module.exports = KubernetesClient;
