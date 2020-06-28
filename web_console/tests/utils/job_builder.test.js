const assert = require('assert');
const path = require('path');
const { loadYaml } = require('../../utils/yaml');
const { readFileSync } = require('../../utils');
const { serverGenerateYaml } = require('../../utils/job_builder');
const testRoleConfig = require('../fixtures/test_role.json');

const testTrainYaml = readFileSync(
  path.resolve(__dirname, '..', 'fixtures', 'test_train.yaml'),
  { encoding: 'utf-8' },
);

describe('serverGenerateYaml', () => {
  it('should generate train yaml', () => {
    let federation = {
      k8s_settings: {
        namespace: "default",
        global_job_spec: {
            apiVersion: "fedlearner.k8s.io/v1alpha1",
            kind: "FLApp",
            spec: {
              cleanPodPolicy: "None",
            },
        },
        global_replica_spec: {
          template: {
            spec: {
              restartPolicy: "Never",
              volumes: [{"hostPath": {"path": "/data"}, "name": "data"}],
              containers: {
                env: [
                  { "name": "POD_IP", "value": { "valueFrom": { "fieldRef": { "fieldPath": "status.podIP" } } } },
                  { "name": "POD_NAME", "value": { "valueFrom": { "fieldRef": { "fieldPath": "metadata.name" } } } }
                ],
                imagePullPolicy: "IfNotPresent",
                volumeMounts: [{ "mountPath": "/data", "name": "data" }],
                name: "tensorflow",
              }
            },
          }
        },
      },
    };

    let job = {
      name: "application_id",
    };

    let ticket = {
      role: "leader",
      public_params: null,
      private_params: {
        spec: {
          flReplicaSpecs: {
            Master: {
              pair: false,
              replicas: 1,
              template: {
                spec: {
                  containers: {
                    env: [
                      {name: "MODEL_NAME", value: "fedlearner_model"},
                      {name: "START_DATE", value: "2020041500"},
                      {name: "END_DATE", value: "2020041700"},
                    ],
                    image: "image_path",
                    ports: [
                      {containerPort: 50051, name: "flapp-port"},
                    ],
                    resources: {
                      limits: {
                        cpu: "4000m",
                        memory: "4Gi",
                      },
                      requests: {
                        cpu: "4000m",
                        memory: "4Gi",
                      },
                    },
                    command: ["/app/fedlearner_byted/deploy/scripts/trainer/run_customed_trainer_master.sh"],
                    args: [],
                  },
                },
              },
            },
            PS: {
              pair: false,
              replicas: 1,
              template: {
                spec: {
                  containers: {
                    env: [
                      {name: "MODEL_NAME", value: "fedlearner_model"},
                    ],
                    image: "image_path",
                    ports: [
                      {containerPort: 50051, name: "flapp-port"},
                    ],
                    resources: {
                      limits: {
                        cpu: "4000m",
                        memory: "4Gi",
                      },
                      requests: {
                        cpu: "4000m",
                        memory: "4Gi",
                      },
                    },
                    command: ['/app/fedlearner_byted/deploy/scripts/trainer/run_trainer_ps.sh'],
                    args: [],
                  },
                },
              },
            },
            Worker: {
              pair: true,
              replicas: 1,
              template: {
                spec: {
                  containers: {
                    env: [
                      {name: "MODEL_NAME", value: "fedlearner_model"},
                    ],
                    image: "image_path",
                    ports: [
                      {containerPort: 50051, name: "flapp-port"},
                      {containerPort: 50052, name: "tf-port"},
                    ],
                    resources: {
                      limits: {
                        cpu: "4000m",
                        memory: "4Gi",
                      },
                      requests: {
                        cpu: "4000m",
                        memory: "4Gi",
                      },
                    },
                    command: ['/app/fedlearner_byted/deploy/scripts/wait4pair_wrapper.sh'],
                    args: ['/app/fedlearner_byted/deploy/scripts/trainer/run_trainer_worker.sh'],
                  },
                },
              },
            },
          },
        },
      },
    };

    assert.deepStrictEqual(
      serverGenerateYaml(federation, job, {}, ticket),
      loadYaml(testTrainYaml),
    );
  });
});
