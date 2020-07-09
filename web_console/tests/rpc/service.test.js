const assert = require('assert');
const grpc = require('@grpc/grpc-js');
const getPort = require('get-port');
const { Op } = require('sequelize');
const models = require('../../models');
const server = require('../../rpc/server');
const FederationClient = require('../../rpc/client');
const users = require('../fixtures/user');
const federations = require('../fixtures/federation');
const tickets = require('../fixtures/ticket');
const jobs = require('../fixtures/job');

const { Federation, Ticket, User, Job } = models;
let admin;
let leader;
let followerTicket;
let client;

async function setupDatabase() {
  await models.sequelize.sync();

  const [adminRecord] = await User.findOrCreate({
    paranoid: false,
    where: {
      username: { [Op.eq]: users.admin.username },
    },
    defaults: users.admin,
  });
  if (adminRecord.deleted_at) {
    adminRecord.restore();
  }
  admin = adminRecord;

  const [leaderRecord] = await Federation.findOrCreate({
    paranoid: false,
    where: {
      name: { [Op.eq]: federations.leader.name },
    },
    defaults: federations.leader,
  });
  if (leaderRecord.deleted_at) {
    leaderRecord.restore();
  }
  leader = leaderRecord;

  const [followerTicketRecord] = await Ticket.findOrCreate({
    paranoid: false,
    where: {
      name: { [Op.eq]: tickets.follower.name },
    },
    defaults: {
      ...tickets.leader,
      federation_id: leader.id,
      user_id: admin.id,
    },
  });
  if (followerTicketRecord.deleted_at) {
    followerTicketRecord.restore();
  }
  followerTicket = followerTicketRecord;

  const [testJobRecord] = await Job.findOrCreate({
    paranoid: false,
    where: {
      name: { [Op.eq]: jobs.test.name },
    },
    defaults: jobs.test,
  });
  if (testJobRecord.deleted_at) {
    testJobRecord.restore();
  }
}

function setupRpcServer() {
  return new Promise((resolve, reject) => {
    getPort({ port: 1990 })
      .then((port) => {
        const address = `0.0.0.0:${port}`;
        server.bindAsync(
          address,
          grpc.ServerCredentials.createInsecure(),
          (err) => {
            if (err) reject(err);
            server.start();
            client = new FederationClient(address, leader.k8s_settings.authority, {
              ...leader.k8s_settings.extraHeaders,
              'x-federation': leader.name,
            });
            resolve();
          },
        );
      })
      .catch((err) => reject(err));
  });
}

describe('Federation Service', () => {
  before(async () => {
    await setupDatabase();
    await setupRpcServer();
  });

  after(() => server.forceShutdown());

  describe('GetTickets', () => {
    it('should respond tickets for current federation', async () => {
      const { data } = await client.getTickets();
      assert.ok(data.find((x) => x.name === followerTicket.name));
    });
  });

  describe('CreateJob', () => {
    it('should throw error if ticket not found', async () => {
      try {
        await client.createJob({
          name: 'xxx',
          job_type: 'leader',
          client_ticket_name: 'xxx',
          server_ticket_name: 'xxx',
          server_params: 'xxx',
          client_params: 'xxx',
        });
      } catch (err) {
        assert.strictEqual(err.code, 2);
        assert.strictEqual(err.details, 'Ticket not found');
      }
    });

    it('should throw error if job exists', async () => {
      try {
        await client.createJob({
          ...jobs.test,
          client_params: JSON.stringify(jobs.test.client_params),
          server_params: JSON.stringify(jobs.test.server_params),
        });
      } catch (err) {
        assert.strictEqual(err.code, 2);
        assert.strictEqual(err.details, 'Job already exists');
      }
    });

    it('should create job successfully', async () => {
      // TODO: use k8s client to create job @marswong
    });
  });

  describe('DeleteJob', () => {
    it('should delete job successfully', async () => {
      // TODO: use k8s client to delete job @marswong
    });
  });
});
