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

from string import Template

import yaml

from fedlearner_webconsole.proto.e2e_pb2 import E2eJob


def e2e_job_model_to_yaml(job: E2eJob) -> str:
    return _E2E_JOB_TEMPLATE.substitute(
        job_name=job.job_name,
        name_prefix=job.name_prefix,
        e2e_image_uri=job.e2e_image_uri,
        project_name=job.project_name,
        platform_endpoint=job.platform_endpoint,
        fedlearner_image_uri=job.fedlearner_image_uri,
        script_path=job.script_path,
    )


def e2e_job_to_dict(job: E2eJob) -> dict:
    return yaml.load(e2e_job_model_to_yaml(job), Loader=yaml.Loader)


_E2E_JOB_TEMPLATE = Template("""apiVersion: batch/v1
kind: Job
metadata:
  name: $job_name
  labels:
    owner: wangsen.0914
    psm: data.aml.fl
spec:
  template:
    spec:
      containers:
      - name: $job_name
        image: $e2e_image_uri
        env:
        - name: PYTHONPATH
          value: /app
        - name: PROJECT_NAME
          value: $project_name
        - name: PLATFORM_ENDPOINT
          value: $platform_endpoint
        - name: FEDLEARNER_IMAGE
          value: $fedlearner_image_uri
        - name: NAME_PREFIX
          value: $name_prefix
        command:
        - python
        - $script_path
      imagePullSecrets:
        - name: regcred
      restartPolicy: Never
  backoffLimit: 0
""")
