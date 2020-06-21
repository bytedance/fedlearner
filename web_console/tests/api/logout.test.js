const assert = require('assert');
const { Op } = require('sequelize');
const supertest = require('supertest');
const server = require('../../server');
const models = require('../../models');
const { username, password, name, tel, is_admin } = require('../fixtures/user').user;

const { User } = models;
const request = supertest(server.callback());
let cookie;

describe('POST /api/v1/logout', () => {
  before(async () => {
    await models.sequelize.sync();
    const [record] = await User.findOrCreate({
      paranoid: false,
      where: {
        username: { [Op.eq]: username },
      },
      defaults: {
        username,
        password,
        name,
        tel,
        is_admin,
      },
    });
    if (record.deleted_at) {
      record.restore();
    }
    return new Promise((resolve, reject) => {
      request.post('/api/v1/login')
        .send({ username, password: username })
        .expect(200)
        .end((err, res) => {
          if (err) reject(err);
          cookie = res.header['set-cookie'].map((x) => x.split(';')[0]).join('; ');
          resolve();
        });
    });
  });

  it('respond 404 if session not found', (done) => {
    request.post('/api/v1/logout')
      .expect(404)
      .end((err, res) => {
        if (err) done(err);
        assert.deepStrictEqual(res.body.error, 'Session not found');
        done();
      });
  });

  it('respond 200 and unset cookie', (done) => {
    request.post('/api/v1/logout')
      .set('Cookie', cookie)
      .expect(200)
      .end((err, res) => {
        if (err) done(err);
        assert.ok(/user\.session=;/.test(res.header['set-cookie'][0]));
        assert.deepStrictEqual(res.body.message, 'Logout successfully');
        done();
      });
  });
});
