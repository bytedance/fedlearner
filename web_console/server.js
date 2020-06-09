const path = require('path');
const Koa = require('koa');
const bodyParser = require('koa-bodyparser');
const json = require('koa-json');
const onerror = require('koa-onerror');
const logger = require('koa-pino-logger');
const session = require('koa-session');
const { readdirSync } = require('./utils');

const server = new Koa();
server.silent = true;

onerror(server, {
  accepts() {
    if (this.get('accept').includes('json')) return 'json';
    return 'html';
  },
  html(err, ctx) {
    ctx.log.error(err);
    ctx.redirect('/500');
  },
  json(err, ctx) {
    ctx.log.error(err);
    ctx.body = { message: err.message };
  },
});

server.use(session({
  key: 'user.session',
  maxAge: 2592000000,
  autoCommit: false,
  renew: true,
  secure: false,
}, server));
server.use(bodyParser());
server.use(json());
server.use(logger());

const apiDir = path.join(__dirname, 'api');
readdirSync(apiDir)
  .filter((file) => !file.startsWith('.') && path.extname(file) === '.js')
  .forEach((file) => {
    const router = require(path.join(apiDir, file));
    server.use(router.routes(), router.allowedMethods());
  });

module.exports = server;
