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
import threading
import os

from fedlearner_webconsole.utils.k8s_client import K8sClient
from fedlearner_webconsole.utils.fake_k8s_client import FakeK8sClient

_k8s_client = None


def get_client():
    # pylint: disable=global-statement
    global _k8s_client
    if _k8s_client is None:
        with threading.Lock():
            # Thread-safe singleton
            if _k8s_client is None:
                if os.environ.get('FLASK_ENV') == 'production':
                    _k8s_client = K8sClient()
                else:
                    _k8s_client = FakeK8sClient()
    return _k8s_client
