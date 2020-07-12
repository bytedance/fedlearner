const assert = require('assert');
const path = require('path');
const { loadYaml } = require('../../utils/yaml');
const { readFileSync } = require('../../utils');
const { serverGenerateYaml, serverValidateJob, portalGenerateYaml } = require('../../utils/job_builder');
// const testRoleConfig = require('../fixtures/test_role.json');

const testTrainYaml = readFileSync(
  path.resolve(__dirname, '..', 'fixtures', 'test_train.yaml'),
  { encoding: 'utf-8' },
);

const testPortalYaml = readFileSync(
  path.resolve(__dirname, '..', 'fixtures', 'test_data_portal.yaml'),
  { encoding: 'utf-8' },
);

describe('serverGenerateYaml', () => {
  it('should generate train yaml', () => {
    const federation = {
      k8s_settings: {
        namespace: 'default',
        global_job_spec: {
          apiVersion: 'fedlearner.k8s.io/v1alpha1',
          kind: 'FLApp',
          metadata: {
            namespace: 'default',
          },
          spec: {
            cleanPodPolicy: 'None',
          },
        },
        global_replica_spec: {
          template: {
            spec: {
              restartPolicy: 'Never',
              volumes: [{ hostPath: { path: '/data' }, name: 'data' }],
              containers: [{
                env: [
                  { name: 'POD_IP', value: { valueFrom: { fieldRef: { fieldPath: 'status.podIP' } } } },
                  { name: 'POD_NAME', value: { valueFrom: { fieldRef: { fieldPath: 'metadata.name' } } } },
                ],
                imagePullPolicy: 'IfNotPresent',
                volumeMounts: [{ mountPath: '/data', name: 'data' }],
                name: 'tensorflow',
              }],
            },
          },
        },
        leader_peer_spec: {
          Follower: {
            peerURL: 'fedlearner-stack-ingress-nginx-controller.default.svc.cluster.local:80',
            authority: 'follower.flapp.operator',
            extraHeaders: {
              'x-host': 'follower.flapp.operator',
            },
          },
        },
      },
    };

    const job = {
      name: 'application_id',
      job_type: 'nn_model',
      server_params: {
        spec: {
          flReplicaSpecs: {
            Master: {
              replicas: 1,
              template: {
                spec: {
                  containers: [{
                    env: [
                      { name: 'MODEL_NAME', value: 'fedlearner_model' },
                    ],
                    resources: {
                      limits: {
                        cpu: '4000m',
                        memory: '4Gi',
                      },
                      requests: {
                        cpu: '4000m',
                        memory: '4Gi',
                      },
                    },
                  }],
                },
              },
            },
            PS: {
              replicas: 1,
              template: {
                spec: {
                  containers: [{
                    env: [
                      { name: 'MODEL_NAME', value: 'fedlearner_model' },
                    ],
                    resources: {
                      limits: {
                        cpu: '4000m',
                        memory: '4Gi',
                      },
                      requests: {
                        cpu: '4000m',
                        memory: '4Gi',
                      },
                    },
                  }],
                },
              },
            },
            Worker: {
              replicas: 1,
              template: {
                spec: {
                  containers: [{
                    env: [
                      { name: 'MODEL_NAME', value: 'fedlearner_model' },
                    ],
                    resources: {
                      limits: {
                        cpu: '4000m',
                        memory: '4Gi',
                      },
                      requests: {
                        cpu: '4000m',
                        memory: '4Gi',
                      },
                    },
                  }],
                },
              },
            },
          },
        },
      },
    };

    const ticket = {
      role: 'leader',
      public_params: null,
      private_params: {
        spec: {
          flReplicaSpecs: {
            Master: {
              pair: false,
              template: {
                spec: {
                  containers: [{
                    env: [
                      { name: 'START_DATE', value: '2020041500' },
                      { name: 'END_DATE', value: '2020041700' },
                    ],
                    image: 'image_path',
                    ports: [
                      { containerPort: 50051, name: 'flapp-port' },
                    ],
                    command: ['/app/fedlearner_byted/deploy/scripts/trainer/run_customed_trainer_master.sh'],
                    args: [],
                  }],
                },
              },
            },
            PS: {
              pair: false,
              replicas: 1,
              template: {
                spec: {
                  containers: [{
                    image: 'image_path',
                    ports: [
                      { containerPort: 50051, name: 'flapp-port' },
                    ],
                    command: ['/app/fedlearner_byted/deploy/scripts/trainer/run_trainer_ps.sh'],
                    args: [],
                  }],
                },
              },
            },
            Worker: {
              pair: true,
              replicas: 1,
              template: {
                spec: {
                  containers: [{
                    image: 'image_path',
                    ports: [
                      { containerPort: 50051, name: 'flapp-port' },
                      { containerPort: 50052, name: 'tf-port' },
                    ],
                    command: ['/app/fedlearner_byted/deploy/scripts/wait4pair_wrapper.sh'],
                    args: ['/app/fedlearner_byted/deploy/scripts/trainer/run_trainer_worker.sh'],
                  }],
                },
              },
            },
          },
        },
      },
    };

    assert.ok(serverValidateJob(job, {}, ticket));

    assert.deepStrictEqual(
      serverGenerateYaml(federation, job, {}, ticket),
      loadYaml(testTrainYaml),
    );
  });
});

describe('portalGenerateYaml', () => {
  it('should generate portal yaml', () => {
    const federation = {
      k8s_settings: {
        namespace: 'default',
        global_job_spec: {
          apiVersion: 'fedlearner.k8s.io/v1alpha1',
          kind: 'FLApp',
          metadata: {
            namespace: 'default',
          },
          spec: {
            cleanPodPolicy: 'None',
          },
        },
        global_replica_spec: {
          template: {
            spec: {
              restartPolicy: 'Never',
              volumes: [{ hostPath: { path: '/data' }, name: 'data' }],
              containers: {
                env: [
                  { name: 'POD_IP', value: { valueFrom: { fieldRef: { fieldPath: 'status.podIP' } } } },
                  { name: 'POD_NAME', value: { valueFrom: { fieldRef: { fieldPath: 'metadata.name' } } } },
                ],
                imagePullPolicy: 'IfNotPresent',
                volumeMounts: [{ mountPath: '/data', name: 'data' }],
                name: 'tensorflow',
              },
            },
          },
        },
        peer_spec: {
          Follower: {
            peerURL: '',
            authority: '',
          },
        },
      },
    };

    const raw_data = {
      name: 'test_raw_data',
      output_partition_num: 8,
      data_portal_type: 'Streaming',
      input: '/data/portal_input',
      output: '/data/portal_output',
      context: {
        file_wildcard: '*.rd',
        batch_size: 1024,
        max_flying_item: 300000,
        merge_buffer_size: 4096,
        write_buffer_size: 10000000,
        input_data_format: 'TF_RECORD',
        compressed_type: 'ZLIB',
        yaml_spec: {
          spec: {
            role: 'Leader',
            flReplicaSpecs: {
              Master: {
                template: {
                  spec: {
                    containers: {
                      resources: {
                        limits: {
                          cpu: '2000m',
                          memory: '2Gi',
                        },
                        requests: {
                          cpu: '2000m',
                          memory: '2Gi',
                        },
                      },
                      image: 'image_path',
                      ports: [
                        { containerPort: 50051, name: 'flapp-port' },
                      ],
                      command: ['/app/fedlearner/deploy/scripts/data_portal/run_data_portal_master.sh'],
                      args: [],
                    },
                  },
                },
              },
              PS: {},
              Worker: {
                replicas: 2,
                template: {
                  spec: {
                    containers: {
                      resources: {
                        limits: {
                          cpu: '2000m',
                          memory: '4Gi',
                        },
                        requests: {
                          cpu: '2000m',
                          memory: '4Gi',
                        },
                      },
                      image: 'image_path',
                      command: ['/app/fedlearner/deploy/scripts/data_portal/run_data_portal_worker.sh'],
                      args: [],
                    },
                  },
                },
              },
            },
          },
        },
      },
    };

    assert.deepStrictEqual(
      portalGenerateYaml(federation, raw_data),
      loadYaml(testPortalYaml),
    );
  });
});
