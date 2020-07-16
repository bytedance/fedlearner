const assert = require('assert');
const supertest = require('supertest');
const server = require('../fixtures/server');
const users = require('../fixtures/user');
const models = require('../../models');
const raw_data = require('../fixtures/raw_data');

const request = supertest(server.callback());
let userCookie;
let savedRawData;

describe('RawData System', () => {
  before(async () => {
    await models.sequelize.sync();

    return new Promise((resolve, reject) => {
      request.post('/api/v1/login')
        .send({ username: users.user.username, password: users.user.username })
        .expect(200)
        .end((err, res) => {
          if (err) reject(err);
          userCookie = res.header['set-cookie'].map((x) => x.split(';')[0]).join('; ');
          resolve();
        });
    });
  });

  describe('POST /api/v1/raw_data', () => {
    it('respond 400 if name validation failed', (done) => {
      request.post('/api/v1/raw_data')
        .set('Cookie', userCookie)
        .send({ ...raw_data, name: '$ no *=' })
        .expect(400)
        .end((err, res) => {
          if (err) done(err);
          assert.deepStrictEqual(res.body.error, 'name can only contain letters/numbers/_');
          done();
        });
    });

    it('respond 400 if context is not json', (done) => {
      request.post('/api/v1/raw_data')
        .set('Cookie', userCookie)
        .send({ ...raw_data, context: 'string' })
        .expect(400)
        .end((err, res) => {
          if (err) done(err);
          assert.deepStrictEqual(res.body.error, 'context must be json');
          done();
        });
    });

    it('respond 200 with created RawData', (done) => {
      request.post('/api/v1/raw_data')
        .set('Cookie', userCookie)
        .send(raw_data)
        .expect(200)
        .end((err, res) => {
          if (err) done(err);
          assert.strictEqual(res.body.data.name, raw_data.name);
          savedRawData = res.body.data;
          done();
        });
    });

    it('respond 422 if RawData already exists', (done) => {
      request.post('/api/v1/raw_data')
        .set('Cookie', userCookie)
        .send(raw_data)
        .expect(422)
        .end((err, res) => {
          if (err) done(err);
          assert.deepStrictEqual(res.body.error, 'RawData already exists');
          done();
        });
    });
  });

  describe('POST /api/v1/raw_data/:id/submit', () => {
    it('respond 404 if RawData does not exist', (done) => {
      request.post('/api/v1/raw_data/i_am_not_exist/submit')
        .set('Cookie', userCookie)
        .expect(404)
        .end((err, res) => {
          if (err) done(err);
          assert.deepStrictEqual(res.body.error, 'RawData not found');
          done();
        });
    });

    it('respond 200 with updated RawData', (done) => {
      request.post(`/api/v1/raw_data/${savedRawData.id}/submit`)
        .set('Cookie', userCookie)
        .expect(200)
        .end((err, res) => {
          if (err) done(err);
          assert.strictEqual(res.body.data.name, raw_data.name);
          assert.ok(res.body.data.localdata.k8s_name);
          done();
        });
    });
  });

  describe('GET /api/v1/raw_datas', () => {
    it('should return all RawDatas', (done) => {
      request.get('/api/v1/raw_datas')
        .set('Cookie', userCookie)
        .expect(200)
        .end((err, res) => {
          if (err) done(err);
          const j = res.body.data.find((x) => x.localdata.name === raw_data.name);
          assert.ok(j);
          assert.ok(j.metadata);
          savedRawData = j;
          done();
        });
    });
  });

  describe('GET /api/v1/raw_data/:id', () => {
    it('respond 404 if RawData does not exist', (done) => {
      request.get('/api/v1/raw_data/i_am_not_exist')
        .set('Cookie', userCookie)
        .expect(404)
        .end((err, res) => {
          if (err) done(err);
          assert.deepStrictEqual(res.body.error, 'RawData not found');
          done();
        });
    });

    it('respond 200 with created RawData', (done) => {
      request.get(`/api/v1/raw_data/${savedRawData.id}`)
        .set('Cookie', userCookie)
        .expect(200)
        .end((err, res) => {
          if (err) done(err);
          assert.ok(res.body.data.localdata.name === raw_data.name);
          assert.ok(res.body.data.metadata);
          done();
        });
    });
  });

  describe('DELETE /api/v1/raw_data/:id', () => {
    it('respond 404 if RawData does not exist', (done) => {
      request.delete('/api/v1/raw_data/i_am_not_exist')
        .set('Cookie', userCookie)
        .expect(404)
        .end((err, res) => {
          if (err) done(err);
          assert.deepStrictEqual(res.body.error, 'RawData not found');
          done();
        });
    });

    it('respond 200 with deleted RawData', (done) => {
      request.delete(`/api/v1/raw_data/${savedRawData.id}`)
        .set('Cookie', userCookie)
        .expect(200)
        .end((err, res) => {
          if (err) done(err);
          assert.strictEqual(res.body.data.name, raw_data.name);
          done();
        });
    });
  });
});
