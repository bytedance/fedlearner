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
import json
import unittest
from testing.common import BaseTestCase
from http import HTTPStatus

from envs import Envs


class TfRecordReaderTest(BaseTestCase):

    def test_reader(self):
        metrix = [['id', 'x_1', 'x_2', 'x_3', 'x_4'],
                  [['0'], [0.4660772681236267], [0.9965257048606873], [0.15621308982372284], [0.9282205700874329]],
                  [['1'], [0.04800121858716011], [0.1965402364730835], [0.6086887121200562], [0.9214732646942139]],
                  [['2'], [0.05255622789263725], [0.8994112610816956], [0.6675127744674683], [0.577964186668396]],
                  [['3'], [0.7057438492774963], [0.5592560172080994], [0.6767191886901855], [0.6311695575714111]],
                  [['4'], [0.9203364253044128], [0.9567945599555969], [0.19533273577690125], [0.17610156536102295]]]
        data = {
            'path': f'{Envs.BASE_DIR}/testing/test_data/'
                    f'tfrecord_test.xx.aaa.data',
            'wrong_path': 'adsad.data',
            'lines': 5
        }
        # test right path
        resp = self.get_helper('/api/v2/debug/tfrecord?path={}&lines={}'.format(data['path'], data['lines']))  # pylint: disable=consider-using-f-string
        my_data = json.loads(resp.data).get('data')
        self.assertEqual(metrix, my_data)
        self.assertEqual(HTTPStatus.OK, resp.status_code)

        # test None path
        resp = self.get_helper('/api/v2/debug/tfrecord')
        self.assertEqual(HTTPStatus.BAD_REQUEST, resp.status_code)

        # test wrong path
        resp = self.get_helper('/api/v2/debug/tfrecord?path={}&lines={}'.format(data['wrong_path'], data['lines']))  # pylint: disable=consider-using-f-string
        self.assertEqual(HTTPStatus.BAD_REQUEST, resp.status_code)


if __name__ == '__main__':
    unittest.main()
