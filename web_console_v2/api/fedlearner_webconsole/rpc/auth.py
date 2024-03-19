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

from typing import Optional

X_HOST_HEADER = 'x-host'
SSL_CLIENT_SUBJECT_DN_HEADER = 'ssl-client-subject-dn'
PROJECT_NAME_HEADER = 'project-name'


def get_common_name(subject_dn: str) -> Optional[str]:
    """Gets common name from x.509

    Args:
        subject_dn (str): ssl-client-subject-dn from header

    Returns:
        Optional[str]: common name if exists
    """

    # ssl-client-subject-dn example:
    # CN=*.fl-xxx.com,OU=security,O=security,L=beijing,ST=beijing,C=CN
    for s in subject_dn.split(','):
        if s.find('=') == -1:
            return None
        k, v = s.split('=', maxsplit=1)
        if k == 'CN':
            return v
    return None
