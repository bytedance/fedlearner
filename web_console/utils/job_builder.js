const lodash = require('lodash');
const getConfig = require('./get_confg');

const server_config = getConfig();

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

function serverValidateJob(job, client_ticket, server_ticket) {
  // for now we don't allow client to submit params to server;
  if (job.server_params != "") return false;
  return true;
}

function generateYaml(federation, job, ticket) {
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

  return yaml;
}

function clientGenerateYaml(federation, job, client_ticket, server_ticket) {
  return generateYaml(federation, job, client_ticket);
}

function serverGenerateYaml(federation, job, client_ticket, server_ticket) {
  return generateYaml(federation, job, server_ticket);
}

module.exports = {
  validateTicket,
  clientValidateJob,
  serverValidateJob,
  clientGenerateYaml,
  serverGenerateYaml
};