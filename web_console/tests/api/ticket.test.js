const assert = require('assert');
const { Op } = require('sequelize');
const supertest = require('supertest');
const server = require('../fixtures/server');
const models = require('../../models');
const users = require('../fixtures/user');
const federations = require('../fixtures/federation');
const tickets = require('../fixtures/ticket');

const { Federation, User, Ticket } = models;
const request = supertest(server.callback());
let admin;
let adminCookie;
let leader;
let follower;
let leaderTicket;
let followerTicket;

describe('Ticket System', () => {
  before(async () => {
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

    const [leaderTicketRecord] = await Ticket.findOrCreate({
      paranoid: false,
      where: {
        name: { [Op.eq]: tickets.leader.name },
      },
      defaults: {
        ...tickets.leader,
        federation_id: leader.id,
        user_id: admin.id,
      },
    });
    if (leaderTicketRecord.deleted_at) {
      leaderTicketRecord.restore();
    }
    leaderTicket = leaderTicketRecord;

    const [followerTicketRecord] = await Ticket.findOrCreate({
      paranoid: false,
      where: {
        name: { [Op.eq]: tickets.follower.name },
      },
      defaults: {
        ...tickets.follower,
        federation_id: follower.id,
        user_id: admin.id,
      },
    });
    if (followerTicketRecord.deleted_at) {
      followerTicketRecord.restore();
    }
    followerTicket = followerTicketRecord;

    const testTicketRecord = await Ticket.findOne({
      paranoid: false,
      where: {
        name: { [Op.eq]: tickets.test.name },
      },
    });
    if (testTicketRecord) {
      await testTicketRecord.destroy({ force: true });
    }

    return new Promise((resolve, reject) => {
      request.post('/api/v1/login')
        .send({ username: users.admin.username, password: users.admin.username })
        .expect(200)
        .end((err, res) => {
          if (err) reject(err);
          adminCookie = res.header['set-cookie'].map((x) => x.split(';')[0]).join('; ');
          resolve();
        });
    });
  });

  describe('GET /api/v1/tickets', () => {
    it('should return all tickets', (done) => {
      request.get('/api/v1/tickets')
        .set('Cookie', adminCookie)
        .expect(200)
        .end((err, res) => {
          if (err) done(err);
          assert.ok(res.body.data.find((x) => x.federation_id === leader.id));
          assert.ok(res.body.data.find((x) => x.federation_id === follower.id));
          done();
        });
    });

    it('should return tickets filtered by federation_id', (done) => {
      request.get(`/api/v1/tickets?federation_id=${leader.id}`)
        .set('Cookie', adminCookie)
        .expect(200)
        .end((err, res) => {
          if (err) done(err);
          assert.ok(res.body.data.find((x) => x.federation_id === leader.id && x.name === leaderTicket.name));
          done();
        });
    });
  });

  describe('POST /api/v1/tickets', () => {
    it('respond 200 with created ticket', (done) => {
      request.post('/api/v1/tickets')
        .set('Cookie', adminCookie)
        .send({ ...tickets.test, federation_id: leader.id })
        .expect(200)
        .end((err, res) => {
          if (err) done(err);
          assert.strictEqual(res.body.data.name, tickets.test.name);
          done();
        });
    });
  });
});
