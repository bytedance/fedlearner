module.exports = async function FederationMiddleware(ctx, next) {
  if (!ctx.session.user.is_admin) {
    ctx.status = 403;
    ctx.body = {
      error: 'Permission denied',
    };
    return;
  }

  await next();
};
