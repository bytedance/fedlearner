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
from fedlearner_webconsole.k8s.k8s_cache import Event, ObjectType, EventType


class EventTest(unittest.TestCase):

    def test_from_json(self):
        app_object = {'metadata': {'name': 'test'}, 'status': None, 'spec': {'test': 1}}
        test_event_dict = {'type': 'ADDED', 'object': app_object}
        event = Event.from_json(test_event_dict, ObjectType.FLAPP)
        self.assertEqual(event.app_name, 'test')
        self.assertEqual(event.obj_type, ObjectType.FLAPP)
        self.assertEqual(event.event_type, EventType.ADDED)
        self.assertEqual(event.obj_dict, app_object)


if __name__ == '__main__':
    unittest.main()
