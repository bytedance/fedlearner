# Copyright 2020 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8

from google.protobuf import text_format
from fedlearner_webconsole.proto.workflow_definition_pb2 import (
    WorkflowDefinition, JobDefinition, JobDependency
)
from fedlearner_webconsole.proto.common_pb2 import (
    Variable
)

def make_workflow_template():
    workflow = WorkflowDefinition(
        group_alias='test_template',
        is_left=True,
        variables=[
            Variable(
                name='image_version',
                value='v1.5-rc3',
                access_mode=Variable.PEER_READABLE),
        ],
        job_definitions=[
            JobDefinition(
                name='raw_data_job',
                type=JobDefinition.RAW_DATA,
                is_federated=False,
                is_manual=False,
                variables=[
                    Variable(
                        name='input_dir',
                        value='/data/input/test_input',
                        access_mode=Variable.PRIVATE),
                ],
                yaml_template='''
{
  "spec": {
    "flReplicaSpecs": {
      "Master": {
        "pair": true,
        "replicas": 1,
        "template": {
          "spec": {
            "containers": [
              {
                "env": [
                  {
                    "name": "INPUT_BASE_DIR",
                    "value": "{workflow.raw_data_job.input_dir}"
                  }
                ],
                "image": "{workflow.image_version}",
              }
            ]
          }
        }
      }
    }
  }
}
                '''
            ),
            JobDefinition(
                name='data_join_job',
                type=JobDefinition.DATA_JOIN,
                is_federated=True,
                is_manual=False,
                variables=[
                    Variable(
                        name='input_dir',
                        value='/data/input/test_input',
                        access_mode=Variable.PRIVATE),
                ],
                dependencies=[
                    JobDependency(
                        source='raw_data_job',

                    )
                ],
                yaml_template='''
{
  "spec": {
    "flReplicaSpecs": {
      "Master": {
        "pair": true,
        "replicas": 1,
        "template": {
          "spec": {
            "containers": [
              {
                "env": [
                  {
                    "name": "RAW_DATA_SUB_DIR",
                    "value": "{workflow.raw_data_job.name}"
                  }
                ],
                "image": "{workflow.image_version}",
              }
            ]
          }
        }
      }
    }
  }
}
                '''
            )
        ])
    
    print(text_format.MessageToString(workflow))


if __name__ == '__main__':
    make_workflow_template()