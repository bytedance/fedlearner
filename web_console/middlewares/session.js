// TODO: add validation
module.exports = async function SessionMiddleware(ctx, next) {
  await next();

  // const session = ctx.cookies.get('user.session');

  // if (ctx.session.isNew || !session) {
  //   // user has not logged in
  //   ctx.redirect('/login');
  //   return;
  // }
  // await next();
};
