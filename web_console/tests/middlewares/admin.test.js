const assert = require('assert');
const { Op } = require('sequelize');
const supertest = require('supertest');
const server = require('../fixtures/server');
const models = require('../../models');
const { admin, user } = require('../fixtures/user');

const { User } = models;
const request = supertest(server.callback());
let adminCookie;
let userCookie;

describe('AdminMiddleware', () => {
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
    const [userRecord] = await User.findOrCreate({
      paranoid: false,
      where: {
        username: { [Op.eq]: user.username },
      },
      defaults: user,
    });
    if (userRecord.deleted_at) {
      userRecord.restore();
    }
    return Promise.all([
      new Promise((resolve, reject) => {
        request.post('/api/v1/login')
          .send({ username: admin.username, password: admin.username })
          .expect(200)
          .end((err, res) => {
            if (err) reject(err);
            adminCookie = res.header['set-cookie'].map((x) => x.split(';')[0]).join('; ');
            resolve();
          });
      }),
      new Promise((resolve, reject) => {
        request.post('/api/v1/login')
          .send({ username: user.username, password: user.username })
          .expect(200)
          .end((err, res) => {
            if (err) reject(err);
            userCookie = res.header['set-cookie'].map((x) => x.split(';')[0]).join('; ');
            resolve();
          });
      }),
    ]);
  });

  it('respond 403 for non-admin user', (done) => {
    request.post('/api/v1/admin/ping')
      .set('Cookie', userCookie)
      .expect(403)
      .end((err, res) => {
        if (err) done(err);
        assert.deepStrictEqual(res.body.error, 'Permission denied');
        done();
      });
  });

  it('allow next middleware for admin', (done) => {
    request.post('/api/v1/admin/ping')
      .set('Cookie', adminCookie)
      .expect(200)
      .end((err, res) => {
        if (err) done(err);
        assert.deepStrictEqual(res.body.message, 'pong');
        done();
      });
  });
});
