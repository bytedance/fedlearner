const Router = require('@koa/router');
const Next = require('next');
const SessionMiddleware = require('./middlewares/session');
const models = require('./models');
const routes = require('./routes');
const server = require('./server');

const env = process.env.NODE_ENV || 'development';
const renderer = Next({
  dev: env === 'development',
});

async function setupNextRoutes() {
  const router = new Router();
  const handle = renderer.getRequestHandler();

  Object.keys(routes).forEach((route) => {
    router.get(route, SessionMiddleware, async (ctx) => {
      await renderer.render(ctx.req, ctx.res, routes[route], ctx.query);
      ctx.respond = false;
    });
  });

  router.all('*', async (ctx) => {
    await handle(ctx.req, ctx.res);
    ctx.respond = false;
  });

  server.use(async (ctx, next) => {
    ctx.res.statusCode = 200;
    await next();
  });

  server.use(router.routes(), router.allowedMethods());
}

function bootstrap() {
  const host = process.env.HOST || '0.0.0.0';
  const port = parseInt(process.env.PORT, 10) || 1989;
  server.listen(port, () => console.log(`> Server is ready on http://${host}:${port}`));
}

renderer.prepare()
  .then(() => models.sequelize.sync())
  .then(() => setupNextRoutes())
  .then(() => bootstrap());
