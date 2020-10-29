/**
 * Common proxy of Kubernetes Deployment API
 */

const router = require('@koa/router')();
const SessionMiddleware = require('../middlewares/session');
const k8s = require('../libs/k8s');

router.get('/api/v1/deployments', SessionMiddleware, async (ctx) => {
  const res = await k8s.listDeployments();
  ctx.body = { data: res.deployments.items };
});

router.get('/api/v1/deployments/:name', SessionMiddleware, async (ctx) => {
  const { deployment: data } = await k8s.getDeployment(ctx.params.name);
  ctx.body = { data };
});

router.put('/api/v1/deployments/:name', SessionMiddleware, async (ctx) => {
  const { deployment: data } = await k8s.updateDeployment(ctx.request.body);
  ctx.body = { data };
});

module.exports = router;
