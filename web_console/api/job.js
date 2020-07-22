const router = require('@koa/router')();
const { Op } = require('sequelize');
const SessionMiddleware = require('../middlewares/session');
const k8s = require('../libs/k8s');
const es = require('../libs/es');
const { Job, Ticket, Federation } = require('../models');
const FederationClient = require('../rpc/client');
const getConfig = require('../utils/get_confg');
const checkParseJson = require('../utils/check_parse_json');
const { clientValidateJob, clientGenerateYaml } = require('../utils/job_builder');

const config = getConfig({
  NAMESPACE: process.env.NAMESPACE,
});
const namespace = config.NAMESPACE;

router.get('/api/v1/jobs', SessionMiddleware, async (ctx) => {
  const jobs = await Job.findAll({
    order: [['created_at', 'DESC']],
  });
  const { flapps } = await k8s.getFLAppsByNamespace(namespace);
  const data = jobs.map((job) => ({
    ...(flapps.items.find((item) => item.metadata.name === job.name)),
    localdata: job,
  }));
  ctx.body = { data };
});

router.get('/api/v1/job/:id', SessionMiddleware, async (ctx) => {
  const { id } = ctx.params;
  const job = await Job.findByPk(id);
  if (!job) {
    ctx.status = 404;
    ctx.body = {
      error: 'Job not found',
    };
    return;
  }
  const { flapp } = await k8s.getFLApp(namespace, job.name);
  ctx.body = {
    data: {
      ...flapp,
      localdata: job,
    },
  };
});

router.get('/api/v1/job/:k8s_name/pods', SessionMiddleware, async (ctx) => {
  const { k8s_name } = ctx.params;
  const { pods } = await k8s.getFLAppPods(namespace, k8s_name);
  ctx.body = { data: pods.items };
});

router.get('/api/v1/job/:k8s_name/logs', SessionMiddleware, async (ctx) => {
  const { k8s_name } = ctx.params;
  const { start_time } = ctx.query;
  if (!start_time) {
    ctx.status = 400;
    ctx.body = {
      error: 'start_time is required',
    };
    return;
  }
  const logs = await es.queryLog('filebeat-*', k8s_name, 'fedlearner-operator', start_time, Date.now());

  ctx.body = { data: logs };
});

router.get('/api/v1/job/pod/:pod_name/container', SessionMiddleware, async (ctx) => {
  const { pod_name } = ctx.params;
  const base = k8s.getBaseUrl();
  const { id } = await k8s.getWebshellSession(namespace, pod_name, 'tensorflow');
  ctx.body = { data: { id, base } };
});

router.get('/api/v1/job/pod/:pod_name/logs', SessionMiddleware, async (ctx) => {
  const { pod_name } = ctx.params;
  const { start_time } = ctx.query;
  if (!start_time) {
    ctx.status = 400;
    ctx.body = {
      error: 'start_time is required',
    };
    return;
  }
  const logs = await es.queryLog('filebeat-*', '', pod_name, start_time, Date.now());

  ctx.body = { data: logs };
});

router.post('/api/v1/job', SessionMiddleware, async (ctx) => {
  const { name, job_type, client_ticket_name, server_ticket_name } = ctx.request.body;

  if (!(/^[a-zA-Z\d-]+$/.test(name))) {
    ctx.status = 400;
    ctx.body = {
      error: 'name can only contain letters/numbers/-',
    };
    return;
  }

  const [client_params_pass, client_params] = checkParseJson(ctx.request.body.client_params);
  if (!client_params_pass) {
    ctx.status = 400;
    ctx.body = {
      error: 'client_params must be json',
    };
    return;
  }
  const [server_params_pass, server_params] = checkParseJson(ctx.request.body.server_params);
  if (!server_params_pass) {
    ctx.status = 400;
    ctx.body = {
      error: 'server_params must be json',
    };
    return;
  }

  const job = {
    name, job_type, client_ticket_name, server_ticket_name,
    client_params, server_params,
  };

  const exists = await Job.findOne({
    where: {
      name: { [Op.eq]: name },
    },
  });
  if (exists) {
    ctx.status = 422;
    ctx.body = {
      error: 'Job already exists',
    };
    return;
  }

  const clientTicket = await Ticket.findOne({
    where: {
      name: { [Op.eq]: client_ticket_name },
    },
  });
  if (!clientTicket) {
    ctx.status = 422;
    ctx.body = {
      error: 'client_ticket does not exist',
    };
    return;
  }

  try {
    clientValidateJob(job, clientTicket);
  } catch (e) {
    ctx.status = 400;
    ctx.body = {
      error: 'client_params validation failed',
    };
    return;
  }

  const clientFed = await Federation.findByPk(clientTicket.federation_id);
  if (!clientFed) {
    ctx.status = 422;
    ctx.body = {
      error: 'Federation does not exist',
    };
    return;
  }
  const rpcClient = new FederationClient(clientFed);
  try {
    await rpcClient.createJob(job);
  } catch (err) {
    ctx.status = 500;
    ctx.body = {
      error: err.details,
    };
    return;
  }

  const clientYaml = clientGenerateYaml(clientFed, job, clientTicket);

  await k8s.createFLApp(namespace, clientYaml);

  const [data, created] = await Job.findOrCreate({
    paranoid: false,
    where: {
      name: { [Op.eq]: name },
    },
    defaults: {
      ...job,
      user_id: ctx.session && ctx.session.user ? ctx.session.user.id : null,
    },
  });

  if (!created) {
    ctx.status = 422;
    ctx.body = {
      error: 'Job already exists',
    };
    return;
  }

  ctx.body = { data };
});

router.delete('/api/v1/job/:id', SessionMiddleware, async (ctx) => {
  // TODO: just owner can delete
  const { id } = ctx.params;
  const data = await Job.findByPk(id);

  if (!data) {
    ctx.status = 404;
    ctx.body = {
      error: 'Job not found',
    };
    return;
  }

  const ticket = await Ticket.findOne({
    where: {
      name: { [Op.eq]: data.client_ticket_name },
    },
  });
  const rpcClient = new FederationClient(ticket.federation);
  try {
    await rpcClient.deleteJob({ name: data.name });
  } catch (err) {
    ctx.status = 500;
    ctx.body = {
      error: err.details,
    };
    return;
  }
  await k8s.deleteFLApp(namespace, data.name);
  await data.destroy();

  ctx.body = { data };
});

module.exports = router;
