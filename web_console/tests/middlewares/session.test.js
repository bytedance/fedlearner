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

describe('SessionMiddleware', () => {
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

  it('redirect to /login for non-logged-in user', (done) => {
    request.get('/')
      .expect(302)
      .end((err, res) => {
        if (err) done(err);
        assert.deepStrictEqual(res.header.location, '/login');
        done();
      });
  });

  it('allow non-logged-in user access /login', (done) => {
    request.get('/login')
      .expect(200)
      .end((err, res) => {
        if (err) done(err);
        assert.deepStrictEqual(res.text, 'login');
        done();
      });
  });

  it('redirect to / for logged-in user accessing /login', (done) => {
    request.get('/login')
      .set('Cookie', userCookie)
      .expect(302)
      .end((err, res) => {
        if (err) done(err);
        assert.deepStrictEqual(res.header.location, '/');
        done();
      });
  });

  it('redirect to /404 for non-admin user accessing /admin', (done) => {
    request.get('/admin')
      .set('Cookie', userCookie)
      .expect(302)
      .end((err, res) => {
        if (err) done(err);
        assert.deepStrictEqual(res.header.location, '/404');
        done();
      });
  });

  it('allow admin access /admin', (done) => {
    request.get('/admin')
      .set('Cookie', adminCookie)
      .expect(200)
      .end((err, res) => {
        if (err) done(err);
        assert.deepStrictEqual(res.text, 'admin');
        done();
      });
  });

  it('should not redirect for favicon request', (done) => {
    request.get('/favicon.ico')
      .expect(200)
      .end((err, res) => {
        if (err) done(err);
        assert.deepStrictEqual(res.header['content-type'], 'image/x-icon');
        done();
      });
  });

  it('should not redirect for static file request', (done) => {
    request.get('/_next/static/test.js')
      .expect(200)
      .end((err, res) => {
        if (err) done(err);
        assert.deepStrictEqual(res.header['content-type'], 'application/javascript; charset=UTF-8');
        assert.deepStrictEqual(res.text, '<script>console.log("ok")</script>');
        done();
      });
  });
});
