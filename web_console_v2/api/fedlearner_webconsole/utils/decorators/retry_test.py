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

import unittest
from unittest.mock import MagicMock, patch, Mock

from fedlearner_webconsole.utils.decorators.retry import retry_fn


class RpcError(Exception):

    def __init__(self, status: int = 0):
        super().__init__()
        self.status = status


def some_unstable_connect(grpc_call):
    res = grpc_call()
    if res['status'] != 0:
        raise RpcError(res['status'])
    return res['data']


class RetryTest(unittest.TestCase):

    def test_retry_fn(self):

        @retry_fn(retry_times=2, need_retry=lambda e: isinstance(e, RpcError))
        def retry_twice(grpc_call):
            return some_unstable_connect(grpc_call)

        grpc_call = MagicMock()
        grpc_call.side_effect = [{'status': -1, 'data': 'hhhhhh'}, {'status': -1, 'data': 'hhhh'}]
        with self.assertRaises(RpcError):
            retry_twice(grpc_call=grpc_call)

        grpc_call = MagicMock()
        grpc_call.side_effect = [{'status': -1, 'data': 'hhhhhh'}, {'status': 0, 'data': 'hhhh'}]
        self.assertEqual(retry_twice(grpc_call=grpc_call), 'hhhh')

    @patch('fedlearner_webconsole.utils.decorators.retry.time.sleep')
    def test_retry_fn_with_delay(self, mock_sleep: Mock):
        sleep_time = 0

        def fake_sleep(s):
            nonlocal sleep_time
            sleep_time = sleep_time + s

        mock_sleep.side_effect = fake_sleep

        @retry_fn(retry_times=5, delay=1000, backoff=2)
        def retry_with_delay(grpc_call):
            return some_unstable_connect(grpc_call)

        grpc_call = MagicMock()
        grpc_call.return_value = {'status': 0, 'data': '123'}
        self.assertEqual(retry_with_delay(grpc_call), '123')
        mock_sleep.assert_not_called()

        grpc_call = MagicMock()
        grpc_call.side_effect = [{'status': 255}, {'status': -1}, {'status': 2}, {'status': 0, 'data': '123'}]
        self.assertEqual(retry_with_delay(grpc_call), '123')
        self.assertEqual(mock_sleep.call_count, 3)
        # 1 + 2 + 4
        self.assertEqual(sleep_time, 7)

        # Failed case
        sleep_time = 0
        mock_sleep.reset_mock()
        grpc_call = MagicMock()
        grpc_call.side_effect = RuntimeError()
        with self.assertRaises(RuntimeError):
            retry_with_delay(grpc_call=grpc_call)
        self.assertEqual(mock_sleep.call_count, 4)
        # 1 + 2 + 4 + 8
        self.assertEqual(sleep_time, 15)

    def test_retry_fn_with_need_retry(self):

        @retry_fn(retry_times=10, need_retry=lambda e: e.status == 3)
        def custom_retry(grpc_call):
            return some_unstable_connect(grpc_call)

        grpc_call = MagicMock()
        grpc_call.side_effect = [{'status': 3}, {'status': 3}, {'status': 5}, {'status': 6}]
        with self.assertRaises(RpcError):
            custom_retry(grpc_call)
        # When status is 5, it will not retry again.
        self.assertEqual(grpc_call.call_count, 3)


if __name__ == '__main__':
    unittest.main()
