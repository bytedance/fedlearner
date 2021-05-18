import json
import logging
import yaml
import os
from string import Template

import flatten_dict

from tensorflow.compat.v1 import gfile
from fedlearner.data_join.raw_data.common import Constants


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


class _DictConfig(object):
    def __init__(self, attr):
        self._attr = attr

    def as_dict(self):
        return self._attr


class SparkFileConfig(_DictConfig):
    def __init__(self, entry_file, config_file, dep_file=None):
        attr = dict()
        attr["entry_file"] = entry_file
        attr["config_file"] = config_file
        attr["dep_file"] = dep_file
        super(SparkFileConfig, self).__init__(attr)


class SparkDriverConfig(_DictConfig):
    def __init__(self, cores, memory):
        attr = dict()
        attr["cores"] = cores
        attr["memory"] = memory
        super(SparkDriverConfig, self).__init__(attr)


class SparkExecutorConfig(_DictConfig):
    def __init__(self, cores, memory, instances):
        attr = dict()
        attr["cores"] = cores
        attr["memory"] = memory
        attr["instances"] = instances
        super(SparkExecutorConfig, self).__init__(attr)


class _YamlTemplate(Template):
    delimiter = '$'
    # Which placeholders in the template should be interpreted
    idpattern = r'[a-zA-Z_\-\[0-9\]]+(\.[a-zA-Z_\-\[0-9\]]+)*'


def format_yaml(yaml, **kwargs):
    """Formats a yaml template.

    Example usage:
        format_yaml('{"abc": ${x.y}}', x={'y': 123})
    output should be  '{"abc": 123}'
    """
    template = _YamlTemplate(yaml)
    print(kwargs)
    try:
        return template.substitute(flatten_dict.flatten(kwargs or {},
                                                        reducer='dot'))
    except KeyError as e:
        raise RuntimeError(
            'Unknown placeholder: {}'.format(e.args[0])) from e


class SparkTaskConfig(object):
    @staticmethod
    def task_json(task_name, file_config,
                  driver_config, executor_config):
        yaml_template = """
apiVersion: "sparkoperator.k8s.io/v1beta2"
kind: SparkApplication
metadata:
  name: ${task_name}
  namespace: fedlearner
  labels:
    psm: data.aml.fl
    owner: zhaopeng.1991
spec:
  type: Python
  pythonVersion: "3"
  mode: cluster
  image: hub.byted.org/fedlearner/fedlearner_dataflow:334b53906c2be09becd98c5489ba3c9e
  imagePullPolicy: Always
  mainApplicationFile: ${file_config.entry_file}
  arguments:
    - --config
    - ${file_config.config_file}
  deps:
    pyFiles: ["${file_config.dep_file}"]
  sparkVersion: "3.0.0"
  restartPolicy:
    type: Never
  dynamicAllocation:
    enabled: false
  volumes:
    - name: "spark-deploy"
      hostPath:
        path: "/opt/tiger/spark_deploy"
        type: Directory
    - name: "yarn-deploy"
      hostPath:
        path: "/opt/tiger/yarn_deploy"
        type: Directory
  driver:
    cores: ${driver_config.cores}
    memory: "${driver_config.memory}"
    labels:
      version: 3.0.0
    serviceAccount: spark
    volumeMounts:
      - name: "spark-deploy"
        mountPath: "/opt/tiger/spark_deploy"
        readOnly: true
      - name: "yarn-deploy"
        mountPath: "/opt/tiger/yarn_deploy"
        readOnly: true
  executor:
    cores: ${executor_config.cores}
    instances: ${executor_config.instances}
    memory: "${executor_config.memory}"
    labels:
      version: 3.0.0
    volumeMounts:
      - name: "spark-deploy"
        mountPath: "/opt/tiger/spark_deploy"
        readOnly: true
      - name: "yarn-deploy"
        mountPath: "/opt/tiger/yarn_deploy"
        readOnly: true
        """
        yaml_config = format_yaml(yaml_template,
                                  task_name=task_name,
                                  file_config=file_config.as_dict(),
                                  driver_config=driver_config.as_dict(),
                                  executor_config=executor_config.as_dict())
        print(yaml_config)
        try:
            config = yaml.safe_load(yaml_config)
            return config
        except Exception as e:  # pylint: disable=broad-except
            logging.error("Invalid spark config, %s", str(e))
            exit(-1)
