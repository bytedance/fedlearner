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

from typing import Dict, List, Tuple

from kubernetes.client import ApiException

from envs import Envs
from fedlearner_webconsole.e2e.utils import e2e_job_to_dict
from fedlearner_webconsole.proto.e2e_pb2 import E2eJob, InitiateE2eJobsParameter
from fedlearner_webconsole.k8s.k8s_client import k8s_client

COORDINATOR_TESTS = {
    'fed-workflow': 'scripts/auto_e2e/fed_workflow/test_coordinator.py',
    'vertical-dataset-model-serving': 'scripts/auto_e2e/vertical_dataset_model_serving/test_coordinator.py'
}

PARTICIPANT_TESTS = {
    'fed-workflow': 'scripts/auto_e2e/fed_workflow/test_participant.py',
    'vertical-dataset-model-serving': 'scripts/auto_e2e/vertical_dataset_model_serving/test_participant.py'
}

ROLES_MAPPING: Dict[str, Dict] = {'coordinator': COORDINATOR_TESTS, 'participant': PARTICIPANT_TESTS}


def start_job(e2e_job: E2eJob):
    try:
        get_job(e2e_job.job_name)
        raise ValueError(f'failed to start {e2e_job.job_name}; job with job_name={e2e_job.job_name} exists')
    except ApiException:
        pass
    k8s_client.create_app(e2e_job_to_dict(e2e_job), group='batch', version='v1', plural='jobs')


def get_job(job_name: str) -> dict:
    return k8s_client.crds.get_namespaced_custom_object(group='batch',
                                                        version='v1',
                                                        namespace=Envs.K8S_NAMESPACE,
                                                        plural='jobs',
                                                        name=job_name)


def get_job_logs(job_name: str) -> List[str]:
    return k8s_client.get_pod_log(job_name, Envs.K8S_NAMESPACE, 30)


def generate_job_list(params: InitiateE2eJobsParameter) -> List[Tuple[str, E2eJob]]:
    jobs = []
    fed_jobs = ROLES_MAPPING[params.role]
    for job_type, script_path in fed_jobs.items():
        jobs.append((job_type,
                     E2eJob(project_name=params.project_name,
                            script_path=script_path,
                            fedlearner_image_uri=params.fedlearner_image_uri,
                            e2e_image_uri=params.e2e_image_uri,
                            job_name=f'auto-e2e-{params.name_prefix}-{job_type}',
                            platform_endpoint=params.platform_endpoint,
                            name_prefix=f'auto-e2e-{params.name_prefix}')))
    return jobs


def initiate_all_tests(params: InitiateE2eJobsParameter) -> List[Dict[str, str]]:
    jobs = generate_job_list(params)
    for _, job in jobs:
        start_job(job)
    return [{'job_type': job_type, 'job_name': job.job_name} for job_type, job in jobs]
