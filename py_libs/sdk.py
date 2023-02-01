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

import json
import logging
from time import sleep
import time
import urllib
import requests
from http import HTTPStatus
from typing import Dict, Tuple, Optional, List
from fedlearner_webconsole.mmgr.models import ModelJobType
from fedlearner_webconsole.dataset.models import DatasetJobKind, DatasetKindV2 as DatasetKind


def _get_response_data(resp: requests.Response) -> Tuple[int, Dict]:
    return resp.status_code, json.loads(resp.content)


class WebconsoleClient:

    def __init__(self, domain_name: str):
        self._domain_name = domain_name
        self._session = None
        self.sign_in()

    def sign_in(self):
        self._session = requests.Session()
        payload = {'username': 'robot', 'password': 'ZmxAMTIzNDUu'}
        resp = self._session.post(f'{self._domain_name}/api/v2/auth/signin', json=payload)
        content = json.loads(resp.content)
        access_token = content['data']['access_token']
        self._session.headers.update({'Authorization': f'Bearer {access_token}'})

    def get_system_info(self):
        url = f'{self._domain_name}/api/v2/settings/system_info'
        return _get_response_data(self._session.get(url))

    def get_templates(self):
        url = f'{self._domain_name}/api/v2/workflow_templates'
        return _get_response_data(self._session.get(url))

    def get_template(self, template_id):
        url = f'{self._domain_name}/api/v2/workflow_templates/{template_id}'
        return _get_response_data(self._session.get(url))

    def get_projects(self):
        url = f'{self._domain_name}/api/v2/projects'
        return _get_response_data(self._session.get(url))

    def get_project_by_id(self, project_id: int):
        url = f'{self._domain_name}/api/v2/projects/{project_id}'
        return _get_response_data(self._session.get(url))

    def get_data_sources(self, project_id: int):
        url = f'{self._domain_name}/api/v2/data_sources?project_id={project_id}'
        return _get_response_data(self._session.get(url))

    def get_datasets(self, project_id: int, keyword: Optional[str] = None):
        url = f'{self._domain_name}/api/v2/datasets'
        filter_expression = urllib.parse.quote(f'(and(project_id={project_id})(name~="{keyword}"))')
        return _get_response_data(self._session.get(f'{url}?filter={filter_expression}'))

    def post_data_source(self, project_id: int, input_data_path: str, data_source_name: str, store_format: str):
        url = f'{self._domain_name}/api/v2/data_sources'
        payload = {
            'project_id': project_id,
            'data_source': {
                'data_source_url': input_data_path,
                'name': data_source_name,
                'store_format': store_format,
                'dataset_format': 'TABULAR',
            }
        }
        resp = self._session.post(url, json=payload)
        return _get_response_data(resp)

    def post_raw_dataset(self, project_id: int, name: str):
        url = f'{self._domain_name}/api/v2/datasets'
        payload = {
            'dataset_format': 'TABULAR',
            'dataset_type': 'PSI',
            'import_type': 'COPY',
            'store_format': 'TFRECORDS',
            'name': name,
            'kind': DatasetKind.RAW.value,
            'need_publish': True,
            'project_id': project_id
        }
        resp = self._session.post(url, json=payload)
        return _get_response_data(resp)

    def post_intersection_dataset(self, project_id: int, name: str):
        url = f'{self._domain_name}/api/v2/datasets'
        payload = {
            'dataset_format': 'TABULAR',
            'dataset_type': 'PSI',
            'import_type': 'COPY',
            'store_format': 'TFRECORDS',
            'name': name,
            'kind': DatasetKind.PROCESSED.value,
            'is_published': True,
            'project_id': project_id
        }
        resp = self._session.post(url, json=payload)
        return _get_response_data(resp)

    def post_data_batches(self, dataset_id: int, data_source_id: int):
        url = f'{self._domain_name}/api/v2/datasets/{str(dataset_id)}/batches'
        payload = {'data_source_id': data_source_id}
        resp = self._session.post(url, json=payload)
        return _get_response_data(resp)

    def get_participant_datasets(self, project_id: int, kind: DatasetKind):
        url = f'{self._domain_name}/api/v2/project/{project_id}/participant_datasets?kind={kind.value}'
        return _get_response_data(self._session.get(url))

    def get_dataset_job_variables(self, dataset_job_kind: DatasetJobKind):
        url = f'{self._domain_name}/api/v2/dataset_job_definitions/{dataset_job_kind.value}'
        return _get_response_data(self._session.get(url))

    def post_dataset_job(self, project_id: int, output_dataset_id: int, dataset_job_parameter: Dict):
        url = f'{self._domain_name}/api/v2/projects/{project_id}/dataset_jobs'
        payload = {'dataset_job_parameter': dataset_job_parameter, 'output_dataset_id': output_dataset_id}
        resp = self._session.post(url, json=payload)
        return _get_response_data(resp)

    def get_model_job_groups(self, project_id: int, keyword: Optional[str] = None):
        url = f'{self._domain_name}/api/v2/projects/{project_id}/model_job_groups'
        resp = self._session.get(url, json={'keyword': keyword})
        return _get_response_data(resp)

    def get_model_job_group(self, project_id: int, group_id: int):
        url = f'{self._domain_name}/api/v2/projects/{project_id}/model_job_groups/{group_id}'
        resp = self._session.get(url)
        return _get_response_data(resp)

    def post_model_job_groups(self, project_id: int, name: str, dataset_id: int):
        url = f'{self._domain_name}/api/v2/projects/{project_id}/model_job_groups'
        payload = {'name': name, 'dataset_id': dataset_id, 'algorithm_type': 'NN_VERTICAL'}
        resp = self._session.post(url, json=payload)
        return _get_response_data(resp)

    def put_model_job_group(self, project_id: int, group_id: int, algorithm_id: int, config: Dict):
        url = f'{self._domain_name}/api/v2/projects/{project_id}/model_job_groups/{group_id}'
        payload = {'authorized': True, 'algorithm_id': algorithm_id, 'config': config}
        resp = self._session.put(url, json=payload)
        return _get_response_data(resp)

    def launch_model_job(self, project_id: int, group_id: int):
        url = f'{self._domain_name}/api/v2/projects/{project_id}/model_job_groups/{group_id}:launch'
        resp = self._session.post(url, json={'comment': 'created by automated scheduler'})
        return _get_response_data(resp)

    def get_model_jobs(self, project_id: int, keyword: Optional[str] = None):
        url = f'{self._domain_name}/api/v2/projects/{project_id}/model_jobs'
        resp = self._session.get(url, json={'keyword': keyword})
        return _get_response_data(resp)

    def get_model_job(self, project_id: int, model_job_id: int):
        url = f'{self._domain_name}/api/v2/projects/{project_id}/model_jobs/{model_job_id}'
        resp = self._session.get(url)
        return _get_response_data(resp)

    def post_model_jobs(self, project_id: int, name: str, model_job_type: ModelJobType, dataset_id: int,
                        algorithm_id: int, model_id: int, config: Dict):
        url = f'{self._domain_name}/api/v2/projects/{project_id}/model_jobs'
        payload = {
            'name': name,
            'model_job_type': model_job_type.name,
            'dataset_id': dataset_id,
            'algorithm_type': 'NN_VERTICAL',
            'algorithm_id': algorithm_id,
            'model_id': model_id,
            'config': config
        }
        resp = self._session.post(url, json=payload)
        return _get_response_data(resp)

    def put_model_job(self, project_id: int, model_job_id: int, algorithm_id: int, config: Dict):
        url = f'{self._domain_name}/api/v2/projects/{project_id}/model_jobs/{model_job_id}'
        payload = {'algorithm_id': algorithm_id, 'config': config}
        resp = self._session.put(url, json=payload)
        return _get_response_data(resp)

    def get_peer_model_job_group(self, project_id: int, group_id: int, participant_id: int):
        url = f'{self._domain_name}/api/v2/projects/{project_id}/model_job_groups/{group_id}/peers/{participant_id}'
        return _get_response_data(self._session.get(url))

    def patch_peer_model_job_group(self, project_id: int, group_id: int, participant_id: int, config: Dict):
        url = f'{self._domain_name}/api/v2/projects/{project_id}/model_job_groups/{group_id}/peers/{participant_id}'
        return _get_response_data(self._session.patch(url, json={'config': config}))

    def get_models(self, project_id: int, keyword: str):
        url = f'{self._domain_name}/api/v2/projects/{project_id}/models?keyword={keyword}'
        return _get_response_data(self._session.get(url))

    def get_algorithms(self, project_id: int):
        url = f'{self._domain_name}/api/v2/projects/{project_id}/algorithms'
        return _get_response_data(self._session.get(url))


class WebconsoleService:

    def __init__(self, client: WebconsoleClient):
        self.client = client

    def get_project_by_name(self, name: str) -> Optional[Dict]:
        code, content = self.client.get_projects()
        assert code == HTTPStatus.OK
        for project in content['data']:
            if project['name'] == name:
                return project
        return None

    def get_project_id_by_name(self, name: str) -> int:
        project = self.get_project_by_name(name=name)
        assert project is not None
        return project['id']

    def get_template_by_name(self, name: str) -> Optional[Dict]:
        code, content = self.client.get_templates()
        assert code == HTTPStatus.OK
        for template in content['data']:
            if template['name'] == name:
                code, content = self.client.get_template(template['id'])
                assert code == HTTPStatus.OK
                return content['data']
        return None

    def get_model_job_group_by_name(self, project_id: int, name: str) -> Optional[Dict]:
        code, content = self.client.get_model_job_groups(project_id=project_id)
        assert code == HTTPStatus.OK
        for group in content['data']:
            if group['name'] == name:
                group_id = group['id']
                code, content = self.client.get_model_job_group(project_id=project_id, group_id=group_id)
                if code == HTTPStatus.OK:
                    return content['data']
        return None

    def get_model_job_by_name(self, project_id: int, name: str) -> Optional[Dict]:
        code, content = self.client.get_model_jobs(project_id=project_id, keyword=name)
        assert code == HTTPStatus.OK
        for job in content['data']:
            if job['name'] == name:
                return job
        return None

    def get_latest_model_job(self, project_id: int, group_id: int) -> Optional[Dict]:
        code, content = self.client.get_model_job_group(project_id=project_id, group_id=group_id)
        assert code == HTTPStatus.OK
        if len(content['data']['model_jobs']) == 0:
            return None
        model_job_id = content['data']['model_jobs'][0]['id']
        code, content = self.client.get_model_job(project_id=project_id, model_job_id=model_job_id)
        if code != HTTPStatus.OK:
            raise Exception(f'get job {model_job_id} failed with details {content}')
        return content['data']

    def get_model_by_name(self, project_id: int, name: str) -> Optional[Dict]:
        code, content = self.client.get_models(project_id=project_id, keyword=name)
        assert code == HTTPStatus.OK
        for model in content['data']:
            if model['name'] == name:
                return model
        return None

    def get_data_source_by_name(self, name: str, project_id: int) -> Optional[Dict]:
        code, content = self.client.get_data_sources(project_id=project_id)
        assert code == HTTPStatus.OK
        for data_source in content['data']:
            if data_source['name'] == name:
                return data_source
        return None

    def get_dataset_by_name(self, name: str, project_id: int) -> Optional[Dict]:
        code, content = self.client.get_datasets(project_id=project_id, keyword=name)
        assert code == HTTPStatus.OK
        for dataset in content['data']:
            if dataset['name'] == name:
                return dataset
        return None

    def get_domain_name(self) -> str:
        code, content = self.client.get_system_info()
        assert code == HTTPStatus.OK
        return content['data']['domain_name']

    def get_participant_domain_name(self, name) -> str:
        project = self.get_project_by_name(name=name)
        assert project is not None
        return project['participants'][0]['domain_name']

    def get_participant_dataset_by_name(self, name: str, project_id: int, kind: DatasetKind) -> Optional[Dict]:
        code, content = self.client.get_participant_datasets(project_id=project_id, kind=kind)
        assert code == HTTPStatus.OK
        for participant_dataset in content['data']:
            if participant_dataset['name'] == name:
                return participant_dataset
        return None

    def check_dataset_ready(self, name: str, project_id: int, log_interval: int = 50) -> Dict:
        last_log_time = 0
        while True:
            dataset = self.get_dataset_by_name(name=name, project_id=project_id)
            if dataset is not None and dataset['state_frontend'] == 'SUCCEEDED' and dataset['is_published']:
                return dataset
            current_time = time.time()
            if current_time - last_log_time > log_interval:
                logging.info(f'[check_dataset_ready]: still waiting for dataset {name} ready')
                last_log_time = current_time
            sleep(60)

    def check_participant_dataset_ready(self,
                                        name: str,
                                        project_id: int,
                                        kind: DatasetKind,
                                        log_interval: int = 50) -> Dict:
        last_log_time = 0
        while True:
            participant_dataset = self.get_participant_dataset_by_name(name=name, project_id=project_id, kind=kind)
            if participant_dataset is not None:
                return participant_dataset
            current_time = time.time()
            if current_time - last_log_time > log_interval:
                logging.info(f'[check_participant_dataset_ready]: still waiting for participant dataset {name} ready')
                last_log_time = current_time
            sleep(60)

    def get_algorithm_by_path(self, project_id: int, path: str):
        code, content = self.client.get_algorithms(project_id=project_id)
        assert code == HTTPStatus.OK
        for algorithm in content['data']:
            if algorithm['path'] == path:
                return algorithm
        return None

    def get_groups_by_prefix(self, project_name: str, prefix: str) -> List[Dict]:
        project_id = self.get_project_id_by_name(name=project_name)
        code, content = self.client.get_model_job_groups(project_id=project_id)
        assert code == HTTPStatus.OK
        return [group for group in content['data'] if group['name'].startswith(prefix)]
