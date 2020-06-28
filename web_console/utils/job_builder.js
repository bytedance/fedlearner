const lodash = require('lodash');
const assert = require('assert');
const getConfig = require('./get_confg');

const server_config = getConfig();

const permittedJobEnvs = {
  data_join: [],
  psi_data_join: [],
  tree_model: [],
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

function validateTicket(ticket) {
  return true;
}


function clientValidateJob(job, client_ticket, server_ticket) {
  return true;
}

// Only allow some fields to be used from job.server_params because
// it is received from peers and cannot be totally trusted.
function extractPermittedJobParams(job) {
  let params = job.server_params;
  let permitted_envs = permittedJobEnvs[job.job_type];
  let extracted = {};

  if (!params || !params.spec || !params.spec.flReplicaSpecs) {
    return extracted;
  }

  extracted.spec = { flReplicaSpecs: {} };

  for (let key in params.spec.flReplicaSpecs) {
    let obj = extracted.spec.flReplicaSpecs[key] = {};
    let src = params.spec.flReplicaSpecs[key];
    if (!src.replicas) {
      obj.replicas = src.replicas;
    }
    if (src.template && src.template.spec &&
        src.template.spec.containers) {
      obj.template = { spec: { containers: {} } };
      if (src.template.spec.containers.resources) {
        obj.template.spec.containers.resources =
            src.template.spec.containers.resources;
      }
      if (src.template.spec.containers &&
          lodash.isArray(src.template.spec.containers.env)) {
        let obj_envs = obj.template.spec.containers.env = [];
        let src_envs = src.template.spec.containers.env;
        for (let i in src_envs) {
          let kv = src_envs[i];
          if (permitted_envs.includes(kv.name) &&
              typeof(kv.value) == 'string') {
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
  let extracted = extractPermittedJobParams(job);
  assert.deepStrictEqual(job.server_params, extracted);
  return true;
}

function generateYaml(federation, job, job_params, ticket) {
  let k8s_settings = federation.k8s_settings;
  let yaml = mergeJson({}, k8s_settings.global_job_spec);

  let peer_role = 'follower';
  let cap_peer_role = 'Follower';
  if (ticket.role == 'follower') {
    peer_role = 'leader';
    cap_peer_role = 'Leader';
  }
  yaml = mergeJson(yaml, {
    metadata: {
      name: job.name,
      namespace: k8s_settings['namespace'],
    },
    spec: {
      role: ticket.role,
      cleanPodPolicy: "None",
      peerSpecs: {
        [cap_peer_role]: {
          peerURL: 'fedlearner-stack-ingress-nginx-controller.' + k8s_settings['namespace'] + '.svc.cluster.local:80',
          authority: peer_role + ".flapp.operator",
          extraHeaders: {
            "x-host": peer_role + ".flapp.operator",
          }
        },
      },
    }
  });
  yaml = mergeJson(yaml, ticket.public_params);
  yaml = mergeJson(yaml, ticket.private_params);

  let replica_specs = yaml["spec"]["flReplicaSpecs"];
  for (let key in replica_specs) {
    let base_spec = mergeJson({}, k8s_settings.global_replica_spec);
    base_spec = mergeJson(base_spec, {
      template: {
        spec: {
          containers: {
            env: [
              {name: "ROLE", value: ticket.role},
              {name: "APPLICATION_ID", value: job.name},
            ]
          }
        },
      },
    });
    replica_specs[key] = mergeJson(
      base_spec, replica_specs[key]);
  }

  yaml = mergeJson(yaml, job_params);

  return yaml;
}

function clientGenerateYaml(federation, job, client_ticket, server_ticket) {
  return generateYaml(federation, job, job.client_params, client_ticket);
}

function serverGenerateYaml(federation, job, client_ticket, server_ticket) {
  return generateYaml(
    federation, job,
    extractPermittedJobParams(job),
    server_ticket);
}

module.exports = {
  validateTicket,
  clientValidateJob,
  serverValidateJob,
  clientGenerateYaml,
  serverGenerateYaml
};