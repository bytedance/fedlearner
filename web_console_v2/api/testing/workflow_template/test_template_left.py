# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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
import json
from google.protobuf.json_format import MessageToDict
from fedlearner_webconsole.proto.workflow_definition_pb2 import (WorkflowDefinition, JobDefinition, JobDependency)
from fedlearner_webconsole.proto.common_pb2 import (Variable)


def make_workflow_template():
    workflow = WorkflowDefinition(group_alias='test_template',
                                  variables=[
                                      Variable(name='image_version',
                                               value='v1.5-rc3',
                                               access_mode=Variable.PEER_READABLE),
                                      Variable(name='num_partitions', value='4', access_mode=Variable.PEER_WRITABLE),
                                  ],
                                  job_definitions=[
                                      JobDefinition(name='raw-data-job',
                                                    job_type=JobDefinition.RAW_DATA,
                                                    is_federated=False,
                                                    variables=[
                                                        Variable(name='input_dir',
                                                                 value='/app/deploy/integrated_test/tfrecord_raw_data',
                                                                 access_mode=Variable.PRIVATE),
                                                        Variable(name='file_wildcard',
                                                                 value='*.rd',
                                                                 access_mode=Variable.PRIVATE),
                                                        Variable(name='batch_size',
                                                                 value='1024',
                                                                 access_mode=Variable.PEER_WRITABLE),
                                                        Variable(name='input_format',
                                                                 value='TF_RECORD',
                                                                 access_mode=Variable.PRIVATE),
                                                        Variable(name='output_format',
                                                                 value='TF_RECORD',
                                                                 access_mode=Variable.PRIVATE),
                                                        Variable(name='master_cpu',
                                                                 value='2000m',
                                                                 access_mode=Variable.PEER_WRITABLE),
                                                        Variable(name='master_mem',
                                                                 value='3Gi',
                                                                 access_mode=Variable.PEER_WRITABLE),
                                                        Variable(name='worker_cpu',
                                                                 value='2000m',
                                                                 access_mode=Variable.PEER_WRITABLE),
                                                        Variable(name='worker_mem',
                                                                 value='4Gi',
                                                                 access_mode=Variable.PEER_WRITABLE),
                                                    ],
                                                    yaml_template="""{'metadata':{'name': self.name,'labels':{}},
                                            self.variables.master_cpu: self.variables.master_mem,
                                            '1': workflow.variables.image_version,
                                            '2': workflow.jobs['raw-data-job'].variables.batch_size,
                                            project.participants[0].egress_domain: project.variables.storage_root_path,
                                            project.id: project.name,
                                            workflow.id: workflow.uuid,
                                            workflow.name: workflow.creator
                                            ,}"""),
                                      JobDefinition(name='data-join-job',
                                                    job_type=JobDefinition.DATA_JOIN,
                                                    is_federated=True,
                                                    variables=[
                                                        Variable(name='master_cpu',
                                                                 value='2000m',
                                                                 access_mode=Variable.PEER_WRITABLE),
                                                        Variable(name='master_mem',
                                                                 value='3Gi',
                                                                 access_mode=Variable.PEER_WRITABLE),
                                                        Variable(name='worker_cpu',
                                                                 value='4000m',
                                                                 access_mode=Variable.PEER_WRITABLE),
                                                        Variable(name='worker_mem',
                                                                 value='4Gi',
                                                                 access_mode=Variable.PEER_WRITABLE),
                                                    ],
                                                    dependencies=[JobDependency(source='raw-data-job')],
                                                    yaml_template="""{'metadata':{'name': self.name,'labels':{}},
                                            self.variables.master_cpu: self.variables.master_mem,
                                            '1': workflow.variables.image_version,
                                            '2': workflow.jobs['raw-data-job'].variables.batch_size}""")
                                  ])

    return workflow


if __name__ == '__main__':
    print(
        json.dumps(
            MessageToDict(make_workflow_template(),
                          preserving_proto_field_name=True,
                          including_default_value_fields=True)))
