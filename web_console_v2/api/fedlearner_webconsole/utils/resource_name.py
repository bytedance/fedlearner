# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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
from uuid import uuid4


def resource_uuid() -> str:
    """Build resource uuid
    Returns:
        A DNS-1035 label. A DNS-1035 label must start with an
        alphabetic character. Since k8s resource name is limited to 64 chars,
        job_def name is limited to 24 chars and pod name suffix is limit to
        19 chars, 20 chars are left for uuid.
        substring uuid[:19] has no collision in 10 million draws.
    """
    return f'u{uuid4().hex[:19]}'
