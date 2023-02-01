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

# pylint: disable=unsupported-assignment-operation
import json
import unittest

from google.protobuf.struct_pb2 import Struct, Value, ListValue

from fedlearner_webconsole.proto.testing.testing_pb2 import PrivateInfo, RichMessage, Tdata, Int64Message, StructWrapper
from fedlearner_webconsole.utils.proto import remove_secrets, to_dict, to_json, parse_from_json


class ProtoTest(unittest.TestCase):

    def test_remove_secrets(self):
        proto = RichMessage(
            field1='f1',
            field2=123,
            pinfo=PrivateInfo(pii='pii', non_pii='non pii'),
            infos=[PrivateInfo(pii='only pii'), PrivateInfo(non_pii='only non pii')],
            pinfo_map={
                'k1': PrivateInfo(non_pii='hello non pii'),
                'k2': PrivateInfo(pii='hello pii')
            },
            pstring_map={'s1': 'v1'},
            pstring_list=['p1'],
        )
        proto_without_secret = RichMessage(
            field1='f1',
            pinfo=PrivateInfo(non_pii='non pii'),
            infos=[PrivateInfo(), PrivateInfo(non_pii='only non pii')],
            pinfo_map={
                'k1': PrivateInfo(non_pii='hello non pii'),
                'k2': PrivateInfo()
            },
            pstring_map={'s1': ''},
        )
        self.assertEqual(remove_secrets(proto), proto_without_secret)

    def test_to_dict_with_secret(self):
        proto = RichMessage(field1='f1',
                            field2=123,
                            pinfo=PrivateInfo(pii='pii', non_pii='non pii'),
                            infos=[PrivateInfo(pii='only pii'),
                                   PrivateInfo(non_pii='only non pii')],
                            pinfo_map={
                                'k1': PrivateInfo(non_pii='hello non pii'),
                                'k2': PrivateInfo(pii='hello pii')
                            },
                            pstring_map={'s1': 'v1'},
                            pstring_list=['p1'])
        self.assertEqual(
            to_dict(proto), {
                'field1': 'f1',
                'field2': 123,
                'infos': [{
                    'pii': 'only pii',
                    'non_pii': ''
                }, {
                    'pii': '',
                    'non_pii': 'only non pii'
                }],
                'pinfo': {
                    'pii': 'pii',
                    'non_pii': 'non pii'
                },
                'pinfo_map': {
                    'k1': {
                        'non_pii': 'hello non pii',
                        'pii': ''
                    },
                    'k2': {
                        'non_pii': '',
                        'pii': 'hello pii'
                    }
                },
                'pstring_map': {
                    's1': 'v1'
                },
                'pstring_list': ['p1']
            })
        self.assertEqual(
            to_dict(proto, with_secret=False), {
                'field1': 'f1',
                'field2': 0,
                'infos': [{
                    'pii': '',
                    'non_pii': ''
                }, {
                    'pii': '',
                    'non_pii': 'only non pii'
                }],
                'pinfo': {
                    'pii': '',
                    'non_pii': 'non pii'
                },
                'pinfo_map': {
                    'k1': {
                        'non_pii': 'hello non pii',
                        'pii': ''
                    },
                    'k2': {
                        'non_pii': '',
                        'pii': ''
                    }
                },
                'pstring_map': {
                    's1': ''
                },
                'pstring_list': []
            })

    def test_to_dict_int64(self):
        proto = Int64Message(id=123456789,
                             uuid='123123',
                             project_id=666,
                             data=[Tdata(id=987), Tdata(projects=[1, 2, 3])])
        self.assertEqual(
            to_dict(proto), {
                'uuid':
                    '123123',
                'project_id':
                    666,
                'id':
                    123456789,
                'data': [
                    {
                        'id': 987,
                        'mappers': {},
                        'projects': [],
                        'tt': 'UNSPECIFIED',
                    },
                    {
                        'id': 0,
                        'mappers': {},
                        'projects': [1, 2, 3],
                        'tt': 'UNSPECIFIED',
                    },
                ]
            })

    def test_to_dict_struct(self):
        list_value = ListValue(values=[Value(string_value='string in list')])
        nested_struct = Struct()
        nested_struct['haha'] = 2.33
        struct = Struct()
        struct['nested_list'] = list_value
        struct['nested_struct'] = nested_struct

        struct_wrapper = StructWrapper(typed_value=Value(string_value='str'), struct=struct)
        self.assertEqual(to_dict(struct_wrapper), {
            'typed_value': 'str',
            'struct': {
                'nested_list': ['string in list'],
                'nested_struct': {
                    'haha': 2.33
                }
            }
        })

    def test_to_json(self):
        proto = RichMessage(field1='field1',
                            field2=123123,
                            pinfo=PrivateInfo(pii='pii', non_pii='non pii'),
                            pstring_map={'s1': 'v1'},
                            pstring_list=['p1'])
        self.assertEqual(
            json.loads(to_json(proto)), {
                'field1': 'field1',
                'field2': 123123,
                'pinfo': {
                    'pii': 'pii',
                    'non_pii': 'non pii'
                },
                'pstring_map': {
                    's1': 'v1'
                },
                'pstring_list': ['p1']
            })

    def test_parse_from_json(self):
        proto = RichMessage(field1='field1', field2=123123, pstring_map={'s1': 'v1'}, pstring_list=['p1'])
        self.assertEqual(
            to_dict(
                parse_from_json(
                    json.dumps({
                        'field1': 'field1',
                        'field2': 123123,
                        'pstring_map': {
                            's1': 'v1'
                        },
                        'pstring_list': ['p1'],
                        'unknown_f': '123'
                    }), RichMessage())), to_dict(proto))


if __name__ == '__main__':
    unittest.main()
