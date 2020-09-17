const path = require('path');
const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const { Op } = require('sequelize');
const { Federation, Job, Ticket } = require('../models');
const k8s = require('../libs/k8s');
const { serverGenerateYaml, validateTicket } = require('../utils/job_builder');
const getConfig = require('../utils/get_confg');

const { NAMESPACE } = getConfig({
  NAMESPACE: process.env.NAMESPACE,
});
const packageDefinition = protoLoader.loadSync(
  path.resolve(__dirname, 'meta.proto'),
  {
    keepCase: true,
    longs: String,
    enums: String,
    defaults: true,
    oneofs: true,
  },
);
const pkg = grpc.loadPackageDefinition(packageDefinition);

/**
 * validate call with custom header
 *
 * @param {grpc.MetaData} metadata
 * @return {Object} - the federation record
 */
async function authenticate(metadata) {
  const headers = metadata.toHttp2Headers();
  const name = headers['x-federation'];
  const federation = await Federation.findOne({
    where: {
      name: { [Op.eq]: name },
    },
  });
  if (!federation) throw new Error('Unauthorized');
  return federation;
}

/**
 * get available tickets of current federation
 */
async function getTickets(call, callback) {
  try {
    const federation = await authenticate(call.metadata);
    const { role, job_type } = call.request;
    const where = {
      federation_id: { [Op.eq]: federation.id },
    };
    if (role) {
      where.role = { [Op.eq]: role };
    }
    if (job_type) {
      where.job_type = { [Op.eq]: job_type };
    }
    let data = await Ticket.findAll({ where });
    data = data.map((x) => ({
      name: x.name,
      job_type: x.job_type,
      role: x.role,
      sdk_version: x.sdk_version,
      expire_time: x.expire_time,
      remark: x.remark,
      public_params: JSON.stringify(x.public_params),
    }));
    callback(null, { data });
  } catch (err) {
    callback(err);
  }
}

/**
 * Always remember the sense of `client` and `server`:
 * - `client` stands for requester
 * - `server` stands for responder
 */
async function createJob(call, callback) {
  let job;

  try {
    const federation = await authenticate(call.metadata);

    const {
      name,
      job_type,
      client_ticket_name: server_ticket_name,
      server_ticket_name: client_ticket_name,
      server_params,
    } = call.request;
    const ticketRecord = await Ticket.findOne({
      where: {
        name: { [Op.eq]: client_ticket_name },
      },
    });
    if (!ticketRecord) throw new Error('Ticket not found');
    if (ticketRecord.federation_id != federation.id) throw new Error("Invalid ticket name");

    const params = JSON.parse(server_params);
    validateTicket(ticketRecord, params);

    const [data, created] = await Job.findOrCreate({
      paranoid: false,
      where: {
        name: { [Op.eq]: name },
      },
      defaults: {
        name,
        job_type,
        client_ticket_name,
        server_ticket_name,
        server_params: JSON.parse(server_params),
        status: 'started',
        federation_id: federation.id,
      },
    });
    if (!created) throw new Error('Job already exists');
    job = data;
    const args = serverGenerateYaml(federation, job, ticketRecord);
    await k8s.createFLApp(NAMESPACE, args);

    callback(null, {
      data: {
        name: data.name,
        job_type: data.job_type,
        client_ticket_name: data.server_ticket_name,
        server_ticket_name: data.client_ticket_name,
        server_params: JSON.stringify(data.server_params),
        status: 'started',
        federation_id: federation.id,
      },
    });
  } catch (err) {
    if (job) {
      await job.destroy({ force: true });
    }
    callback(err);
  }
}

async function deleteJob(call, callback) {
  try {
    await authenticate(call.metadata);
    const job = await Job.findOne({
      where: {
        name: { [Op.eq]: call.request.name },
      },
    });
    if (!job) throw new Error('Job not found');
    if (data.status == 'started') {
      await k8s.deleteFLApp(NAMESPACE, job.name);
    }
    await job.destroy({ force: true });
    callback(null, { message: 'Delete job successfully' });
  } catch (err) {
    callback(err);
  }
}

async function updateJob(call, callback) {
  try {
    const federation = await authenticate(call.metadata);

    const {
      name,
      job_type,
      client_ticket_name: server_ticket_name,
      server_ticket_name: client_ticket_name,
      server_params,
      status,
    } = call.request;

    const new_job = {
      name, job_type, client_ticket_name, server_ticket_name,
      server_params, status,
    }

    const old_job = await Job.findOne({
      where: {
        name: { [Op.eq]: name },
      },
    });
    if (!old_job) throw new Error(`Job ${name} not found`);

    if (old_job.status === 'error') {
      throw new Error("Cannot update errored job");
    }
    if (old_job.status === 'started' && new_job.status != 'stopped') {
      throw new Error("Cannot change running job");
    }
    if (job_type != old_job.job_type) {
      throw new Error("Cannot change job type");
    }

    const ticketRecord = await Ticket.findOne({
      where: {
        name: { [Op.eq]: client_ticket_name },
      },
    });
    if (!ticketRecord) throw new Error('Ticket not found');
    if (ticketRecord.federation_id != federation.id) throw new Error("Invalid ticket name");

    if (ticketRecord.federation_id != old_job.federation_id) {
      throw new Error("Cannot change job federation");
    }

    const params = JSON.parse(server_params);
    validateTicket(ticketRecord, params);

    if (old_job.status === 'started' && status === 'stopped') {
      flapp = (await k8s.getFLApp(NAMESPACE, name)).flapp;
      pods = (await k8s.getFLAppPods(NAMESPACE, name)).pods;
      old_job.k8s_meta_snapshot = JSON.stringify({flapp, pods});
      await k8s.deleteFLApp(NAMESPACE, name);
    } else if (old_job.status === 'stopped' && new_job.status === 'started') {
      const args = serverGenerateYaml(federation, new_job, ticketRecord);
      await k8s.createFLApp(NAMESPACE, args);
    }

    old_job.client_ticket_name = new_job.client_ticket_name;
    old_job.server_ticket_name = new_job.server_ticket_name;
    old_job.server_params = new_job.server_params;
    old_job.status = new_job.status;
    old_job.federation_id = new_job.federation_id;

    const data = await old_job.save();

    callback(null, {
      data: {
        name: data.name,
        job_type: data.job_type,
        client_ticket_name: data.server_ticket_name,
        server_ticket_name: data.client_ticket_name,
        server_params: JSON.stringify(data.server_params),
      },
      status: data.status,
    });
  } catch (err) {
    callback(err);
  }
}

/**
 * get available tickets of current federation
 */
async function heartBeat(call, callback) {
  try {
    const federation = await authenticate(call.metadata);
    callback(null, { status: 'success' });
  } catch (err) {
    callback(err);
  }
}

const server = new grpc.Server();

server.addService(pkg.federation.Federation.service, {
  getTickets,
  createJob,
  deleteJob,
  updateJob,
  heartBeat,
});

module.exports = server;
