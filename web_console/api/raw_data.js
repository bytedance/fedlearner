const router = require('@koa/router')();
const { Op } = require('sequelize');
const SessionMiddleware = require('../middlewares/session');
const checkParseJson = require('../utils/check_parse_json');
const KubernetesClient = require('../libs/k8s');
const getConfig = require('../utils/get_confg');
const { RawData } = require('../models');
// const { rawGenerateYaml } = require('../utils/job_builder');

const config = getConfig({
  NAMESPACE: process.env.NAMESPACE,
});
const namespace = config.NAMESPACE;

const k8s = new KubernetesClient();

router.get('/api/v1/raw_datas', SessionMiddleware, async (ctx) => {
  const data = await RawData.findAll({ order: [['created_at', 'DESC']] });
  ctx.body = { data };
});

router.get('/api/v1/raw_data/:id', SessionMiddleware, async (ctx) => {
  const { id } = ctx.params;
  const rawData = await RawData.findByPk(id);
  if (!rawData) {
    ctx.status = 404;
    ctx.body = {
      error: 'RawData not found',
    };
    return;
  }
  const { flapp } = await k8s.getFLApp(namespace, rawData.k8s_name);
  ctx.body = {
    data: {
      ...flapp,
      localdata: rawData,
    },
  };
});

router.post('/api/v1/raw_data', SessionMiddleware, async (ctx) => {
  const { name, input, output, comment } = ctx.request.body;

  if (!(/^[a-zA-Z\d_]+$/.test(name))) {
    ctx.status = 400;
    ctx.body = {
      error: 'name can only contain letters/numbers/_',
    };
    return;
  }

  const [context_pass, context] = checkParseJson(ctx.request.body.context);
  if (!context_pass) {
    ctx.status = 400;
    ctx.body = {
      error: 'context must be json',
    };
    return;
  }
  const rawData = { name, input, output, context, comment };

  const exists = await RawData.findOne({
    where: {
      name: { [Op.eq]: name },
    },
  });
  if (exists) {
    ctx.status = 422;
    ctx.body = {
      error: 'RawData already exists',
    };
    return;
  }

  // TODO: generate raw yaml
  // const yaml = rawGenerateYaml(clientFed, job, clientTicket, serverTicket);

  // const res = await k8s.createFLApp(namespace, yaml);

  const [data, created] = await RawData.findOrCreate({
    paranoid: false,
    where: {
      name: { [Op.eq]: name },
    },
    defaults: {
      ...rawData,
      user_id: ctx.session.user.id,
      // k8s_name: res.metadata.name,
    },
  });

  if (!created) {
    ctx.status = 422;
    ctx.body = {
      error: 'RawData already exists',
    };
    return;
  }

  ctx.body = { data };
});

router.delete('/api/v1/raw_data/:id', SessionMiddleware, async (ctx) => {
  // TODO: just owner can delete
  const { id } = ctx.params;
  const data = await RawData.findByPk(id);

  if (!data) {
    ctx.status = 404;
    ctx.body = {
      error: 'RawData not found',
    };
    return;
  }

  await k8s.deleteFLApp(namespace, data.k8s_name);
  await data.destroy();

  ctx.body = { data };
});

module.exports = router;
