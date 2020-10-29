const router = require('@koa/router')();
const { Op } = require('sequelize');
const SessionMiddleware = require('../middlewares/session');
const AdminMiddleware = require('../middlewares/admin');
const { User } = require('../models');
const encrypt = require('../utils/encrypt');

router.get('/api/v1/user', SessionMiddleware, async (ctx) => {
  ctx.body = { data: ctx.session.user };
});

router.put('/api/v1/user', SessionMiddleware, async (ctx) => {
  const { body } = ctx.request;

  const user = await User.findByPk(ctx.session.user.id);
  if (!user) {
    ctx.status = 404;
    ctx.body = {
      error: 'User not found',
    };
    return;
  }

  const fields = ['password', 'name', 'tel', 'email', 'avatar', 'is_admin'].reduce((total, current) => {
    const value = body[current];
    if (value) {
      total[current] = current === 'password' ? encrypt(value) : value;
    }
    return total;
  }, {});

  await user.update(fields);
  ctx.session.user = {
    id: user.id,
    username: user.username,
    name: user.name,
    tel: user.tel,
    is_admin: user.is_admin,
  };
  ctx.session.manuallyCommit();
  ctx.body = { data: user };
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
      username, name, email, tel, is_admin,
      password: encrypt(password),
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

router.put('/api/v1/users/:id', SessionMiddleware, AdminMiddleware, async (ctx) => {
  const { id } = ctx.params;
  const { body } = ctx.request;

  const user = await User.findByPk(id);
  if (!user) {
    ctx.status = 404;
    ctx.body = {
      error: 'User not found',
    };
    return;
  }

  const fields = ['password', 'name', 'tel', 'email', 'avatar', 'is_admin'].reduce((total, current) => {
    const value = body[current];
    if (value) {
      total[current] = current === 'password' ? encrypt(value) : value;
    }
    return total;
  }, {});

  await user.update(fields);

  if (user.id === ctx.session.user.id) {
    ctx.session.user = {
      id: user.id,
      username: user.username,
      name: user.name,
      tel: user.tel,
      is_admin: user.is_admin,
    };
    ctx.session.manuallyCommit();
  }

  ctx.body = { data: user };
});

router.delete('/api/v1/users/:id', SessionMiddleware, AdminMiddleware, async (ctx) => {
  const data = await User.findByPk(ctx.params.id);

  if (!data) {
    ctx.status = 404;
    ctx.body = {
      error: 'User not found',
    };
    return;
  }

  await data.destroy({ force: true });
  ctx.body = { data };
});

module.exports = router;
