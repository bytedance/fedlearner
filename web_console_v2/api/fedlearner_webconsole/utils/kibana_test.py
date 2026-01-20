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

# pylint: disable=protected-access
import unittest

from fedlearner_webconsole.exceptions import UnauthorizedException
from fedlearner_webconsole.utils.kibana import Kibana


class KibanaTest(unittest.TestCase):

    def test_auth(self):
        self.assertRaises(UnauthorizedException, Kibana._check_authorization, 'tags.1')
        self.assertRaises(UnauthorizedException, Kibana._check_authorization, 'tags.1:2')
        self.assertRaises(UnauthorizedException, Kibana._check_authorization, 'x:3 and y:4', {'x'})
        self.assertRaises(UnauthorizedException, Kibana._check_authorization, 'x:3 OR y:4 AND z:5', {'x', 'z'})
        try:
            Kibana._check_authorization('x:1', {'x'})
            Kibana._check_authorization('x:1 AND y:2 OR z:3', {'x', 'y', 'z'})
            Kibana._check_authorization('x:1 oR y:2 aNd z:3', {'x', 'y', 'z'})
            Kibana._check_authorization('*', {'x', '*'})
            Kibana._check_authorization(None, None)
        except UnauthorizedException:
            self.fail()

    def test_parse_time(self):
        dt1 = 0
        dt2 = 60 * 60 * 24
        args = {'start_time': dt1, 'end_time': dt2}
        st, et = Kibana._parse_start_end_time(args)
        self.assertEqual(st, '1970-01-01T00:00:00Z')
        self.assertEqual(et, '1970-01-02T00:00:00Z')
        st, et = Kibana._parse_start_end_time({'start_time': -1, 'end_time': -1})
        self.assertEqual(st, 'now-5y')
        self.assertEqual(et, 'now')


if __name__ == '__main__':
    unittest.main()
