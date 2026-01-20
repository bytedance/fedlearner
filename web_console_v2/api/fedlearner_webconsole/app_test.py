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
import unittest
from http import HTTPStatus

from marshmallow import fields
from webargs.flaskparser import use_args

from fedlearner_webconsole.utils.flask_utils import make_flask_response
from testing.common import BaseTestCase


class ExceptionHandlersTest(BaseTestCase):

    def test_404(self):
        self.assert404(self.get_helper('/api/v2/not_found', use_auth=False))

    def test_405(self):
        self.assert405(self.post_helper('/api/v2/versions', use_auth=False))

    def test_uncaught_exception(self):

        @self.app.route('/test_uncaught')
        def test_route():
            raise RuntimeError('Uncaught')

        response = self.get_helper('/test_uncaught', use_auth=False)
        self.assert500(response)

    def test_marshmallow_validation_error(self):

        @self.app.route('/test_validation')
        @use_args({'must': fields.Bool(required=True)})
        def test_route(params):
            return make_flask_response({'succeeded': params['must']})

        resp = self.get_helper('/test_validation', use_auth=False)
        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(resp.get_json()['details'], {'json': {'must': ['Missing data for required field.']}})


if __name__ == '__main__':
    unittest.main()
