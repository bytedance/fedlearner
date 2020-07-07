/**
 * for debugging with this client, just set environment variables by:
 * ```
 * export GRPC_TRACE=all
 * export GRPC_VERBOSITY=DEBUG
 * ```
 */
const path = require('path');
const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
// const { readFileSync } = require('../utils');
const getConfig = require('../utils/get_confg');

const config = getConfig({
  GRPC_CA: process.env.GRPC_CA,
  GRPC_KEY: process.env.GRPC_KEY,
  GRPC_CERT: process.env.GRPC_CERT,
  GRPC_AUTHORITY: process.env.GRPC_AUTHORITY,
  GRPC_HOST: process.env.GRPC_HOST,
  GRPC_PORT: process.env.GRPC_PORT,
});
// const ca = readFileSync(config.GRPC_CA);

const packageDefinition = protoLoader.loadSync(
  path.resolve(__dirname, 'meta.proto'),
  {
    keepCase: true,
    longs: String,
    enums: String,
    defaults: true,
    oneofs: true,
  });
const pkg = grpc.loadPackageDefinition(packageDefinition);

class FederationClient {
  constructor(host, federation, fingerprint) {
    // TODO: use federation signature for production @peng09
    // this.channelCredentials = grpc.credentials.createSsl(ca);
    this.metadata = new grpc.Metadata();
    this.metadata.set('authority', config.GRPC_AUTHORITY);
    this.metadata.set('x-host', host);
    this.metadata.set('x-federation', federation);
    this.metadata.set('x-fingerprint', fingerprint);
    // this.callCredentials = grpc.credentials.createFromMetadataGenerator((options, callback) => {
    //   callback(null, this.metadata);
    // });
    this._client = new pkg.federation.Federation(
      `${config.GRPC_HOST}:${config.GRPC_PORT}`,
      // grpc.credentials.combineChannelCredentials(this.channelCredentials, this.callCredentials),
      grpc.credentials.createInsecure(),
    );
    this._request = (method, params) => new Promise((resolve, reject) => {
      this._client[method](params, this.metadata, (err, data) => {
        if (err) reject(err);
        resolve(data);
      });
    });
  }

  // Protobuf limit: `job_type` must be a string
  getTickets(params = { job_type: '', role: 'leader', offset: 0, limit: 10 }) {
    return this._request('getTickets', params);
  }

  createJob(params) {
    return this._request('createJob', params);
  }

  deleteJob(params) {
    return this._request('deleteJob', params);
  }
}

module.exports = FederationClient;
