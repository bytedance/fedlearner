const getConfig = require('./get_confg');

const server_config = getConfig();

function mergeJson(a, b) {
    a = Object.assign({}, a);
    for (key in b) {
        if (key in a && typeof(a[key]) == "object" &&
            typeof(b[key]) == "object") {
            a[key] = mergeJson(a[key], b[key]);
        } else {
            a[key] = b[key];
        }
    }
    return a;
}

function validateTicket(ticket) {
    return true;
}

function clientValidateJob(job, client_ticket, server_ticket) {
    return true;
}

function serverValidateJob(job, client_ticket, server_ticket) {
    return true;
}

function generateYaml(federation, job, ticket) {
    let yaml = {};
    yaml = mergeJson(yaml, JSON.parse(federation.global_job_spec));
    yaml = mergeJson(yaml, {
        "metadata": {
            "name": job.id,
        },
        "spec": {
            "role": ticket.role,
        }
    });
    yaml = mergeJson(yaml, ticket);

    replica_specs = yaml["spec"]["flReplicaSpecs"];
    global_replica_spec = JSON.parse(federation.global_replica_spec);
    for (key in global_replica_spec) {
        replica_specs[key] = mergeJson(
            global_replica_spec, replica_specs[key]);
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