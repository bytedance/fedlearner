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

# coding: utf-8
import json
import unittest

from http import HTTPStatus
from unittest.mock import patch
from google.protobuf import struct_pb2

from fedlearner_webconsole.auth.models import User
from fedlearner_webconsole.proto.filtering_pb2 import FilterExpression
from fedlearner_webconsole.proto.testing.testing_pb2 import Tdata
from fedlearner_webconsole.utils.decorators.pp_flask import use_kwargs
from fedlearner_webconsole.utils.flask_utils import download_json, get_current_user, set_current_user, \
    make_flask_response, _normalize_data, get_link, FilterExpField, get_current_sso
from testing.common import BaseTestCase


class FlaskUtilsTest(BaseTestCase):

    def test_download_json(self):
        test_content = {'haha': {'hh': [0]}, 'abc': 123, 'unicode': ['boss行味镪', '🤑']}

        @self.app.route('/test', methods=['POST'])
        def test_route():
            return download_json(test_content, 'test_file')

        response = self.client.post('/test')
        self.assertEqual(
            response.data, b'{"haha": {"hh": [0]}, "abc": 123,'
            b' "unicode": ["boss\xe8\xa1\x8c\xe5\x91\xb3\xe9\x95\xaa", "\xf0\x9f\xa4\x91"]}')
        self.assertEqual(response.data.decode('utf-8'),
                         '{"haha": {"hh": [0]}, "abc": 123, "unicode": ["boss行味镪", "🤑"]}')
        self.assertEqual(json.loads(response.data.decode('utf-8')), test_content)
        self.assertEqual(response.headers['Content-Disposition'], 'attachment; filename=test_file.json')
        self.assertEqual(response.headers['Content-Type'], 'application/json; charset=UTF-8')

    def test_get_current_user(self):
        test_user = User(id=1, username='test')

        @self.app.route('/test', methods=['POST'])
        def test_route():
            set_current_user(test_user)
            return {}, HTTPStatus.OK

        self.client.post('/test')
        self.assertEqual(test_user, get_current_user())

    def test_normalize_data(self):
        # Dict
        d = {'a': 123}
        self.assertEqual(_normalize_data(d), d)
        # Proto
        self.assertEqual(_normalize_data(Tdata(id=134)), {
            'id': 134,
            'mappers': {},
            'projects': [],
            'tt': 'UNSPECIFIED',
        })
        # Array of proto
        self.assertEqual(_normalize_data([Tdata(id=1), Tdata(id=2)]), [{
            'id': 1,
            'mappers': {},
            'projects': [],
            'tt': 'UNSPECIFIED',
        }, {
            'id': 2,
            'mappers': {},
            'projects': [],
            'tt': 'UNSPECIFIED',
        }])
        # Array
        l = [{'a': 44}, {'b': '123'}]
        self.assertEqual(_normalize_data(l), l)
        # Dict with nested Protobuf Message and map<int, Message> structure.
        self.assertEqual(_normalize_data({'a': Tdata(id=1, mappers={0: struct_pb2.Value(string_value='test')})}),
                         {'a': {
                             'id': 1,
                             'mappers': {
                                 '0': 'test',
                             },
                             'projects': [],
                             'tt': 'UNSPECIFIED',
                         }})

    def test_make_flask_response(self):
        resp, status = make_flask_response()
        self.assertDictEqual(resp, {'data': {}, 'page_meta': {}})
        self.assertEqual(HTTPStatus.OK, status)

        data = [{'name': 'kiyoshi'} for _ in range(5)]
        page_meta = {'page': 1, 'page_size': 0, 'total_items': 5, 'total_pages': 1}
        resp, status = make_flask_response(data, page_meta)
        self.assertDictEqual(data[0], resp.get('data')[0])
        self.assertDictEqual(page_meta, resp.get('page_meta'))

    def test_get_link_in_flask(self):

        @self.app.route('/test')
        def test_route():
            return get_link('/v2/workflow-center/workflows/123')

        resp = self.get_helper('/test', use_auth=False)
        self.assertEqual(resp.data.decode('utf-8'), 'http://localhost/v2/workflow-center/workflows/123')

    @patch('fedlearner_webconsole.utils.flask_utils.request.headers.get')
    def test_get_current_sso(self, mock_headers):
        mock_headers.return_value = 'test oauth access_token'
        sso_name = get_current_sso()
        self.assertEqual(sso_name, 'test')


class NonFlaskTest(unittest.TestCase):

    def test_get_link_not_in_flask(self):
        self.assertEqual(get_link('/v2/test'), 'http://localhost:666/v2/test')


class FilterExpFieldTest(BaseTestCase):

    def test_custom_field(self):

        @self.app.route('/test')
        @use_kwargs({
            'filter_exp': FilterExpField(required=False, load_default=None),
        }, location='query')
        def test_route(filter_exp: FilterExpression):
            return make_flask_response(data=filter_exp)

        resp = self.get_helper('/test', use_auth=False)
        self.assertEqual(resp.status_code, HTTPStatus.OK)

        resp = self.get_helper('/test?filter_exp=invalid', use_auth=False)
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)

        resp = self.get_helper('/test?filter_exp=(x%3D123)', use_auth=False)
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = self.get_response_data(resp)
        self.assertEqual(data['simple_exp']['field'], 'x')


if __name__ == '__main__':
    unittest.main()
