const assert = require('assert');
const { roleConfig, trainConfig } = require('../../utils/job_builder');


describe('roleConfig', () => {
    it('should generate role config', () => {
        console.log(roleConfig(
            {
                "pair": true, 
                "replicas": 1,
                "image": "image_path",
                "ports": "ports",
                "cpu": 1,
                "memory": 4,
                "command": ["command"],
                "args": []
            }))
    });
});


describe('trainConfig', () => {
    it('should generate train config', () => {
        console.log(trainConfig({
            "application_id": "application_id",
            "role": "leader",
            "peer_role": "Follower",
            "peer_url": "ingress-nginx.ingress-nginx.svc.cluster.local:80",
            "peer_authority": "follower.flapp.operator",
            "x_host": "follower.flapp.operator",
            "public_env": {
                "ROLE": "leader",
                "APPLICATION_ID": "application_id",
                "MODEL_NAME": "fedlearner_model"
            },
            "public_volume": {
                "data": "/data"
            },
            "master_config": {
                "pair": false,
                "replicas": 1,
                "image": "image_path",
                "env": {
                    "START_DATE": "2020041500",
                    "END_DATE": "2020041700"
                },
                "command": ["/opt/tiger/fedlearner_byted/deploy/scripts/trainer/run_customed_trainer_master.sh"],
                "args": []
            },
            "ps_config": {
                "pair": false,
                "replicas": 1,
                "image": "image_path",
                "env": {},
                "command": ["/opt/tiger/fedlearner_byted/deploy/scripts/trainer/run_trainer_ps.sh"],
                "args": []
            },
            "worker_config": {
                "pair": true,
                "replicas": 1,
                "image": "image_path",
                "env": {},
                "command": ["/opt/tiger/fedlearner_byted/deploy/scripts/wait4pair_wrapper.sh"],
                "args": ["/opt/tiger/fedlearner_byted/deploy/scripts/trainer/run_trainer_worker.sh"]
            }
        }))
    });
});
