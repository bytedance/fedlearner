const assert = require('assert');
const { Op } = require('sequelize');
const supertest = require('supertest');
const grpc = require('@grpc/grpc-js');
const server = require('../fixtures/server');
const models = require('../../models');
const { admin } = require('../fixtures/user');
const federations = require('../fixtures/federation');
const tickets = require('../fixtures/ticket');
const rpcServer = require('../../rpc/server');

const { Federation, User, Ticket } = models;
const request = supertest(server.callback());
let adminCookie;
let leader;
let follower;
let followerTicket;

async function setupDatabase() {
  await models.sequelize.sync();

  const [adminRecord] = await User.findOrCreate({
    paranoid: false,
    where: {
      username: { [Op.eq]: admin.username },
    },
    defaults: admin,
  });
  if (adminRecord.deleted_at) {
    adminRecord.restore();
  }

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
}

function setupRpcServer() {
  return new Promise((resolve, reject) => {
    rpcServer.bindAsync(
      follower.k8s_settings.grpc_spec.peerURL,
      grpc.ServerCredentials.createInsecure(),
      (err) => {
        if (err) reject(err);
        rpcServer.start();
        resolve();
      },
    );
  });
}

describe('Federation System', () => {
  before(async () => {
    await setupDatabase();
    await setupRpcServer();
    return new Promise((resolve, reject) => {
      request.post('/api/v1/login')
        .send({ username: admin.username, password: admin.username })
        .expect(200)
        .end((err, res) => {
          if (err) reject(err);
          adminCookie = res.header['set-cookie'].map((x) => x.split(';')[0]).join('; ');
          resolve();
        });
    });
  });

  after(() => rpcServer.forceShutdown());

  describe('GET /api/v1/federations', () => {
    it('should return all federations', (done) => {
      request.get('/api/v1/federations')
        .set('Cookie', adminCookie)
        .expect(200)
        .end((err, res) => {
          if (err) done(err);
          assert.ok(res.body.data.find((x) => x.name === leader.name));
          assert.ok(res.body.data.find((x) => x.name === follower.name));
          done();
        });
    });
  });

  describe('GET /api/v1/federations/:id/tickets', () => {
    it('respond 404 if federation not found', (done) => {
      request.get('/api/v1/federations/218379128738912/tickets')
        .set('Cookie', adminCookie)
        .expect(404)
        .end((err, res) => {
          if (err) done(err);
          assert.deepStrictEqual(res.body.error, 'Federation not found');
          done();
        });
    });

    it('respond 200 with tickets from federation', (done) => {
      request.get(`/api/v1/federations/${follower.id}/tickets`)
        .set('Cookie', adminCookie)
        .expect(200)
        .end((err, res) => {
          if (err) done(err);
          assert.ok(res.body.data.find((x) => x.name === followerTicket.name));
          done();
        });
    });
  });
});
