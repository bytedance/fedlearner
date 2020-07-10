const assert = require('assert');
const lodash = require('lodash');

const permittedJobEnvs = {
  data_join: [],
  psi_data_join: [],
  tree_model: [
    'VERBOSITY', 'LEARNING_RATE', 'MAX_ITERS', 'MAX_DEPTH',
    'L2_REGULARIZATION', 'MAX_BINS', 'NUM_PARALELL',
    'VERIFY_EXAMPLE_IDS', 'USE_STREAMING',
  ],
  nn_model: ['MODEL_NAME'],
};

function mergeCustomizer(obj, src) {
  if (lodash.isArray(obj) && lodash.isArray(src)) {
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
      obj.template = { spec: { containers: {} } };
      if (src.template.spec.containers.resources) {
        obj.template.spec.containers.resources = src.template.spec.containers.resources;
      }
      if (src.template.spec.containers
        && lodash.isArray(src.template.spec.containers.env)) {
        const obj_envs = obj.template.spec.containers.env = [];
        const src_envs = src.template.spec.containers.env;
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
  let yaml = mergeJson({}, k8s_settings.global_job_spec);

  let peer_spec = k8s_settings.leader_peer_spec;
  if (ticket.role == 'follower') {
    peer_spec = k8s_settings.follower_peer_spec;
  }
  yaml = mergeJson(yaml, {
    metadata: {
      name: job.name,
    },
    spec: {
      role: ticket.role,
      cleanPodPolicy: 'None',
      peerSpecs: peer_spec,
    },
  });

  yaml = mergeJson(yaml, ticket.public_params);
  yaml = mergeJson(yaml, ticket.private_params);

  const replica_specs = yaml.spec.flReplicaSpecs;
  for (const key in replica_specs) {
    let base_spec = mergeJson({}, k8s_settings.global_replica_spec);
    base_spec = mergeJson(base_spec, {
      template: {
        spec: {
          containers: {
            env: [
              { name: 'ROLE', value: ticket.role },
              { name: 'APPLICATION_ID', value: job.name },
            ],
          },
        },
      },
    });
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
  let k8s_settings = federation.k8s_settings;
  let yaml = mergeJson({}, k8s_settings.global_job_spec);

  let peer_spec = k8s_settings.peer_spec;
  yaml = mergeJson(yaml, {
    metadata: {
      name: raw_data.name,
    },
    spec: {
      role: ticket.role,
      cleanPodPolicy: "None",
      peerSpecs: peer_spec,
    },
  });

  yaml = mergeJson(yaml, raw_data.context.yaml_spec);

  let master_spec = yaml["spec"]["flReplicaSpecs"]['Master'];
  master_spec = mergeJson(master_spec, k8s_settings.global_replica_spec);
  let master_env_spec = mergeJson({}, {
    pair: false,
    replicas: 1,
    template: {
      spec: {
        containers: {
          env: [
            {name: "APPLICATION_ID", value: raw_data.name},
            {name: "OUTPUT_PARTITION_NUM", value: raw_data.output_partition_num},
            {name: "INPUT_BASE_DIR", value: raw_data.input+'/'+},
            {name: "OUTPUT_BASE_DIR", value: raw_data.output+'/'+raw_data.name},
            {name: "RAW_DATA_PUBLISH_DIR", value: raw_data.name},
            {name: "DATA_PORTAL_TYPE", value: raw_data.data_portal_type},
            {name: "FILE_WILDCARD", value: raw_data.context.file_wildcard},
          ],
        }
      },
    },
  });
  master_spec = mergeJson(master_spec. master_env_spec);

  let worker_spec = yaml["spec"]["flReplicaSpecs"]['Worker'];
  worker_spec = mergeJson(worker_spec, k8s_settings.global_replica_spec);
  let worker_env_spec = mergeJson({}, {
    pair: false,
    template: {
      spec: {
        containers: {
          env: [
            {name: "APPLICATION_ID", value: raw_data.name},
            {name: "BATCH_SIZE", value: raw_data.context.batch_size},
            {name: "MAX_FLYING_ITEM", value: raw_data.context.max_flying_item},
            {name: "MERGE_BUFFER_SIZE", value: raw_data.context.merge_buffer_size},
            {name: "WRITE_BUFFER_SIZE", value: raw_data.context.write_buffer_size},
            {name: "INPUT_DATA_FORMAT", value: raw_data.context.input_data_format},
            {name: "COMPRESSED_TYPE", value: raw_data.compressed_type},
          ],
        }
      },
    },
  });
  worker_spec = mergeJson(worker_spec. worker_env_spec);

  let ps_spec = yaml["spec"]["flReplicaSpecs"]['PS'];
  let ps_env_spec = mergeJson({}, {
    pair: false,
    replicas: 0,
  });
  ps_spec = mergeJson(ps_spec. ps_env_spec);

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
