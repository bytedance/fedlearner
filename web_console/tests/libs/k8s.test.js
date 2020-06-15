const assert = require('assert');
const { spawn } = require('child_process');
const getPort = require('get-port');
const KubernetesClient = require('../../libs/k8s');

let k8sProxy;
let port;
let k8s;

describe('Kubernetes Client', () => {
  // TODO: setup FL cluster here
  before(async () => {
    port = await getPort({ port: 8080 });
    k8sProxy = spawn('kubectl', ['proxy', `--port=${port}`]);
    k8s = new KubernetesClient({ proxy: `http://127.0.0.1:${port}` });
  });

  after(() => {
    k8sProxy.kill('SIGHUP');
  });

  describe('getNamespaces', () => {
    it('should get all namespaces', async () => {
      const { items } = await k8s.getNamespaces();
      assert.ok(items.find(x => x.metadata.name === 'default'));
    });
  });

  describe('getPods', () => {
    it('should get all pods', async () => {
      const { items } = await k8s.getPods();
      assert.ok(items.find(x => x.status.phase === 'Running'));
    });
  });
});
