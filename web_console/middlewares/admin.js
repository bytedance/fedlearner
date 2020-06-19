module.exports = async function AdminMiddleware(ctx, next) {
  if (!ctx.session.user.is_admin) {
    ctx.status = 403;
    ctx.body = {
      error: 'Permission denied',
    };
    return;
  }

  await next();
};
