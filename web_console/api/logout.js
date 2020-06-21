const router = require('@koa/router')();

router.post('/api/v1/logout', async (ctx) => {
  if (ctx.session.isNew || !ctx.session.user) {
    ctx.status = 404;
    ctx.body = {
      error: 'Session not found',
    };
  } else {
    ctx.session = null;
    ctx.cookies.set('user.session', null);
    ctx.cookies.set('user.session.sig', null);
    ctx.body = {
      message: 'Logout successfully',
    };
  }
});

module.exports = router;
