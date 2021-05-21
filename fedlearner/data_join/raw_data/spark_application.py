import logging
import os
import sys
import time
from string import Template
import yaml

import flatten_dict

from fedlearner.data_join.raw_data.k8s_client import FakeK8SClient, K8SClient, \
    K8SAPPStatus


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
        super().__init__(attr)

    def entry_file(self):
        return self._attr['entry_file']

    def config_file(self):
        return self._attr['config_file']


class SparkDriverConfig(_DictConfig):
    def __init__(self, cores, memory):
        attr = dict()
        attr["cores"] = cores
        attr["memory"] = memory
        super().__init__(attr)


class SparkExecutorConfig(_DictConfig):
    def __init__(self, cores, memory, instances):
        attr = dict()
        attr["cores"] = cores
        attr["memory"] = memory
        attr["instances"] = instances
        super().__init__(attr)


class _YamlTemplate(Template):
    delimiter = '$'
    # Which placeholders in the template should be interpreted
    idpattern = r'[a-zA-Z_\-\[0-9\]]+(\.[a-zA-Z_\-\[0-9\]]+)*'


def format_yaml(yaml_str, **kwargs):
    """Formats a yaml template.

    Example usage:
        format_yaml('{"abc": ${x.y}}', x={'y': 123})
    output should be  '{"abc": 123}'
    """
    template = _YamlTemplate(yaml_str)
    try:
        return template.substitute(flatten_dict.flatten(kwargs or {},
                                                        reducer='dot'))
    except KeyError as e:
        raise RuntimeError(
            'Unknown placeholder: {}'.format(e.args[0])) from e


class SparkApplication(object):
    def __init__(self, name, file_config, driver_config, executor_config,
                 k8s_config_path=None,
                 use_fake_k8s=False):
        self._name = name
        if use_fake_k8s:
            self._config = self._local_task_config(name, file_config)
            self._k8s_client = FakeK8SClient()
        else:
            self._k8s_client = K8SClient()
            self._k8s_client.init(k8s_config_path)
            self._config = self._task_config(
                name, file_config, driver_config, executor_config)

    def launch(self, namespace):
        try:
            self._k8s_client.delete_sparkapplication(
                self._name, namespace=namespace)
        except RuntimeError as error:
            logging.info("Spark application %s not exist",
                         self._name)

        try:
            self._k8s_client.create_sparkapplication(
                self._config, namespace=namespace)
        except RuntimeError as error:
            logging.fatal("Spark application error %s", error)
            sys.exit(-1)

    def join(self, namespace):
        try:
            while True:
                status, msg = self._k8s_client.get_sparkapplication(
                    self._name, namespace=namespace)
                if status == K8SAPPStatus.COMPLETED:
                    logging.info("Spark job %s completed", self._name)
                    break
                if status == K8SAPPStatus.FAILED:
                    logging.error("Spark job %s failed, with response %s",
                                  self._name, msg)
                    sys.exit(-1)
                else:
                    logging.info("Sleep 10s to wait spark job done...")
                    time.sleep(10)
            self._k8s_client.delete_sparkapplication(
                self._name, namespace=namespace)
        except RuntimeError as error:
            logging.fatal("Spark application error %s", error)
            sys.exit(-1)

    @staticmethod
    def _task_config(task_name, file_config,
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
        logging.debug(yaml_config)
        try:
            config = yaml.safe_load(yaml_config)
            return config
        except Exception as e:  # pylint: disable=broad-except
            logging.error("Invalid spark config, %s", str(e))
            sys.exit(-1)

    @staticmethod
    def _local_task_config(name, file_config):
        local_jars = os.environ.get("SPARK_JARS", "")
        return {
            FakeK8SClient.name_key(): name,
            FakeK8SClient.entry_key(): file_config.entry_file(),
            FakeK8SClient.arg_key(): [
                "--config={}".format(file_config.config_file()),
                "--packages={}".format(local_jars)]
        }
