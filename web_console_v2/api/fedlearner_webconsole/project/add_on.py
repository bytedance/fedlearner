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

import tarfile
import io
from base64 import b64encode, b64decode


def _parse_certificates(encoded_gz):
    """
    Parse certificates from base64-encoded string to a dict
    Args:
        encoded_gz: A base64-encoded string from a `.gz` file.
    Returns:
        dict: key is the file name, value is the content
    """
    binary_gz = io.BytesIO(b64decode(encoded_gz))
    with tarfile.open(fileobj=binary_gz) as gz:
        certificates = {}
        for file in gz.getmembers():
            if file.isfile():
                # raw file name is like `fl-test.com/client/client.pem`
                certificates[file.name.split('/', 1)[-1]] = str(b64encode(gz.extractfile(file).read()),
                                                                encoding='utf-8')
    return certificates


def _create_add_on(client, domain_name, certificates):
    """Create add on and upgrade nginx-ingress and operator"""
    # TODO
    pass
