const assert = require('assert');
const grpc = require('@grpc/grpc-js');
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
let follower;
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

  const [followerRecord] = await Federation.findOrCreate({
    paranoid: false,
    where: {
      name: { [Op.eq]: federations.follower.name },
    },
    defaults: federations.follower,
  });
  if (followerRecord.deleted_at) {
    followerRecord.restore();
  }
  follower = followerRecord;

  const [followerTicketRecord] = await Ticket.findOrCreate({
    paranoid: false,
    where: {
      name: { [Op.eq]: tickets.follower.name },
    },
    defaults: {
      ...tickets.follower,
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
    server.bindAsync(
      follower.k8s_settings.grpc_spec.peerURL,
      grpc.ServerCredentials.createInsecure(),
      (err) => {
        if (err) reject(err);
        server.start();
        client = new FederationClient(follower);
        resolve();
      },
    );
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
