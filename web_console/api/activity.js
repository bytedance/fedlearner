const router = require('@koa/router')();
const SessionMiddleware = require('../middlewares/session');
const PaginationMiddleware = require('../middlewares/pagination');
const docker = require('../libs/docker');

/**
 * Convert images from Docker Hub to releases
 *
 * @param {Array<Object>} images - ref: https://hub.docker.com/v2/repositories/fedlearner/fedlearner-web-console/tags/
 * @return {Array<Object>} - checkout `tests/fixtures/activity.js` for schema detail
 */
function mapImageToRelease(images) {
  return images.map(x => ({
    id: x.images[0].digest,
    type: 'release',
    creator: 'bytedance',
    created_at: x.tag_last_pushed,
    ctx: {
      docker: x,
      // fake github data
      github: {
        html_url: `https://github.com/bytedance/fedlearner/releases/tag/${x.name}`,
        tag_name: x.name,
        published_at: x.tag_last_pushed,
        author: {
          login: 'bytedance',
          avatar_url: 'https://avatars3.githubusercontent.com/u/4158466?v=4',
          html_url: 'https://github.com/bytedance',
        },
      },
    },
  }));
}

router.get('/api/v1/activities', SessionMiddleware, PaginationMiddleware, async (ctx) => {
  let page = 1;
  let pageSize = 10;

  if (ctx.pagination.limit > 0 && ctx.pagination.offset >= 0) {
    page = ctx.pagination.offset / ctx.pagination.limit + 1;
    pageSize = ctx.pagination.limit;
  }

  // 'v' is used to filter standard versions
  const { count, results } = await docker.listImageTags('fedlearner/fedlearner-web-console', 'v', page, pageSize);
  ctx.body = { count, data: mapImageToRelease(results) };
});

module.exports = router;
