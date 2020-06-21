const path = require('path');
const Koa = require('koa');
const bodyParser = require('koa-bodyparser');
const json = require('koa-json');
const onerror = require('koa-onerror');
const logger = require('koa-pino-logger');
const session = require('koa-session');
const { readdirSync } = require('./utils');

let config;
try {
  config = require('./server.config');
} catch (err) {
  config = require('./constants').DEFAULT_SERVER_CONFIG;
}

const isTest = process.env.NODE_ENV === 'test';
const server = new Koa();
server.silent = true;
server.keys = [
  process.env.SERVER_CIPHER || config.SERVER_CIPHER,
  process.env.SERVER_DECIPHER || config.SERVER_DECIPHER,
];

server.use(session({
  key: 'user.session',
  maxAge: 2592000000,
  autoCommit: false,
  rolling: true,
  renew: true,
  secure: false,
}, server));
server.use(bodyParser());
server.use(json());

if (!isTest) {
  server.use(logger());
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
      ctx.body = { error: err.message };
    },
  });
}


const apiDir = path.join(__dirname, 'api');
readdirSync(apiDir)
  .filter((file) => !file.startsWith('.') && path.extname(file) === '.js')
  .forEach((file) => {
    const router = require(path.join(apiDir, file));
    server.use(router.routes(), router.allowedMethods());
  });

module.exports = server;
