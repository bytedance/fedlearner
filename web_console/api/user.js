const router = require('@koa/router')();
const { Op } = require('sequelize');
const SessionMiddleware = require('../middlewares/session');
const AdminMiddleware = require('../middlewares/admin');
const { User } = require('../models');

router.get('/api/v1/user', SessionMiddleware, async (ctx) => {
  ctx.body = { data: ctx.session.user };
});

router.get('/api/v1/users', SessionMiddleware, AdminMiddleware, async (ctx) => {
  const data = await User.findAll({ paranoid: false });
  ctx.body = { data };
});

router.post('/api/v1/users', SessionMiddleware, AdminMiddleware, async (ctx) => {
  const { username, password, name, email, tel, is_admin } = ctx.request.body;

  if (!username) {
    ctx.status = 400;
    ctx.body = {
      error: 'Missing field: username',
    };
    return;
  }

  if (!password) {
    ctx.status = 400;
    ctx.body = {
      error: 'Missing field: password',
    };
    return;
  }

  const [data, created] = await User.findOrCreate({
    paranoid: false,
    where: {
      username: { [Op.eq]: username },
    },
    defaults: {
      username, password, name, email, tel, is_admin,
    },
  });

  if (!created) {
    ctx.status = 422;
    ctx.body = {
      error: 'User already exists',
    };
    return;
  }

  ctx.body = { data };
});

// TODO
// router.put('/api/v1/users/:id', async (ctx) => {
//   const { id } = ctx.params;
//   const { body } = ctx.request;
//   const fields = ['password', 'name', 'tel'].reduce((total, current) => {
//     const value = body[current];
//     if (value) {
//       total[current] = value;
//     }
//     return total;
//   }, {});
//   const data = await User.update(fields, {
//     where: {
//       id: { [Op.eq]: id },
//     },
//   });
//   ctx.body = { data };
// });

router.delete('/api/v1/users/:id', SessionMiddleware, AdminMiddleware, async (ctx) => {
  const data = await User.findByPk(ctx.params.id);

  if (!data) {
    ctx.status = 404;
    ctx.body = {
      error: 'User not found',
    };
    return;
  }

  await data.destroy();
  ctx.body = { data };
});

module.exports = router;
