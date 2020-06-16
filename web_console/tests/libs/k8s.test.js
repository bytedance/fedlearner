const assert = require('assert');
const KubernetesClient = require('../../libs/k8s');

let k8s;

describe('Kubernetes Client', () => {
  before(() => {
    k8s = new KubernetesClient();
  });

  describe('getNamespaces', () => {
    it('should get all namespaces', async () => {
      const { namespaces } = await k8s.getNamespaces();
      assert.ok(namespaces.items.find((x) => x.metadata.name === 'fedlearner-system'));
    });
  });

  describe('getFLAppsByNamespace', () => {
    it('should throw for none namespace', () => {
      assert.rejects(k8s.getFLAppsByNamespace());
    });

    it('should get all pods for fedlearner-system', async () => {
      const { flapps } = await k8s.getFLAppsByNamespace('fedlearner-system');
      assert.ok(Array.isArray(flapps.items));
    });
  });
});
