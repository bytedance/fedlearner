const assert = require('assert');
const { Op } = require('sequelize');
const supertest = require('supertest');
const server = require('../../server');
const models = require('../../models');
const { username, password, name, tel, is_admin } = require('../fixtures/user').user;

const { User } = models;
const request = supertest(server.callback());
let id;

describe('POST /api/v1/login', () => {
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
    id = record.id;
    if (record.deleted_at) {
      record.restore();
    }
  });

  it('respond 400 if missing username', (done) => {
    request.post('/api/v1/login')
      .send({ password })
      .expect(400)
      .end((err, res) => {
        if (err) done(err);
        assert.deepStrictEqual(res.body.error, 'Missing field: username');
        done();
      });
  });

  it('respond 400 if missing password', (done) => {
    request.post('/api/v1/login')
      .send({ username })
      .expect(400)
      .end((err, res) => {
        if (err) done(err);
        assert.deepStrictEqual(res.body.error, 'Missing field: password');
        done();
      });
  });

  it('respond 401 if authentication failed', (done) => {
    request.post('/api/v1/login')
      .send({ username, password })
      .expect(401)
      .end((err, res) => {
        if (err) done(err);
        assert.deepStrictEqual(res.body.error, 'Bad credentials');
        done();
      });
  });

  it('respond 404 if user not found', (done) => {
    request.post('/api/v1/login')
      .send({ username: 'foo', password })
      .expect(404)
      .end((err, res) => {
        if (err) done(err);
        assert.deepStrictEqual(res.body.error, 'User not found');
        done();
      });
  });

  it('respond 200 with user and set cookie', (done) => {
    request.post('/api/v1/login')
      .send({ username, password: username })
      .expect(200)
      .end((err, res) => {
        if (err) done(err);
        const cookie = res.header['set-cookie'][0];
        assert.ok(/user\.session/.test(cookie));
        assert.deepEqual(res.body.data, { id, username, name, tel, is_admin });
        done();
      });
  });
});
