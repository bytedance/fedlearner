const assert = require('assert');
const path = require('path');
const { loadYaml } = require('../../utils/yaml');
const { readFileSync } = require('../../utils');
const { roleConfig, trainConfig } = require('../../utils/job_builder');
const testRoleConfig = require('../fixtures/test_role.json');

const testTrainYaml = readFileSync(
    path.resolve(__dirname, '..', 'fixtures', 'test_train.yaml'),
    { encoding: 'utf-8' },
);

describe('roleConfig', () => {
    it('should generate role config', () => {
        assert.deepStrictEqual(
            roleConfig(
                {
                    "pair": true,
                    "replicas": 1,
                    "image": "image_path",
                    "ports": [
                        {
                            "containerPort": 50051,
                            "name": "flapp-port"
                        },
                        {
                            "containerPort": 50052,
                            "name": "tf-port"
                        }
                    ],
                    "cpu": "4000m",
                    "memory": "4Gi",
                    "command": ["command"],
                    "args": []
                },
                {
                    "ROLE": "leader",
                    "APPLICATION_ID": "application_id",
                    "MODEL_NAME": "fedlearner_model"
                },
                {
                    "data": "/data"
                }
            ), testRoleConfig)
    });
});

describe('trainConfig', () => {
    it('should generate train config', () => {
        assert.deepStrictEqual(
            trainConfig({
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
                    "ports": [
                        {
                            "containerPort": 50051,
                            "name": "flapp-port"
                        }
                    ],
                    "cpu": "4000m",
                    "memory": "4Gi",
                    "env": {
                        "START_DATE": "2020041500",
                        "END_DATE": "2020041700"
                    },
                    "command": ["/opt/tiger/fedlearner_byted/deploy/scripts/trainer/run_customed_trainer_master.sh"],
                    "args": []
                },
                "ps_config": {
                    "pair": false,
                    "ports": [
                        {
                            "containerPort": 50051,
                            "name": "flapp-port"
                        }
                    ],
                    "cpu": "4000m",
                    "memory": "4Gi",
                    "replicas": 1,
                    "image": "image_path",
                    "env": {},
                    "command": ["/opt/tiger/fedlearner_byted/deploy/scripts/trainer/run_trainer_ps.sh"],
                    "args": []
                },
                "worker_config": {
                    "pair": true,
                    "ports": [
                        {
                            "containerPort": 50051,
                            "name": "flapp-port"
                        },
                        {
                            "containerPort": 50052,
                            "name": "tf-port"
                        }
                    ],
                    "cpu": "4000m",
                    "memory": "4Gi",
                    "replicas": 1,
                    "image": "image_path",
                    "env": {},
                    "command": ["/opt/tiger/fedlearner_byted/deploy/scripts/wait4pair_wrapper.sh"],
                    "args": ["/opt/tiger/fedlearner_byted/deploy/scripts/trainer/run_trainer_worker.sh"]
                }
            }),
            loadYaml(testTrainYaml))
    });
});
