/**
 * for debugging request, just set these environment variables:
 *
 * ```
 * export GRPC_TRACE=all
 * export GRPC_VERBOSITY=DEBUG
 * ```
 */
const path = require('path');
const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');

const packageDefinition = protoLoader.loadSync(
  path.resolve(__dirname, 'meta.proto'),
  {
    keepCase: true,
    longs: String,
    enums: String,
    defaults: true,
    oneofs: true,
  },
);
const pkg = grpc.loadPackageDefinition(packageDefinition);

class FederationClient {
  /**
   * options are maintained at `federations` table
   *
   * @param {Object} federation - Federation instance
   * @return {FederationClient}
   */
  constructor(federation) {
    const { peerURL, authority, extraHeaders } = federation.k8s_settings;
    this.metadata = new grpc.Metadata();
    Object.keys(extraHeaders).forEach((key) => {
      this.metadata.set(key, extraHeaders[key]);
    });
    this._client = new pkg.federation.Federation(
      peerURL,
      grpc.credentials.createInsecure(),
      // options defined at https://github.com/grpc/grpc/blob/master/include/grpc/impl/codegen/grpc_types.h
      {
        'grpc.default_authority': authority,
      },
    );
    this._request = (method, params) => new Promise((resolve, reject) => {
      this._client[method](params, this.metadata, (err, data) => {
        if (err) reject(err);
        resolve(data);
      });
    });
  }

  getTickets(params = { job_type: '', role: 'follower' }) {
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
