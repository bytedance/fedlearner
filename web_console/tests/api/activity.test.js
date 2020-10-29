const assert = require('assert');
const { Op } = require('sequelize');
const supertest = require('supertest');
const server = require('../fixtures/server');
const { release } = require('../fixtures/activity');
const models = require('../../models');
const { admin } = require('../fixtures/user');

const { User } = models;
const request = supertest(server.callback());
let adminCookie;

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
}

describe('Activity API', () => {
  before(async () => {
    await setupDatabase();
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

  describe('GET /api/v1/activities', () => {
    it('should return releases as expected', (done) => {
      request.get('/api/v1/activities')
        .set('Cookie', adminCookie)
        .expect(200)
        .end((err, res) => {
          if (err) done(err);
          const item = res.body.data.find((x) => x.id === release.id);
          assert.deepStrictEqual(item, release);
          done();
        });
    });
  });
});
