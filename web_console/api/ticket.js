const router = require('@koa/router')();
const { Op } = require('sequelize');
const SessionMiddleware = require('../middlewares/session');
const { Ticket } = require('../models');

router.get('/api/v1/tickets', SessionMiddleware, async (ctx) => {
  const where = {};
  if (ctx.query.federation_id) {
    where.federation_id = { [Op.eq]: +ctx.query.federation_id };
  }
  const data = await Ticket.findAll({ where });
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

module.exports = router;
