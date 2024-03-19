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

import logging
from pathlib import Path

from yaml import load, Loader

from pp_lite.deploy.configs.models_pb2 import Config


def get_deploy_config_from_yaml(path: Path) -> Config:
    logging.info(f'Getting config from YAML file with path={path}...')
    with open(path, mode='r', encoding='utf-8') as f:
        content = load(f, Loader=Loader)
    logging.info(f'Getting config from YAML file with path={path}... [DONE]')
    return Config(pure_domain_name=content['pure_domain_name'],
                  image_uri=content['image_uri'],
                  include_image=content['include_image'],
                  auto_cert_api_key=content['auto_cert_api_key'])
