# Copyright 2021 The FedLearner Authors. All Rights Reserved.
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
import io
import logging
import os
import tarfile
import traceback

from enum import Enum
from copy import deepcopy
from typing import Tuple, Optional, List
from uuid import uuid4

from envs import Envs

from fedlearner_webconsole.composer.interface import IItem, IRunner, ItemType
from fedlearner_webconsole.composer.models import Context, RunnerStatus
from fedlearner_webconsole.sparkapp.service import SparkAppService
from fedlearner_webconsole.sparkapp.schema import SparkAppConfig


class DataPipelineType(Enum):
    ANALYZER = 'analyzer'
    CONVERTER = 'converter'
    TRANSFORMER = 'transformer'


class DataPipelineItem(IItem):
    def __init__(self, task_id: int):
        self.id = task_id

    def type(self) -> ItemType:
        return ItemType.DATA_PIPELINE

    def get_id(self) -> int:
        return self.id


class DataPipelineRunner(IRunner):
    TYPE_PARAMS_MAPPER = {
        DataPipelineType.ANALYZER: {
            'files_dir': 'fedlearner_webconsole/dataset/sparkapp/pipeline',
            'main_application': 'pipeline/analyzer.py',
        },
        DataPipelineType.CONVERTER: {
            'files_dir': 'fedlearner_webconsole/dataset/sparkapp/pipeline',
            'main_application': 'pipeline/converter.py',
        },
        DataPipelineType.TRANSFORMER: {
            'files_dir': 'fedlearner_webconsole/dataset/sparkapp/pipeline',
            'main_application': 'pipeline/transformer.py',
        }
    }

    SPARKAPP_STATE_TO_RUNNER_STATUS = {
        '': RunnerStatus.RUNNING,
        'SUBMITTED': RunnerStatus.RUNNING,
        'PENDING_RERUN': RunnerStatus.RUNNING,
        'RUNNING': RunnerStatus.RUNNING,
        'COMPLETED': RunnerStatus.DONE,
        'SUCCEEDING': RunnerStatus.DONE,
        'FAILED': RunnerStatus.FAILED,
        'SUBMISSION_FAILED': RunnerStatus.FAILED,
        'INVALIDATING': RunnerStatus.FAILED,
        'FAILING': RunnerStatus.FAILED,
        'UNKNOWN': RunnerStatus.FAILED
    }

    def __init__(self, task_id: int) -> None:
        self.task_id = task_id
        self.task_type = None
        self.files_dir = None
        self.files_path = None
        self.main_application = None
        self.command = []
        self.sparkapp_name = None
        self.args = {}
        self.started = False
        self.error_msg = False

        self.spark_service = SparkAppService()

    def start(self, context: Context):
        try:
            self.started = True
            self.args = deepcopy(context.data.get(str(self.task_id), {}))
            self.task_type = DataPipelineType(self.args.pop('task_type'))
            name = self.args.pop('sparkapp_name')
            job_id = uuid4().hex
            self.sparkapp_name = f'pipe-{self.task_type.value}-{job_id}-{name}'

            params = self.__class__.TYPE_PARAMS_MAPPER[self.task_type]
            self.files_dir = os.path.join(Envs.BASE_DIR, params['files_dir'])
            self.files_path = Envs.SPARKAPP_FILES_PATH
            self.main_application = params['main_application']
            self.command = self.args.pop('input')

            files = None
            if self.files_path is None:
                files_obj = io.BytesIO()
                with tarfile.open(fileobj=files_obj, mode='w') as f:
                    f.add(self.files_dir)
                files = files_obj.getvalue()

            config = {
                'name': self.sparkapp_name,
                'files': files,
                'files_path': self.files_path,
                'image_url': Envs.SPARKAPP_IMAGE_URL,
                'volumes': gen_sparkapp_volumes(Envs.SPARKAPP_VOLUMES),
                'driver_config': {
                    'cores':
                    1,
                    'memory':
                    '4g',
                    'volume_mounts':
                    gen_sparkapp_volume_mounts(Envs.SPARKAPP_VOLUME_MOUNTS),
                },
                'executor_config': {
                    'cores':
                    2,
                    'memory':
                    '4g',
                    'instances':
                    1,
                    'volume_mounts':
                    gen_sparkapp_volume_mounts(Envs.SPARKAPP_VOLUME_MOUNTS),
                },
                'main_application': f'${{prefix}}/{self.main_application}',
                'command': self.command,
            }
            config_dict = SparkAppConfig.from_dict(config)
            resp = self.spark_service.submit_sparkapp(config=config_dict)
            logging.info(
                f'created spark app, name: {name}, '
                f'config: {config_dict.__dict__}, resp: {resp.__dict__}')
        except Exception as e:  # pylint: disable=broad-except
            self.error_msg = f'[composer] failed to run this item, err: {e}, \
            trace: {traceback.format_exc()}'

    def result(self, context: Context) -> Tuple[RunnerStatus, dict]:
        if self.error_msg:
            context.set_data(f'failed_{self.task_id}',
                             {'error': self.error_msg})
            return RunnerStatus.FAILED, {}
        if not self.started:
            return RunnerStatus.RUNNING, {}
        resp = self.spark_service.get_sparkapp_info(self.sparkapp_name)
        logging.info(f'sparkapp resp: {resp.__dict__}')
        if not resp.state:
            return RunnerStatus.RUNNING, {}
        return self.__class__.SPARKAPP_STATE_TO_RUNNER_STATUS.get(
            resp.state, RunnerStatus.FAILED), resp.to_dict()


def gen_sparkapp_volumes(value: str) -> Optional[List[dict]]:
    if value != 'data':
        return None
    # TODO: better to read from conf
    return [{
        'name': 'data',
        'persistentVolumeClaim': {
            'claimName': 'pvc-fedlearner-default'
        }
    }]


def gen_sparkapp_volume_mounts(value: str) -> Optional[List[dict]]:
    if value != 'data':
        return None
    # TODO: better to read from conf
    return [{'name': 'data', 'mountPath': '/data'}]
