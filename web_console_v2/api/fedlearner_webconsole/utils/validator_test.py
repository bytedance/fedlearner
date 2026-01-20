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

from fedlearner_webconsole.utils.validator import Validator


class MyTestCase(unittest.TestCase):

    def test_validator(self):
        validators = [
            Validator('field_1', lambda x: x > 0),
            Validator('field_2', lambda x: x > 0),
            Validator('field_3', lambda x: x > 0)
        ]

        dct_1 = {'field_1': 1, 'field_2': 2, 'field_3': 3}

        dct_2 = {'field_1': -1, 'field_2': 2, 'field_3': 3}

        dct_3 = {'field_1': 1, 'field_2': 2}

        res_1, err_1 = Validator.validate(dct_1, validators)
        res_2, err_2 = Validator.validate(dct_2, validators)
        res_3, err_3 = Validator.validate(dct_3, validators)

        self.assertTrue(res_1)
        self.assertFalse(res_2)
        self.assertFalse(res_3)

        self.assertEqual(0, len(err_1))
        self.assertEqual(1, len(err_2))
        self.assertEqual(1, len(err_3))


if __name__ == '__main__':
    unittest.main()
