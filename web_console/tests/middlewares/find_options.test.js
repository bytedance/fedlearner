const assert = require('assert');
const supertest = require('supertest');
const server = require('../fixtures/server');

const request = supertest(server.callback());

describe('FindOptionsMiddleware', () => {
  it('generate blank object default', (done) => {
    request.get('/find')
      .expect(200)
      .end((err, res) => {
        if (err) done(err);
        assert.deepStrictEqual(res.body, {});
        done();
      });
  });

  it('respond 400 for illegal X-Federation-Id header', (done) => {
    request.get('/find')
      .set('X-Federation-Id', 'xxx')
      .expect(400)
      .end((err, res) => {
        if (err) done(err);
        assert.deepStrictEqual(res.body.error, 'Invalid header: X-Federation-Id');
        done();
      });
  });

  it('generate object with where for legal X-Federation-Id header', (done) => {
    request.get('/find')
      .set('X-Federation-Id', 1)
      .expect(200)
      .end((err, res) => {
        if (err) done(err);
        assert.deepStrictEqual(res.body, { where: { federation_id: 1 } });
        done();
      });
  });
});
