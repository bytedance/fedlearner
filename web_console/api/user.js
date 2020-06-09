const router = require('@koa/router')();
const { Op } = require('sequelize');
const SessionMiddleware = require('../middlewares/session');
const { User } = require('../models');
const { ok, error } = require('../libs/response');

router.get('/users', async (ctx) => {
  const { limit = 20, offset = 0 } = ctx.query;
  const order = [['id', 'DESC']];
  const data = await User.findAll({ limit, offset, order });
  ctx.body = ok(data);
});

router.post('/users', SessionMiddleware, async (ctx) => {
  // TODO: implement common request body validation middleware
  if (!ctx.request.body) {
    ctx.body = error('Illegal request body');
    return;
  }

  const { username, password, name, tel } = ctx.request.body;
  const data = await User.create({
    username,
    password,
    name,
    tel,
  });
  ctx.body = ok(data, 'Create user successfully.');
});

router.get('/users/:id', async (ctx) => {
  const data = await User.findById(ctx.params.id);
  ctx.body = ok(data);
});

router.put('/users/:id', async (ctx) => {
  const { id } = ctx.params;
  const { body } = ctx.request;
  const fields = ['password', 'name', 'tel'].reduce((total, current) => {
    const value = body[current];
    if (value) {
      total[current] = value;
    }
    return total;
  }, {});
  const data = await User.update(fields, {
    where: {
      id: { [Op.eq]: id },
    },
  });
  ctx.body = ok(data, 'Update user successfully.');
});

// TODO
router.delete('/queries/:id', async (ctx) => {
  ctx.status = 501;
});

module.exports = router;
