# Copyright 2020 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
import os
from base64 import b64encode
from fedlearner_webconsole.utils.k8s_client import K8sClient


def create_image_pull_secret():
    """Create certificate for image hub (Once for a system)"""
    if os.environ.get('IMAGE_HUB_URL', None) is None or \
        os.environ.get('IMAGE_HUB_USERNAME', None) is None or \
        os.environ.get('IMAGE_HUB_PASSWORD', None) is None:
        return

    client = K8sClient()
    # using base64 to encode authorization information
    encoded_username_password = str(b64encode(
        '{}:{}'.format(os.environ.get('IMAGE_HUB_USERNAME'),
                       os.environ.get('IMAGE_HUB_PASSWORD'))
    ))
    encoded_image_cert = str(b64encode(
        '{"auths":{"{}":{"username":"{}","password":"{}","auth":"{}"}}}'.format(
            os.environ.get('IMAGE_HUB_URL'), os.environ.get('IMAGE_HUB_USERNAME'),
            os.environ.get('IMAGE_HUB_PASSWORD'), encoded_username_password
        )
    ), 'utf-8')

    client.create_secret(
        data={
            '.dockerconfigjson': encoded_image_cert
        },
        metadata={
            'name': 'regcred',
            'namespace': 'default'
        },
        type='kubernetes.io/dockerconfigjson'
    )
