const path = require('path');
const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const { Op } = require('sequelize');
const { Federation, Job, Ticket } = require('../models');
const k8s = require('../libs/k8s');
const { serverGenerateYaml, validateTicket } = require('../utils/job_builder');

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
    const data = await Ticket.findAll({ where });
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
      server_params: client_params,
    } = call.request;
    const ticketRecord = await Ticket.findOne({
      where: {
        name: { [Op.eq]: client_ticket_name },
      },
    });
    if (!ticketRecord) throw new Error('Ticket not found');
    const params = JSON.parse(client_params);
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
        client_params: JSON.parse(client_params),
      },
    });
    if (!created) throw new Error('Job already exists');
    job = data;
    const args = serverGenerateYaml(federation, job, ticketRecord);
    await k8s.createFLApp('default', args);

    callback(null, {
      data: {
        name: data.name,
        job_type: data.job_type,
        client_ticket_name: data.server_ticket_name,
        server_ticket_name: data.client_ticket_name,
        server_params: JSON.stringify(data.client_params),
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
    await k8s.deleteFLApp('default', job.name);
    await job.destroy({ force: true });
    callback(null, { message: 'Delete job successfully' });
  } catch (err) {
    callback(err);
  }
}

const server = new grpc.Server();

server.addService(pkg.federation.Federation.service, {
  getTickets,
  createJob,
  deleteJob,
});

module.exports = server;
