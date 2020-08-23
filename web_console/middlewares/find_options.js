// Common middleware for Sequelize FindOptions generation

module.exports = async function FindOptionsMiddleware(ctx, next) {
  ctx.findOptions = {};

  if (ctx.headers['x-federation-id']) {
    const federation_id = parseInt(ctx.headers['x-federation-id'], 10);
    if (Number.isNaN(federation_id) || federation_id < 1) {
      ctx.status = 400;
      ctx.body = {
        error: 'Invalid header: X-Federation-Id',
      };
      return;
    }
    ctx.findOptions.where = { federation_id };
  }

  await next();
};
