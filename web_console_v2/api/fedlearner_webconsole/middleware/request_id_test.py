# Copyright 2023 The FedLearner Authors. All Rights Reserved.
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
import threading
import time
import unittest

from fedlearner_webconsole.middleware.request_id import FlaskRequestId, _thread_local_context, get_current_request_id
from testing.common import BaseTestCase


class FlaskRequestIdTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        # Wraps with middleware
        self.app = FlaskRequestId()(self.app)

        @self.app.route('/test', methods=['GET'])
        def test_api():
            return ''

    def test_response_with_request_id(self):
        response = self.client.get('/test')
        self.assertEqual(len(response.headers['X-TT-LOGID']), 26, 'request id should be an uuid')

    def test_request_with_request_id(self):
        response = self.client.get('/test', headers={'X-TT-LOGID': 'test-id'})
        self.assertEqual(response.headers['X-TT-LOGID'], 'test-id')


class ThreadLocalContextTest(unittest.TestCase):

    def test_multi_thread_context(self):
        ids = {}

        def process(index: str):
            if not index == 't1':
                _thread_local_context.set_request_id(index)
            time.sleep(0.2)
            ids[index] = get_current_request_id()

        # t1 executes first
        # t2 and t3 will be in parallel
        t1 = threading.Thread(target=process, args=['t1'])
        t1.start()
        t1.join()
        t2 = threading.Thread(target=process, args=['t2'])
        t3 = threading.Thread(target=process, args=['t3'])
        t2.start()
        t3.start()
        t3.join()
        t2.join()
        self.assertDictEqual(ids, {'t1': '', 't2': 't2', 't3': 't3'})


if __name__ == '__main__':
    unittest.main()
