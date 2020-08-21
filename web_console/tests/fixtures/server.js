const fs = require('fs');
const path = require('path');
const router = require('@koa/router')();
const AdminMiddleware = require('../../middlewares/admin');
const SessionMiddleware = require('../../middlewares/session');
const FindOptionsMiddleware = require('../../middlewares/find_options');
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

router.get('/find', FindOptionsMiddleware, async (ctx) => {
  ctx.body = ctx.findOptions;
});

router.get('/favicon.ico', SessionMiddleware, async (ctx) => {
  ctx.set('Content-Type', 'image/x-icon');
  ctx.body = fs.createReadStream(path.resolve(__dirname, '..', '..', 'public', 'favicon.ico'));
});

router.get('/_next/static/test.js', SessionMiddleware, async (ctx) => {
  ctx.set('Content-Type', 'application/javascript; charset=UTF-8');
  ctx.body = '<script>console.log("ok")</script>';
});

server.use(router.routes(), router.allowedMethods());

module.exports = server;
