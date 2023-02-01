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
import logging


class _MiddlewareRegistry(object):

    def __init__(self):
        self.middlewares = []

    def register(self, middleware):
        self.middlewares.append(middleware)

    def init_app(self, app):
        logging.info('Initializing app with middlewares')
        # Wraps app with middlewares
        for middleware in self.middlewares:
            app = middleware(app)
        return app


flask_middlewares = _MiddlewareRegistry()
wsgi_middlewares = _MiddlewareRegistry()
