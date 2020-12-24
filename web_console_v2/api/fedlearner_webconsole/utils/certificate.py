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
import json
from base64 import b64encode
from fedlearner_webconsole.utils.k8s_client import K8sClient


def create_image_pull_secret():
    """Create certificate for image hub (Once for a system)"""
    image_hub_url = os.environ.get('IMAGE_HUB_URL')
    image_hub_username = os.environ.get('IMAGE_HUB_USERNAME')
    image_hub_password = os.environ.get('IMAGE_HUB_PASSWORD')
    if image_hub_url is None or image_hub_username is None or \
        image_hub_password is None:
        return

    client = K8sClient()
    # using base64 to encode authorization information
    encoded_username_password = str(b64encode(
        '{}:{}'.format(image_hub_username, image_hub_password)
    ))
    encoded_image_cert = str(b64encode(
        json.dumps({
            'auths': {
                image_hub_url: {
                    'username': image_hub_username,
                    'password': image_hub_password,
                    'auth': encoded_username_password
                }
            }})), 'utf-8')

    client.save_secret(
        data={
            '.dockerconfigjson': encoded_image_cert
        },
        metadata={
            'name': 'regcred',
            'namespace': 'default'
        },
        secret_type='kubernetes.io/dockerconfigjson',
        name='regcred'
    )
