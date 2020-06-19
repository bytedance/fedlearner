const router = require('@koa/router')();
const SessionMiddleware = require('../middlewares/session');
const { Federation } = require('../models');

router.get('/api/v1/federations', SessionMiddleware, async (ctx) => {
  const data = await Federation.findAll();
  ctx.body = { data };
});

module.exports = router;
