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

import re
from typing import Optional


def get_pure_domain_name(common_name: str) -> Optional[str]:
    """Get domain name from common name filed in x.509

    Args:
        common_name (str): common name that parse from x.509

    Returns:
        str: domain name, like bytedance/bytedance-test
    """
    for regex in [r'.*fl-([^\.]+)(\.com)?', r'(.+)\.fedlearner\.net']:
        matched = re.match(regex, common_name)
        if matched:
            return matched.group(1)
    return None
