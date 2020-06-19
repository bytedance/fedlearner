const router = require('@koa/router')();
const AdminMiddleware = require('../../middlewares/admin');
const SessionMiddleware = require('../../middlewares/session');
const server = require('../../server');

router.get('/', SessionMiddleware, async (ctx) => {
  ctx.body = 'Hello World';
});

router.get('/login', SessionMiddleware, async (ctx) => {
  ctx.body = 'login';
});

router.get('/admin', SessionMiddleware, async (ctx) => {
  ctx.body = 'admin';
});

router.post('/api/v1/admin/ping', SessionMiddleware, AdminMiddleware, async (ctx) => {
  ctx.body = {
    message: 'pong',
  };
});

server.use(router.routes(), router.allowedMethods());

module.exports = server;
