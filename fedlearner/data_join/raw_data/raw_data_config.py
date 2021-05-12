import json
import os
from collections import namedtuple

from tensorflow.compat.v1 import gfile
from fedlearner.data_join.raw_data.raw_data import Constants


class RawDataJobConfig(object):
    def __init__(self, config_path, job_id):
        name_format = "raw_data_{}.config"
        self._config_path = os.path.join(config_path,
                                         name_format.format(job_id))

    @property
    def config_path(self):
        return self._config_path

    def data_block_config(self,
                          input_files,
                          output_path,
                          output_type,
                          compression_type,
                          data_block_threshold=0):
        config_dict = {
            Constants.input_files_key: ",".join(input_files),
            Constants.output_type_key: output_type,
            Constants.output_path_key: output_path,
            Constants.compression_type_key: compression_type,
            Constants.data_block_threshold_key: data_block_threshold,
        }
        with gfile.Open(self._config_path, 'w') as f:
            f.write(json.dumps(config_dict))

    def raw_data_config(self,
                        input_files,
                        schema_file_path,
                        job_type,
                        output_type,
                        output_partition_num,
                        output_path,
                        compression_type):
        config_dict = {
            Constants.job_type_key: job_type,
            Constants.input_files_key: ",".join(input_files),
            Constants.schema_path_key: schema_file_path,
            Constants.output_type_key: output_type,
            Constants.output_partition_num_key: output_partition_num,
            Constants.output_path_key: output_path,
            Constants.compression_type_key: compression_type,
        }
        with gfile.Open(self._config_path, 'w') as f:
            f.write(json.dumps(config_dict))


SparkFileConfig = namedtuple('SparkFileConfig',
                             ['entry_file', 'config_file', 'dep_file'])

SparkMasterConfig = namedtuple('SparkMasterConfig',
                               ['cores', 'memory'])
SparkWorkerConfig = namedtuple('SparkWorkerConfig',
                               ['cores', 'memory', 'instances'])


class SparkTaskConfig(object):
    @staticmethod
    def task_json(task_name, file_config,
                  master_config, worker_config):
        volume_mounts = [{
            "name": "spark-deploy",
            "hostPath": {"path": "/opt/tiger/spark_deploy",
                         "type": "Directory"},
            "readOnly": True
        }, {
            "name": "yarn-deploy",
            "hostPath": {"path": "/opt/tiger/yarn_deploy",
                         "type": "Directory"},
            "readOnly": True
        }]

        config_dict = {
            "apiVersion": "sparkoperator.k8s.io/v1beta2",
            "kind": "SparkApplication",
            "metadata": {
                "name": task_name,
                "namespace": "fedlearner",
                "labels": {
                    "psm": "data.aml.fl",
                    "owner": "zhaopeng.1991",
                }
            },
            "spec": {
                "type": "Python",
                "pythonVersion": "3",
                "mode": "cluster",
                "image": "hub.byted.org/fedlearner/fedlearner_dataflow:3b71e5d25fe826dc702e7ef46b17e2b1",  # pylint:
                "imagePullPolicy": "Always",
                "mainApplicationFile": file_config.entry_file,
                "arguments": ["--config", file_config.config_file],
                "deps": {"pyFiles": file_config.dep_file},
                "sparkVersion": "3.0.0",
                "restartPolicy": {"type": "Never"},
                "dynamicAllocation": {"enabled": False},
                "volumes": [{
                        "name": "spark-deploy",
                        "hostPath": {"path": "/opt/tiger/spark_deploy",
                                     "type": "Directory"}
                    }, {
                        "name": "yarn-deploy",
                        "hostPath": {"path": "/opt/tiger/yarn_deploy",
                                     "type": "Directory"}
                    }
                ],
                "driver": {
                    "cores": master_config.cores,
                    "coreLimit": "{}m".format(master_config.cores * 1000),
                    "memory": master_config.memory,
                    "labels": {"version": "3.0.0"},
                    "serviceAccount": "spark",
                    "volumeMounts": volume_mounts
                },
                "executor": {
                    "cores": worker_config.cores,
                    "memory": worker_config.memory,
                    "instances": worker_config.instances,
                    "labels": {"version": "3.0.0"},
                    "volumeMounts": volume_mounts
                }
            },
        }
        return json.dumps(config_dict)
