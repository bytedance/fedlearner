const router = require('@koa/router')();
const SessionMiddleware = require('../middlewares/session');
const { Federation } = require('../models');
const FederationClient = require('../rpc/client');

router.get('/api/v1/federations', SessionMiddleware, async (ctx) => {
  const data = await Federation.findAll();
  ctx.body = { data };
});

router.get('/api/v1/federations/:id/tickets', SessionMiddleware, async (ctx) => {
  const federation = await Federation.findByPk(ctx.params.id);
  if (!federation) {
    ctx.status = 404;
    ctx.body = {
      error: 'Federation not found',
    };
    return;
  }
  const client = new FederationClient(federation);
  const { data } = await client.getTickets();
  ctx.body = { data };
});

module.exports = router;
