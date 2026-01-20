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

from google.protobuf.json_format import ParseDict

from fedlearner_webconsole.proto.workflow_definition_pb2 import Slot
from fedlearner_webconsole.workflow_template.slots_formatter import format_yaml, generate_yaml_template, \
    _generate_slots_map


class SlotFormatterTest(unittest.TestCase):

    def test_format_yaml(self):
        slots = {'Slot_prs': 'prs', 'Slot_prs1': 'prs1', 'dada': 'paopaotang'}
        yaml = '${Slot_prs} a${asdf} ${Slot_prs1}'
        self.assertEqual(format_yaml(yaml, **slots), 'prs a${asdf} prs1')

    def test_generate_yaml_template(self):
        slots = {
            'Slot_prs': ParseDict({
                'reference_type': 'DEFAULT',
                'default_value': 'prs'
            }, Slot()),
            'Slot_prs1': Slot(reference_type=Slot.ReferenceType.PROJECT, reference='project.variables.namespace')
        }
        yaml = '${Slot_prs} a${asdf} ${Slot_prs1}'
        self.assertEqual(generate_yaml_template(yaml, slots), '"prs" a${asdf} str(project.variables.namespace)')

    def test_generate_slots_map(self):
        slots = {
            'Slot_prs':
                ParseDict({
                    'reference_type': 'DEFAULT',
                    'default_value': 'prs'
                }, Slot()),
            'Slot_prs1':
                Slot(reference_type=Slot.ReferenceType.PROJECT, reference='project.variables.namespace'),
            'Slot_pr2':
                Slot(reference_type=Slot.ReferenceType.PROJECT,
                     reference='project.variables.namespace',
                     value_type='NUMBER'),
            'Slot_pr3':
                Slot(reference_type=Slot.ReferenceType.PROJECT,
                     reference='project.variables.namespace',
                     value_type='INT'),
            'Slot_pr4':
                Slot(reference_type=Slot.ReferenceType.PROJECT,
                     reference='project.variables.namespace',
                     value_type='BOOL'),
            'Slot_pr5':
                Slot(reference_type=Slot.ReferenceType.PROJECT,
                     reference='project.variables.namespace',
                     value_type='OBJECT'),
            'Slot_pr6':
                Slot(reference_type=Slot.ReferenceType.PROJECT,
                     reference='project.variables.namespace',
                     value_type='LIST')
        }
        self.assertEqual(
            _generate_slots_map(slots), {
                'Slot_prs': '"prs"',
                'Slot_prs1': 'str(project.variables.namespace)',
                'Slot_pr2': 'float(project.variables.namespace)',
                'Slot_pr3': 'int(project.variables.namespace)',
                'Slot_pr4': 'bool(project.variables.namespace)',
                'Slot_pr5': 'dict(project.variables.namespace)',
                'Slot_pr6': 'list(project.variables.namespace)'
            })


if __name__ == '__main__':
    unittest.main()
