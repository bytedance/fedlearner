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

from typing import List


def make_ids_iterator_from_list(ids: List[str], batch_size=4096):
    num_parts = (len(ids) + batch_size - 1) // batch_size
    for part_id in range(num_parts):
        id_part = ids[part_id * batch_size:(part_id + 1) * batch_size]
        yield id_part
