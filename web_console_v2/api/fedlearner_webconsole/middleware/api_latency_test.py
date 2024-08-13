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

import json
import unittest
import flask_testing
from flask import Flask
from io import StringIO
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter

from fedlearner_webconsole.middleware.api_latency import api_latency_middleware


class ApiLatencyTest(flask_testing.TestCase):

    def setUp(self):
        super().setUp()
        self._string_io = StringIO()
        trace.set_tracer_provider(
            TracerProvider(resource=Resource.create({'service.name': 'test_api_lantency'}),
                           active_span_processor=SimpleSpanProcessor(ConsoleSpanExporter(out=self._string_io))))

    def create_app(self):
        app = Flask('test_api_lantency')

        @app.route('/test', methods=['GET'])
        def test():
            return {'data': 'Hello'}

        app = api_latency_middleware(app)
        return app

    def test_api_latency(self):
        get_response = self.client.get('/test')
        self.assertEqual(get_response.json, {'data': 'Hello'})
        span = json.loads(self._string_io.getvalue())
        self.assertEqual(span['name'], '/test')
        self.assertEqual(span['kind'], 'SpanKind.SERVER')
        self.assertEqual(
            span['attributes'], {
                'http.method': 'GET',
                'http.server_name': 'localhost',
                'http.scheme': 'http',
                'net.host.port': 80,
                'http.host': 'localhost',
                'http.target': '/test',
                'net.peer.ip': '127.0.0.1',
                'http.user_agent': 'werkzeug/1.0.1',
                'http.flavor': '1.1',
                'http.route': '/test',
                'http.status_code': 200
            })
        self.assertEqual(
            span['resource'], {
                'telemetry.sdk.language': 'python',
                'telemetry.sdk.name': 'opentelemetry',
                'telemetry.sdk.version': '1.10.0',
                'service.name': 'test_api_lantency'
            })


if __name__ == '__main__':
    unittest.main()
