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
import logging.config
from pathlib import Path
from tempfile import TemporaryDirectory
from shutil import make_archive, copy

from click import command, option, Path as PathType, Choice

from deploy.auto_cert.authenticator import ApiKeyAuthenticator
from deploy.container.containers import pull_image_as_docker_archive
from pp_lite.deploy.configs.logging_config import LOGGING_CONFIG
from pp_lite.deploy.certificate import get_certificate, write_certificate
from pp_lite.deploy.configs.controllers import get_deploy_config_from_yaml


def _pull_image(image_uri: str, pp_lite_path: Path):
    logging.info('include_image is set to true; pulling pp_lite_client...')
    pull_image_as_docker_archive(image_uri, pp_lite_path / 'client_image.tar', 'privacy_computing_platform')
    logging.info('include_image is set to true; pulling pp_lite_client... [DONE]')


def _make_dirs(pp_lite_path: Path):
    pp_lite_path.mkdir()
    (pp_lite_path / 'input').mkdir()
    (pp_lite_path / 'output').mkdir()
    (pp_lite_path / 'log').mkdir()
    (pp_lite_path / 'cert').mkdir()


def _copy_static_files(pp_lite_path: Path):
    path_of_this_file = Path(__file__).parent
    copy(path_of_this_file / 'static' / '.env', Path(pp_lite_path / '.env'))
    copy(path_of_this_file / 'static' / 'start.sh', Path(pp_lite_path / 'start.sh'))


@command(name='PP Lite Client Archiver', help='I make archives for PP Lite Client for your clients.')
@option('--yaml_config_path',
        '-c',
        help='How should I perform?',
        type=PathType(exists=True, file_okay=True, dir_okay=False),
        required=True)
@option('--output_path',
        '-o',
        help='Where should I put the output archive?',
        type=PathType(exists=True, file_okay=False, dir_okay=True),
        required=True)
@option('--output_format',
        '-f',
        help='In what format do you want your archive to be?',
        type=Choice(['tar', 'zip']),
        default='zip')
def archive(yaml_config_path: str, output_path: str, output_format: str):
    with TemporaryDirectory() as temp_dir:
        config = get_deploy_config_from_yaml(Path(yaml_config_path).absolute())
        cert = get_certificate(config.pure_domain_name, ApiKeyAuthenticator(config.auto_cert_api_key))

        pp_lite_path = Path(temp_dir) / 'pp_lite'
        _make_dirs(pp_lite_path)
        _copy_static_files(pp_lite_path)
        write_certificate(pp_lite_path / 'cert', cert)

        if config.include_image:
            _pull_image(config.image_uri, pp_lite_path)

        logging.info('Making zip archive...')
        make_archive(Path(output_path) / 'pp_lite_client', output_format, Path(temp_dir).absolute())
        logging.info('Making zip archive... [DONE]')


if __name__ == '__main__':
    logging.config.dictConfig(LOGGING_CONFIG)
    try:
        archive()  # pylint: disable=no-value-for-parameter
    except Exception as e:  # pylint: disable=broad-except
        logging.error(e)
        raise e
