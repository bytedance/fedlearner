const assert = require('assert');
const crypto = require('crypto');
const { Op } = require('sequelize');
const supertest = require('supertest');
const server = require('../../server');
const models = require('../../models');
const { admin, user } = require('../fixtures/user');

const { User } = models;
const request = supertest(server.callback());
const testUser = {
  username: crypto.randomBytes(8).toString('hex'),
  name: 'Test User',
  secret: 'xxx',
};
let adminCookie;
let userCookie;

describe('User System', () => {
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

  after(async () => {
    await User.destroy({
      force: true,
      paranoid: false,
      where: {
        username: { [Op.eq]: testUser.username },
      },
    });
  });

  describe('GET /api/v1/user', () => {
    it('respond 200 with current user info', (done) => {
      request.get('/api/v1/user')
        .set('Cookie', userCookie)
        .expect(200)
        .end((err, res) => {
          if (err) done(err);
          assert.deepStrictEqual(res.body.data.name, user.name);
          done();
        });
    });

    it('respond 200 with current user info', (done) => {
      request.get('/api/v1/user')
        .set('Cookie', adminCookie)
        .expect(200)
        .end((err, res) => {
          if (err) done(err);
          assert.deepStrictEqual(res.body.data.name, admin.name);
          done();
        });
    });
  });

  describe('GET /api/v1/users', () => {
    it('should return all users', (done) => {
      request.get('/api/v1/users')
        .set('Cookie', adminCookie)
        .expect(200)
        .end((err, res) => {
          if (err) done(err);
          assert.ok(res.body.data.find((x) => x.name === admin.name));
          assert.ok(res.body.data.find((x) => x.name === user.name));
          done();
        });
    });
  });

  describe('POST /api/v1/users', () => {
    it('respond 400 if missing username', (done) => {
      request.post('/api/v1/users')
        .set('Cookie', adminCookie)
        .send({ password: 'xxx' })
        .expect(400)
        .end((err, res) => {
          if (err) done(err);
          assert.deepStrictEqual(res.body.error, 'Missing field: username');
          done();
        });
    });

    it('respond 400 if missing password', (done) => {
      request.post('/api/v1/users')
        .set('Cookie', adminCookie)
        .send({ username: 'xxx' })
        .expect(400)
        .end((err, res) => {
          if (err) done(err);
          assert.deepStrictEqual(res.body.error, 'Missing field: password');
          done();
        });
    });

    it('respond 422 if user exists', (done) => {
      request.post('/api/v1/users')
        .set('Cookie', adminCookie)
        .send({ username: user.username, password: 'xxx' })
        .expect(422)
        .end((err, res) => {
          if (err) done(err);
          assert.deepStrictEqual(res.body.error, 'User already exists');
          done();
        });
    });

    it('respond 200 with created user', (done) => {
      request.post('/api/v1/users')
        .set('Cookie', adminCookie)
        .send({ username: testUser.username, password: testUser.secret })
        .expect(200)
        .end((err, res) => {
          if (err) done(err);
          assert.ok(res.body.data.id);
          testUser.id = res.body.data.id;
          done();
        });
    });
  });

  describe('DELETE /api/v1/users/:id', () => {
    it('respond 404 if user not found', (done) => {
      request.delete('/api/v1/users/218379128738912')
        .set('Cookie', adminCookie)
        .expect(404)
        .end((err, res) => {
          if (err) done(err);
          assert.deepStrictEqual(res.body.error, 'User not found');
          done();
        });
    });

    it('respond 200 with soft-deleted user', (done) => {
      request.delete(`/api/v1/users/${testUser.id}`)
        .set('Cookie', adminCookie)
        .expect(200)
        .end((err, res) => {
          if (err) done(err);
          assert.ok(res.body.data.deleted_at);
          done();
        });
    });
  });
});
