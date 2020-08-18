const router = require('@koa/router')();
const { Op } = require('sequelize');
const AdminMiddleware = require('../middlewares/admin');
const SessionMiddleware = require('../middlewares/session');
const { Federation } = require('../models');
const FederationClient = require('../rpc/client');
const checkParseJson = require('../utils/check_parse_json');

router.get('/api/v1/federations', SessionMiddleware, async (ctx) => {
  const data = await Federation.findAll();
  ctx.body = { data };
});

router.post('/api/v1/federations', SessionMiddleware, AdminMiddleware, async (ctx) => {
  const { name, trademark, email, tel, avatar, k8s_settings } = ctx.request.body;

  if (!name) {
    ctx.status = 400;
    ctx.body = {
      error: 'Missing field: name',
    };
    return;
  }

  if (!k8s_settings) {
    ctx.status = 400;
    ctx.body = {
      error: 'Missing field: k8s_settings',
    };
    return;
  }

  const [pass] = checkParseJson(JSON.stringify(k8s_settings));
  if (!pass) {
    ctx.status = 400;
    ctx.body = {
      error: 'Invalid field: k8s_settings',
    };
    return;
  }

  const [data, created] = await Federation.findOrCreate({
    paranoid: false,
    where: {
      name: { [Op.eq]: name },
    },
    defaults: {
      name, trademark, email, tel, avatar, k8s_settings,
    },
  });

  if (!created) {
    ctx.status = 422;
    ctx.body = {
      error: 'Federation already exists',
    };
    return;
  }

  ctx.body = { data };
});

router.put('/api/v1/federations/:id', SessionMiddleware, AdminMiddleware, async (ctx) => {
  const { id } = ctx.params;
  const { body } = ctx.request;

  const federation = await Federation.findByPk(id);
  if (!federation) {
    ctx.status = 404;
    ctx.body = {
      error: 'Federation not found',
    };
    return;
  }

  const fields = ['trademark', 'email', 'tel', 'avatar', 'k8s_settings'].reduce((total, current) => {
    const value = body[current];
    if (value) {
      total[current] = value;
    }
    return total;
  }, {});

  if (fields.k8s_settings) {
    const [pass] = checkParseJson(JSON.stringify(fields.k8s_settings));
    if (!pass) {
      ctx.status = 400;
      ctx.body = {
        error: 'Invalid field: k8s_settings',
      };
      return;
    }
  }

  await federation.update(fields);
  ctx.body = { data: federation };
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
  const { job_type = '', role = '' } = ctx.query;
  const client = new FederationClient(federation);
  const { data } = await client.getTickets({ job_type, role });
  ctx.body = { data };
});

module.exports = router;
