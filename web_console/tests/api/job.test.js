const assert = require('assert');
const { Op } = require('sequelize');
const supertest = require('supertest');
const server = require('../fixtures/server');
const users = require('../fixtures/user');
const models = require('../../models');
const { test: job } = require('../fixtures/job');

const { Job, User } = models;
const request = supertest(server.callback());
let userCookie;
let pod;
let savedJob;

describe('Job System', () => {
  before(async () => {
    await models.sequelize.sync();
    const [record] = await User.findOrCreate({
      paranoid: false,
      where: {
        username: { [Op.eq]: users.user.username },
      },
      defaults: users.user,
    });
    if (record.deleted_at) {
      record.restore();
    }
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

  describe('POST /api/v1/job', () => {
    it('respond 400 if client_params is not json', (done) => {
      request.post('/api/v1/job')
        .set('Cookie', userCookie)
        .send({ ...job, client_params: 'string' })
        .expect(400)
        .end((err, res) => {
          if (err) done(err);
          assert.deepStrictEqual(res.body.error, 'client_params must be json');
          done();
        });
    });

    it('respond 400 if server_params is not json', (done) => {
      request.post('/api/v1/job')
        .set('Cookie', userCookie)
        .send({ ...job, server_params: 'string' })
        .expect(400)
        .end((err, res) => {
          if (err) done(err);
          assert.deepStrictEqual(res.body.error, 'server_params must be json');
          done();
        });
    });

    it('respond 422 if client_ticket does not exist', (done) => {
      request.post('/api/v1/job')
        .set('Cookie', userCookie)
        .send({ ...job, name: 'client_ticket_not_exist', client_ticket_name: 'client_ticket_not_exist' })
        .expect(422)
        .end((err, res) => {
          if (err) done(err);
          assert.deepStrictEqual(res.body.error, 'client_ticket does not exist');
          done();
        });
    });

    it('respond 400 if client_params validation failed', () => {
      // TODO: @piiswrong
    });

    it('respond 422 if job already exists', (done) => {
      request.post('/api/v1/job')
        .set('Cookie', userCookie)
        .send(job)
        .expect(422)
        .end((err, res) => {
          if (err) done(err);
          assert.deepStrictEqual(res.body.error, 'Job already exists');
          done();
        });
    });

    it('respond 200 with created job', () => {
      // TODO: depends on k8s cluster
    });
  });

  describe('GET /api/v1/jobs', () => {
    it('should return all jobs', (done) => {
      request.get('/api/v1/jobs')
        .set('Cookie', userCookie)
        .expect(200)
        .end((err, res) => {
          if (err) done(err);
          assert.ok(res.body.data.find((x) => x.localdata.name === job.name));
          done();
        });
    });
  });

  describe('GET /api/v1/job/:name', () => {
    it('respond 404 if job does not exist', (done) => {
      request.get('/api/v1/job/i_am_not_exist')
        .set('Cookie', userCookie)
        .expect(404)
        .end((err, res) => {
          if (err) done(err);
          assert.deepStrictEqual(res.body.error, 'Job not found');
          done();
        });
    });

    it('respond 200 with specific job', (done) => {
      request.get(`/api/v1/job/${job.name}`)
        .set('Cookie', userCookie)
        .expect(200)
        .end((err, res) => {
          if (err) done(err);
          assert.ok(res.body.data.localdata.name === job.name);
          assert.ok(res.body.data.metadata);
          savedJob = res.body.data;
          done();
        });
    });
  });

  describe('GET /api/v1/job/:k8s_name/pods', () => {
    it('respond 200 with pods', (done) => {
      request.get(`/api/v1/job/${savedJob.metadata.name}/pods`)
        .set('Cookie', userCookie)
        .expect(200)
        .end((err, res) => {
          if (err) done(err);
          assert.ok(Array.isArray(res.body.data));
          // eslint-disable-next-line prefer-destructuring
          pod = res.body.data[0];
          done();
        });
    });
  });

  describe('GET /api/v1/job/:k8s_name/logs', () => {
    it('respond 400 without start_time', (done) => {
      request.get(`/api/v1/job/${savedJob.metadata.name}/logs`)
        .set('Cookie', userCookie)
        .expect(400)
        .end((err, res) => {
          if (err) done(err);
          assert.deepStrictEqual(res.body.error, 'start_time is required');
          done();
        });
    });

    it('respond 200 with job log', (done) => {
      request.get(`/api/v1/job/${savedJob.metadata.name}/logs?start_time=${new Date(savedJob.metadata.creationTimestamp).getTime()}`)
        .set('Cookie', userCookie)
        .expect(200)
        .end((err, res) => {
          if (err) done(err);
          assert.ok(Array.isArray(res.body.data));
          done();
        });
    });
  });

  describe('GET /api/v1/job/pod/:pod_name/:container', () => {
    it('respond 200 with container info', (done) => {
      request.get(`/api/v1/job/pod/${pod.metadata.name}/${pod.status.containerStatuses[0].name}`)
        .set('Cookie', userCookie)
        .expect(200)
        .end((err, res) => {
          if (err) done(err);
          assert.ok(res.body.data.id);
          assert.ok(res.body.data.base);
          done();
        });
    });
  });

  describe('GET /api/v1/job/pod/:pod_name/logs', () => {
    it('respond 400 without start_time', (done) => {
      request.get(`/api/v1/job/pod/${pod.metadata.name}/logs`)
        .set('Cookie', userCookie)
        .expect(400)
        .end((err, res) => {
          if (err) done(err);
          assert.deepStrictEqual(res.body.error, 'start_time is required');
          done();
        });
    });

    it('respond 200 with pod log', (done) => {
      request.get(`/api/v1/job/pod/${pod.metadata.name}/logs?start_time=${new Date(pod.metadata.creationTimestamp).getTime()}`)
        .set('Cookie', userCookie)
        .expect(200)
        .end((err, res) => {
          if (err) done(err);
          assert.ok(Array.isArray(res.body.data));
          done();
        });
    });
  });

  describe('DELETE /api/v1/job/:name', () => {
    it('respond 404 if job does not exist', (done) => {
      request.delete('/api/v1/job/i_am_not_exist')
        .set('Cookie', userCookie)
        .expect(404)
        .end((err, res) => {
          if (err) done(err);
          assert.deepStrictEqual(res.body.error, 'Job not found');
          done();
        });
    });

    it('respond 200 with deleted job', (done) => {
      request.delete(`/api/v1/job/${job.name}`)
        .set('Cookie', userCookie)
        .expect(200)
        .end((err, res) => {
          if (err) done(err);
          assert.strictEqual(res.body.data.name, job.name);
          done();
        });
    });
  });
});
