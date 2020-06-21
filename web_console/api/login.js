const router = require('@koa/router')();
const { Op } = require('sequelize');
const { User } = require('../models');
const encrypt = require('../utils/encrypt');

router.post('/api/v1/login', async (ctx) => {
  const { username, password } = ctx.request.body;

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

  const user = await User.findOne({
    where: {
      username: { [Op.eq]: username },
    },
  });

  if (!user) {
    ctx.status = 404;
    ctx.body = {
      error: 'User not found',
    };
    return;
  }

  if (user.password !== encrypt(password)) {
    ctx.status = 401;
    ctx.body = {
      error: 'Bad credentials',
    };
    return;
  }

  const data = {
    id: user.id,
    username: user.username,
    name: user.name,
    tel: user.tel,
    is_admin: user.is_admin,
  };
  ctx.session.user = data;
  ctx.session.manuallyCommit();
  ctx.body = { data };
});

module.exports = router;
