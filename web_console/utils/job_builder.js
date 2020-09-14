/**
 * Common utility for Kubernetes job YAML generation
 *
 * Prerequisites:
 * - value of env must be string
 * - use `${var}` to simply transform var from number to string
 *
 * ref: https://kubernetes.io/docs/tasks/inject-data-application/
 */

const assert = require('assert');
const lodash = require('lodash');
const getConfig = require('./get_confg');

const { NAMESPACE, ES_HOST, ES_PORT } = getConfig({
  NAMESPACE: process.env.NAMESPACE,
  ES_HOST: process.env.ES_HOST,
  ES_PORT: process.env.ES_PORT,
});

function joinPath(base, ...rest) {
  const list = [base.replace(/\/$/, '')];

  rest.forEach((p) => {
    list.push(p.replace(/(^\/)|(\/$)/g, ''));
  });

  return list.join('/');
}

const permittedJobEnvs = {
  data_join: [
    'MIN_MATCHING_WINDOW', 'MAX_MATCHING_WINDOW',
    'DATA_BLOCK_DUMP_INTERVAL', 'DATA_BLOCK_DUMP_THRESHOLD',
    'EXAMPLE_ID_DUMP_INTERVAL', 'EXAMPLE_ID_DUMP_THRESHOLD',
  ],
  psi_data_join: [],
  tree_model: [
    'VERBOSITY', 'LEARNING_RATE', 'MAX_ITERS', 'MAX_DEPTH',
    'L2_REGULARIZATION', 'MAX_BINS', 'NUM_PARALELL',
    'VERIFY_EXAMPLE_IDS', 'USE_STREAMING',
  ],
  nn_model: [
    'MODEL_NAME', 'SAVE_CHECKPOINT_STEPS', 'SAVE_CHECKPOINT_SECS',
    'BATCH_SIZE', 'LEARNING_RATE'
  ],
};

function mergeCustomizer(obj, src, key) {
  if (key != 'containers' && lodash.isArray(obj) && lodash.isArray(src)) {
    return obj.concat(src);
  }
}

function mergeJson(obj, src) {
  return lodash.mergeWith(obj, src, mergeCustomizer);
}

/**
 * validate ticket and params, just throw error if validation failed
 *
 * @param {Object} ticket - a Ticket model instance
 * @param {Object} params - a JSON object
 * @return {boolean}
 */
function validateTicket(ticket, params) {
  return true;
}

function clientValidateJob(job, client_ticket, server_ticket) {
  return true;
}

// Only allow some fields to be used from job.server_params because
// it is received from peers and cannot be totally trusted.
function extractPermittedJobParams(job) {
  const params = job.server_params;
  const permitted_envs = permittedJobEnvs[job.job_type];
  const extracted = {};

  if (!params || !params.spec || !params.spec.flReplicaSpecs) {
    return extracted;
  }

  extracted.spec = { flReplicaSpecs: {} };

  for (const key in params.spec.flReplicaSpecs) {
    const obj = extracted.spec.flReplicaSpecs[key] = {};
    const src = params.spec.flReplicaSpecs[key];
    if (src.replicas) {
      obj.replicas = src.replicas;
    }
    if (src.template && src.template.spec
      && src.template.spec.containers) {
      obj.template = { spec: { containers: [{}] } };
      if (src.template.spec.containers[0].resources) {
        obj.template.spec.containers[0].resources = src.template.spec.containers[0].resources;
      }
      if (src.template.spec.containers
        && lodash.isArray(src.template.spec.containers[0].env)) {
        const obj_envs = obj.template.spec.containers[0].env = [];
        const src_envs = src.template.spec.containers[0].env;
        for (const i in src_envs) {
          const kv = src_envs[i];
          if (permitted_envs.includes(kv.name)
            && typeof (kv.value) === 'string') {
            obj_envs.push({
              name: kv.name,
              value: kv.value,
            });
          }
        }
      }
    }
  }

  return extracted;
}

function serverValidateJob(job, client_ticket, server_ticket) {
  const extracted = extractPermittedJobParams(job);
  assert.deepStrictEqual(job.server_params, extracted);
  return true;
}

function generateYaml(federation, job, job_params, ticket) {
  const { k8s_settings } = federation;

  let peer_spec = k8s_settings.leader_peer_spec;
  if (ticket.role == 'Follower') {
    peer_spec = k8s_settings.follower_peer_spec;
  }

  let yaml = {
    apiVersion: 'fedlearner.k8s.io/v1alpha1',
    kind: 'FLApp',
    metadata: {
      name: job.name,
      namespace: NAMESPACE,
    },
    spec: {
      role: ticket.role,
      cleanPodPolicy: 'All',
      peerSpecs: peer_spec,
    },
  };

  yaml = mergeJson(yaml, k8s_settings.global_job_spec);
  yaml = mergeJson(yaml, ticket.public_params);
  yaml = mergeJson(yaml, ticket.private_params);

  let output_base_dir;
  if (job.job_type == 'data_join' || job.job_type == 'psi_data_join') {
    output_base_dir = joinPath(
      k8s_settings.storage_root_path, 'data_source', job.name,
    );
  } else {
    output_base_dir = joinPath(
      k8s_settings.storage_root_path, 'job_output', job.name,
    );
  }

  const replica_specs = yaml.spec.flReplicaSpecs;
  for (const key in replica_specs) {
    let base_spec = {
      template: {
        spec: {
          restartPolicy: 'Never',
          containers: [{
            env: [
              { name: 'POD_IP', valueFrom: { fieldRef: { fieldPath: 'status.podIP' } } },
              { name: 'POD_NAME', valueFrom: { fieldRef: { fieldPath: 'metadata.name' } } },
              { name: 'ROLE', value: ticket.role.toLowerCase() },
              { name: 'APPLICATION_ID', value: job.name },
              { name: 'OUTPUT_BASE_DIR', value: output_base_dir },
              { name: 'CPU_REQUEST', valueFrom: { resourceFieldRef: { resource: 'requests.cpu' } } },
              { name: 'MEM_REQUEST', valueFrom: { resourceFieldRef: { resource: 'requests.memory' } } },
              { name: 'CPU_LIMIT', valueFrom: { resourceFieldRef: { resource: 'limits.cpu' } } },
              { name: 'MEM_LIMIT', valueFrom: { resourceFieldRef: { resource: 'limits.memory' } } },
              { name: 'ES_HOST', value: ES_HOST },
              { name: 'ES_PORT', value: `${ES_PORT}` },
            ],
            imagePullPolicy: 'IfNotPresent',
            name: 'tensorflow',
          }],
        },
      },
    };

    base_spec = mergeJson(base_spec, k8s_settings.global_replica_spec);
    replica_specs[key] = mergeJson(
      base_spec, replica_specs[key],
    );
  }

  yaml = mergeJson(yaml, job_params);

  return yaml;
}

function clientGenerateYaml(federation, job, client_ticket) {
  return generateYaml(federation, job, job.client_params, client_ticket);
}

/**
 * used for job creation at server-side
 *
 * @param {Object} federation - Federation instance
 * @param {Object} job - Job instance
 * @param {Object} server_ticket - Ticket instance
 * @return {Object} - a YAML object
 */
function serverGenerateYaml(federation, job, server_ticket) {
  return generateYaml(
    federation, job,
    extractPermittedJobParams(job),
    server_ticket,
  );
}

function portalGenerateYaml(federation, raw_data) {
  const { k8s_settings } = federation;

  let yaml = {
    apiVersion: 'fedlearner.k8s.io/v1alpha1',
    kind: 'FLApp',
    metadata: {
      name: raw_data.name,
      namespace: NAMESPACE,
    },
    spec: {
      role: 'Follower',
      peerSpecs: {
        Leader: {
          peerURL: '',
          authority: '',
        },
      },
    },
  };
  yaml = mergeJson(yaml, k8s_settings.global_job_spec);
  yaml = mergeJson(yaml, raw_data.context.yaml_spec);

  let master_spec = yaml.spec.flReplicaSpecs.Master;
  master_spec = mergeJson(master_spec, k8s_settings.global_replica_spec);

  master_spec = mergeJson(master_spec, {
    pair: false,
    replicas: 1,
    template: {
      spec: {
        restartPolicy: 'Never',
        containers: [{
          env: [
            { name: 'POD_IP', valueFrom: { fieldRef: { fieldPath: 'status.podIP' } } },
            { name: 'POD_NAME', valueFrom: { fieldRef: { fieldPath: 'metadata.name' } } },
            { name: 'ES_HOST', value: ES_HOST },
            { name: 'ES_PORT', value: `${ES_PORT}` },
            { name: 'APPLICATION_ID', value: raw_data.name },
            { name: 'DATA_PORTAL_NAME', value: raw_data.name },
            { name: 'OUTPUT_PARTITION_NUM', value: `${raw_data.output_partition_num}` },
            { name: 'INPUT_BASE_DIR', value: raw_data.input },
            { name: 'OUTPUT_BASE_DIR', value: joinPath(k8s_settings.storage_root_path, 'raw_data', raw_data.name) },
            { name: 'RAW_DATA_PUBLISH_DIR', value: joinPath('portal_publish_dir', raw_data.name) },
            { name: 'DATA_PORTAL_TYPE', value: raw_data.data_portal_type },
            { name: 'FILE_WILDCARD', value: raw_data.context.file_wildcard },
          ],
          imagePullPolicy: 'IfNotPresent',
          name: 'tensorflow',
        }],
      },
    },
  });

  let worker_spec = yaml.spec.flReplicaSpecs.Worker;
  worker_spec = mergeJson(worker_spec, k8s_settings.global_replica_spec);
  worker_spec = mergeJson(worker_spec, {
    pair: false,
    template: {
      spec: {
        restartPolicy: 'Never',
        containers: [{
          env: [
            { name: 'POD_IP', valueFrom: { fieldRef: { fieldPath: 'status.podIP' } } },
            { name: 'POD_NAME', valueFrom: { fieldRef: { fieldPath: 'metadata.name' } } },
            { name: 'CPU_REQUEST', valueFrom: { resourceFieldRef: { resource: 'requests.cpu' } } },
            { name: 'MEM_REQUEST', valueFrom: { resourceFieldRef: { resource: 'requests.memory' } } },
            { name: 'CPU_LIMIT', valueFrom: { resourceFieldRef: { resource: 'limits.cpu' } } },
            { name: 'MEM_LIMIT', valueFrom: { resourceFieldRef: { resource: 'limits.memory' } } },
            { name: 'ES_HOST', value: ES_HOST },
            { name: 'ES_PORT', value: `${ES_PORT}` },
            { name: 'APPLICATION_ID', value: raw_data.name },
            { name: 'BATCH_SIZE', value: raw_data.context.batch_size ? `${raw_data.context.batch_size}` : ""  },
            { name: 'INPUT_DATA_FORMAT', value: raw_data.context.input_data_format },
            { name: 'COMPRESSED_TYPE', value: raw_data.context.compressed_type },
            { name: 'OUTPUT_DATA_FORMAT', value: raw_data.context.output_data_format },
          ],
          imagePullPolicy: 'IfNotPresent',
          name: 'tensorflow',
        }],
      },
    },
  });

  return yaml;
}

module.exports = {
  validateTicket,
  clientValidateJob,
  serverValidateJob,
  clientGenerateYaml,
  serverGenerateYaml,
  portalGenerateYaml,
};
