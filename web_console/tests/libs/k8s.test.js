const assert = require('assert');
const path = require('path');
const { loadYaml } = require('../../utils/yaml');
const { readFileSync } = require('../../utils');
const KubernetesClient = require('../../libs/k8s');

const testYaml = readFileSync(
  path.resolve(__dirname, '..', 'fixtures', 'test.yaml'),
  { encoding: 'utf-8' },
);

let k8s;

describe('Kubernetes Client', () => {
  before(() => {
    k8s = new KubernetesClient();
  });

  describe('getNamespaces', () => {
    it('should get all namespaces', async () => {
      const { namespaces } = await k8s.getNamespaces();
      assert.ok(namespaces.items.find((x) => x.metadata.name === 'default'));
    });
  });

  describe('createFLApp', () => {
    it('should throw for none namespace, job_body', () => {
      assert.rejects(k8s.createFLApp());
    });

    it('should create default job for default', async () => {
      assert.doesNotReject(k8s.createFLApp('default', loadYaml(testYaml)));
    });
  });


  describe('getFLAppsByNamespace', () => {
    it('should throw for none namespace', () => {
      assert.rejects(k8s.getFLAppsByNamespace());
    });

    it('should get all pods for default', async () => {
      const { flapps } = await k8s.getFLAppsByNamespace('default');
      assert.ok(Array.isArray(flapps.items));
    });
  });

  describe('getFLApp', () => {
    it('should throw for none namespace, name', () => {
      assert.rejects(k8s.getFLApp());
    });

    it('should get all pods for default', async () => {
      assert.doesNotReject(k8s.getFLApp('default', 'normal'));
    });
  });

  describe('getFLAppPods', () => {
    it('should throw for none namespace, name', () => {
      assert.rejects(k8s.getFLAppPods());
    });

    it('should get all pods for default', async () => {
      const { pods } = await k8s.getFLAppPods('default', 'normal');
      assert.ok(Array.isArray(pods.items));
    });
  });

  describe('deleteFLApp', () => {
    it('should throw for none namespace, name', () => {
      assert.rejects(k8s.deleteFLApp());
    });

    it('should delete test application for default', async () => {
      assert.doesNotReject(k8s.deleteFLApp('default', 'normal'))
    });
  });
});
