# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

TEE_YAML_TEMPLATE = """{
    "apiVersion": "fedlearner.k8s.io/v1alpha1",
    "kind": "FedApp",
    "metadata": {
        "name": self.name,
        "namespace": system.variables.namespace,
        "labels": dict(system.variables.labels),
        "annotations": {
            "queue": "fedlearner",
            "schedulerName": "batch",
        },
    },
    "spec": {
        "activeDeadlineSeconds": 86400,
        "fedReplicaSpecs": {
            "Worker": {
                "mustSuccess": True,
                "port": {
                    "containerPort": 50051,
                    "name": "grpc-port",
                    "protocol": "TCP"
                },
                "template": {
                    "spec": {
                        "restartPolicy": "Never",
                        "containers": [
                            {
                                "name": "gene-analysis",
                                "image": str(system.variables.sgx_image),
                                "volumeMounts": list(system.variables.volume_mounts_list),
                                "command": [
                                    '/bin/bash'
                                ],
                                "args": [
                                    '/app/entrypoint.sh'
                                ],
                                "env": system.basic_envs_list + [
                                    {
                                        "name": "PROJECT_NAME",
                                        "value": str(self.variables.get("project_name", ""))
                                    },
                                    {
                                        "name": "DATA_ROLE",
                                        "value": str(self.variables.get("data_role", ""))
                                    },
                                    {
                                        "name": "TASK_TYPE",
                                        "value": str(self.variables.get("task_type", ""))
                                    },
                                    {
                                        "name": "INPUT_DATA_PATH",
                                        "value": str(self.variables.get("input_data_path", ""))
                                    },
                                    {
                                        "name": "OUTPUT_DATA_PATH",
                                        "value": str(self.variables.get("output_data_path", ""))
                                    },
                                    {
                                        "name": "EXPORT_DATA_PATH",
                                        "value": str(self.variables.get("export_data_path", ""))
                                    },
                                    {
                                        "name": "ALGORITHM_PATH",
                                        "value": str(self.variables.algorithm.path)
                                    },
                                    {
                                        "name": "ALGORITHM_PARAMETERS",
                                        "value": str(self.variables.algorithm.config)
                                    },
                                    {
                                        "name": "DOMAIN_NAME",
                                        "value": str(self.variables.get("domain_name", ""))
                                    },
                                    {
                                        "name": "ANALYZER_DOMAIN",
                                        "value": str(self.variables.get("analyzer_domain", ""))
                                    },
                                    {
                                        "name": "PROVIDERS_DOMAIN",
                                        "value": str(self.variables.get("providers_domain", ""))
                                    },
                                    {
                                        "name": "RECEIVER_DOMAIN",
                                        "value": str(self.variables.get("receiver_domain", ""))
                                    },
                                    {
                                        "name": "PCCS_URL",
                                        "value": str(self.variables.get("pccs_url", ""))
                                    },
                                    {
                                        "name": "RESULT_KEY",
                                        "value": str(self.variables.get("result_key", ""))
                                    }
                                ] + [],
                                "imagePullPolicy": "IfNotPresent",
                                "ports": [
                                    {
                                        "containerPort": 50051,
                                        "name": "grpc-port",
                                        "protocol": "TCP"
                                    }
                                ],
                                "resources": {
                                    "limits": {
                                        "cpu": self.variables.worker_cpu,
                                        "memory": self.variables.worker_mem
                                    } ,
                                    "requests": {
                                        "cpu": self.variables.worker_cpu,
                                        "memory": self.variables.worker_mem
                                    }
                                } if not self.variables.get("sgx_mem", "") else {
                                    "limits": {
                                        sgx_epc_mem": str(self.variables.sgx_mem),
                                        "cpu": self.variables.worker_cpu,
                                        "memory": self.variables.worker_mem
                                    } ,
                                    "requests": {
                                        "sgx_epc_mem": str(self.variables.sgx_mem),
                                        "cpu": self.variables.worker_cpu,
                                        "memory": self.variables.worker_mem
                                    }
                                }
                                
                            }
                        ],
                        "imagePullSecrets": [
                            {
                                "name": "regcred"
                            }
                        ],
                        "volumes": list(system.variables.volumes_list)
                    }
                },
                "replicas": self.variables.worker_replicas
            }
        }
    }
}"""
