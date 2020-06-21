const assert = require('assert');
const { Op } = require('sequelize');
const supertest = require('supertest');
const server = require('../fixtures/server');
const models = require('../../models');
const { admin } = require('../fixtures/user');
const { leader, follower } = require('../fixtures/federation');

const { Federation, User } = models;
const request = supertest(server.callback());
let adminCookie;

describe('Federation System', () => {
  before(async () => {
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
        name: { [Op.eq]: leader.name },
      },
      defaults: leader,
    });
    if (leaderRecord.deleted_at) {
      leaderRecord.restore();
    }

    const [followerRecord] = await Federation.findOrCreate({
      paranoid: false,
      where: {
        name: { [Op.eq]: follower.name },
      },
      defaults: follower,
    });
    if (followerRecord.deleted_at) {
      followerRecord.restore();
    }

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
});
