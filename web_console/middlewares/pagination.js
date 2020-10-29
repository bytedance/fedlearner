module.exports = async function PaginationMiddleware(ctx, next) {
  const { offset, limit } = ctx.query;
  ctx.pagination = {};

  if (offset) {
    const res = parseInt(offset, 10);
    if (Number.isNaN(res) || res < 0) {
      ctx.status = 400;
      ctx.body = {
        error: 'Invalid field: offset',
      };
      return;
    }
    ctx.pagination.offset = res;
  }

  if (limit) {
    const res = parseInt(limit, 10);
    if (Number.isNaN(res) || res < 0) {
      ctx.status = 400;
      ctx.body = {
        error: 'Invalid field: limit',
      };
      return;
    }
    ctx.pagination.limit = res;
  }

  await next();
};
