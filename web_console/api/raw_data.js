const router = require('@koa/router')();
const { Op } = require('sequelize');
const SessionMiddleware = require('../middlewares/session');
const FindOptionsMiddleware = require('../middlewares/find_options');
const checkParseJson = require('../utils/check_parse_json');
const k8s = require('../libs/k8s');
const getConfig = require('../utils/get_confg');
const { RawData, Federation } = require('../models');
const { portalGenerateYaml } = require('../utils/job_builder');

const config = getConfig({
  NAMESPACE: process.env.NAMESPACE,
});
const namespace = config.NAMESPACE;

router.get('/api/v1/raw_datas', SessionMiddleware, FindOptionsMiddleware, async (ctx) => {
  const data = await RawData.findAll({
    ...ctx.findOptions,
    order: [['created_at', 'DESC']],
  });
  ctx.body = { data };
});

router.get('/api/v1/raw_data/:id', SessionMiddleware, async (ctx) => {
  const { id } = ctx.params;
  const rawData = await RawData.findByPk(id, {
    include: 'federation',
  });
  if (!rawData) {
    ctx.status = 404;
    ctx.body = {
      error: 'RawData not found',
    };
    return;
  }
  let flapp = {};
  if (rawData.submitted) {
    flapp = (await k8s.getFLApp(namespace, rawData.name)).flapp;
  }
  ctx.body = {
    data: {
      ...flapp,
      localdata: rawData,
    },
  };
});

router.post('/api/v1/raw_data', SessionMiddleware, async (ctx) => {
  const { name, federation_id, input, output, remark, data_portal_type } = ctx.request.body;

  if (!(/^[a-zA-Z\d-]+$/.test(name))) {
    ctx.status = 400;
    ctx.body = {
      error: 'name can only contain letters/numbers/-',
    };
    return;
  }

  const output_partition_num = parseInt(ctx.request.body.output_partition_num, 10);
  if (Number.isNaN(output_partition_num) || output_partition_num < 0) {
    ctx.status = 400;
    ctx.body = {
      error: 'output_partition_num must be integer',
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
  const federation = await Federation.findByPk(federation_id);
  if (!federation) {
    ctx.status = 400;
    ctx.body = {
      error: 'Federation not exists',
    };
    return;
  }

  const rawData = { name, federation_id, input, output, context, remark, output_partition_num, data_portal_type };

  try {
    portalGenerateYaml(federation, rawData);
  } catch (e) {
    ctx.status = 400;
    ctx.body = {
      error: `context not well-formed ${e.message}`,
    };
    return;
  }

  const [data, created] = await RawData.findOrCreate({
    paranoid: false,
    where: {
      name: { [Op.eq]: name },
    },
    defaults: {
      ...rawData,
      user_id: ctx.session.user.id,
      submitted: false,
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

router.post('/api/v1/raw_data/:id/submit', SessionMiddleware, async (ctx) => {
  const { id } = ctx.params;
  const rawData = await RawData.findByPk(id, {
    include: 'federation',
  });
  if (!rawData) {
    ctx.status = 404;
    ctx.body = {
      error: 'RawData not found',
    };
    return;
  }

  if (rawData.submitted) {
    ctx.status = 400;
    ctx.body = {
      error: 'RawData is submitted',
    };
    return;
  }

  const yaml = portalGenerateYaml(rawData.federation, rawData);

  await k8s.createFLApp(namespace, yaml);

  rawData.submitted = true;

  const data = await rawData.save();

  ctx.body = { data };
});

router.post('/api/v1/raw_data/:id/delete_job', SessionMiddleware, async (ctx) => {
  const { id } = ctx.params;
  const rawData = await RawData.findByPk(id);
  if (!rawData) {
    ctx.status = 404;
    ctx.body = {
      error: 'RawData not found',
    };
    return;
  }

  if (!rawData.submitted) {
    ctx.status = 400;
    ctx.body = {
      error: 'RawData is unsubmitted',
    };
    return;
  }

  await k8s.deleteFLApp(namespace, rawData.name);

  rawData.submitted = false;

  const data = await rawData.save();

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

  if (data.submitted) {
    await k8s.deleteFLApp(namespace, data.name);
  }

  await data.destroy();

  ctx.body = { data };
});

module.exports = router;
