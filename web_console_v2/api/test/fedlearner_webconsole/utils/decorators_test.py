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

import unittest
from unittest.mock import MagicMock

from fedlearner_webconsole.utils.decorators import retry_fn
from fedlearner_webconsole.exceptions import NeedToRetryException

@retry_fn(retry_times=2)
def some_unstable_connect(client):
    res = client()
    if res['status'] != 0:
        raise NeedToRetryException(ret_value='hello world')
    else:
        return res['data']


class DecoratorsTest(unittest.TestCase):
    @staticmethod
    def generator_helper(inject_res):
        for r in inject_res:
            yield r

    def test_retry_fn(self):
        res = [{
            'status': -1,
            'data': 'hhhhhh'
        },{
            'status': -1,
            'data': 'hhhh'
        }]

        client = MagicMock()
        client.side_effect = res
        self.assertTrue(some_unstable_connect(client=client) == 'hello world')

        res = [{
            'status': -1,
            'data': 'hhhhhh'
        },{
            'status': 0,
            'data': 'hhhh'
        }]
        client = MagicMock()
        client.side_effect = res
        self.assertTrue(some_unstable_connect(client=client) == 'hhhh')


if __name__ == '__main__':
    unittest.main()
