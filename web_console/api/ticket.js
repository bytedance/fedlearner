const router = require('@koa/router')();
const { Op } = require('sequelize');
const SessionMiddleware = require('../middlewares/session');
const FindOptionsMiddleware = require('../middlewares/find_options');
const { Ticket } = require('../models');
const checkParseJson = require('../utils/check_parse_json');

router.get('/api/v1/tickets', SessionMiddleware, FindOptionsMiddleware, async (ctx) => {
  const data = await Ticket.findAll(ctx.findOptions);
  ctx.body = { data };
});

router.post('/api/v1/tickets', SessionMiddleware, async (ctx) => {
  const {
    name, federation_id, job_type, role, sdk_version,
    expire_time, remark, public_params, private_params,
  } = ctx.request.body;
  const [data, created] = await Ticket.findOrCreate({
    paranoid: false,
    where: {
      name: { [Op.eq]: name },
    },
    defaults: {
      name, federation_id, job_type, role, sdk_version,
      expire_time, remark, public_params, private_params,
      user_id: ctx.session.user.id,
    },
  });

  if (!created) {
    ctx.status = 422;
    ctx.body = {
      error: 'Ticket already exists',
    };
    return;
  }

  ctx.body = { data };
});

router.put('/api/v1/tickets/:id', SessionMiddleware, async (ctx) => {
  const { id } = ctx.params;
  const { body } = ctx.request;

  const ticket = await Ticket.findByPk(id);
  if (!ticket) {
    ctx.status = 404;
    ctx.body = {
      error: 'Ticket not found',
    };
    return;
  }

  const fields = ['job_type', 'role', 'sdk_version', 'expire_time', 'remark', 'public_params', 'private_params'].reduce((total, current) => {
    const value = body[current];
    if (value) {
      total[current] = value;
    }
    return total;
  }, {});

  if (fields.public_params) {
    const [pass] = checkParseJson(JSON.stringify(fields.public_params));
    if (!pass) {
      ctx.status = 400;
      ctx.body = {
        error: 'Invalid field: public_params',
      };
      return;
    }
  }

  if (fields.private_params) {
    const [pass] = checkParseJson(JSON.stringify(fields.private_params));
    if (!pass) {
      ctx.status = 400;
      ctx.body = {
        error: 'Invalid field: private_params',
      };
      return;
    }
  }

  await ticket.update(fields);
  ctx.body = { data: ticket };
});

module.exports = router;
