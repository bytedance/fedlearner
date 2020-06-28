const getConfig = require('./get_confg');

const server_config = getConfig();

function roleConfig(config, public_env = {}, public_volume = {}) {
    let role = {
        "pair": config.pair,
        "replicas": config.replicas,
        "template": {
            "spec": {
                "restartPolicy": "Never",
                "volumes": [],
                "containers": {
                    "env": [
                        { "name": "POD_IP", "value": { "valueFrom": { "fieldRef": { "fieldPath": "status.podIP" } } } },
                        { "name": "POD_NAME", "value": { "valueFrom": { "fieldRef": { "fieldPath": "metadata.name" } } } }],
                    "image": config.image,
                    "imagePullPolicy": "IfNotPresent",
                    "volumeMounts": [],
                    "name": "tensorflow",
                    "ports": config.ports,
                    "resources": { "limits": { "cpu": config.cpu, "memory": config.memory }, "requests": { "cpu": config.cpu, "memory": config.memory } },
                    "command": config.command,
                    "args": config.args
                },
            }
        }
    }

    for (var key in public_env) {
        role["template"]["spec"]["containers"]["env"].push({ "name": key, "value": public_env[key] })
    }

    for (var key in config.env) {
        role["template"]["spec"]["containers"]["env"].push({ "name": key, "value": config.env[key] })
    }

    for (var key in public_volume) {
        role["template"]["spec"]["volumes"].push({ "hostPath": { "path": public_volume[key] }, "name": key })
        role["template"]["spec"]["containers"]["volumeMounts"].push({ "mountPath": public_volume[key], "name": key })
    }
    return role
}

function trainConfig(job) {
    let job_config = {
        "apiVersion": server_config.API_VERSION,
        "kind": server_config.KIND,
        "metadata": {
            "namespace": server_config.NAMESPACE,
            "name": job.application_id
        },
        "spec": {
            "flReplicaSpecs": {},
            "role": job.role,
            "cleanPodPolicy": "None",
            "peerSpecs": {
                [job.peer_role]: {
                    "peerURL": job.peer_url,
                    "authority": job.peer_authority,
                    "extraHeaders": {
                        "x-host": job.x_host
                    }
                }
            }
        },
    }

    job_config["spec"]["flReplicaSpecs"]["Master"] = roleConfig(
        job.master_config,
        job.public_env,
        job.public_volume)
    job_config["spec"]["flReplicaSpecs"]["PS"] = roleConfig(
        job.ps_config,
        job.public_env,
        job.public_volume)
    job_config["spec"]["flReplicaSpecs"]["Worker"] = roleConfig(
        job.worker_config,
        job.public_env,
        job.public_volume)

    return job_config;
}

module.exports = {
    roleConfig,
    trainConfig,
};