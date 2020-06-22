const router = require('@koa/router')();
const SessionMiddleware = require('../middlewares/session');
const KubernetesClient = require('../libs/k8s');
const ElasticSearchClient = require('../libs/es');

const getConfig = require('../utils/get_confg');

const config = getConfig({
  NAMESPACE: process.env.NAMESPACE,
});
const namespace = config.NAMESPACE;

const k8s = new KubernetesClient();
const es = new ElasticSearchClient();

router.get('/api/v1/jobs', SessionMiddleware, async (ctx) => {
  const { flapps } = await k8s.getFLAppsByNamespace(namespace);
  ctx.body = { data: flapps };
});

router.get('/api/v1/job/:name', SessionMiddleware, async (ctx) => {
  const { name } = ctx.params;
  const { flapp } = await k8s.getFLApp(namespace, name);
  ctx.body = { data: flapp };
});

router.get('/api/v1/job/:name/pods', SessionMiddleware, async (ctx) => {
  const { name } = ctx.params;
  const { pods } = await k8s.getFLAppPods(namespace, name);
  ctx.body = { data: pods };
});

router.get('/api/v1/job/pod/:name/:container', SessionMiddleware, async (ctx) => {
  const { name, container } = ctx.params;
  const base = k8s.getBaseUrl();
  const { id } = await k8s.getWebshellSession(namespace, name, container);
  ctx.body = { data: { id, base } };
});

router.get('/api/v1/job/pod/:name/logs/:time', SessionMiddleware, async (ctx) => {
  const { name, time } = ctx.params;
  const logs = await es.queryLog('filebeat-*', '', name, time, Date.now());
  ctx.body = { data: logs };
});

router.post('/api/v1/job/create', SessionMiddleware, async (ctx) => {
  const { fl_app } = ctx.request.body;
  if (!fl_app) {
    ctx.status = 400;
    ctx.body = {
      error: 'Missing field: fl_app',
    };
    return;
  }
  const res = await k8s.createFLApp(namespace, fl_app);
  ctx.body = { data: res };
});

router.delete('/api/v1/job/:name', SessionMiddleware, async (ctx) => {
  // TODO: just owner can delete
  const { name } = ctx.params;
  const res = await k8s.deleteFLApp(namespace, name);
  ctx.body = { data: res };
});

module.exports = router;
