module.exports = async function SessionMiddleware(ctx, next) {
  const isStaticPath = ctx.path.startsWith('/_next') || ctx.path === '/favicon.ico';

  if ((ctx.session.isNew || !ctx.session.user) && ctx.path !== '/login' && !isStaticPath) {
    // redirect to login page if not logged in
    ctx.redirect('/login');
    return;
  }

  if (ctx.session.user && ctx.path === '/login') {
    // redirect to homepage if logged in and accessing login page
    ctx.redirect('/');
    return;
  }

  if (ctx.session.user && !ctx.session.user.is_admin && ctx.path === '/admin') {
    // redirect to 404 page if user is not admin
    ctx.redirect('/404');
    return;
  }

  await next();
};
