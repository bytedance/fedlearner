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

from google.protobuf.json_format import MessageToDict

from fedlearner_webconsole.db import Session
from fedlearner_webconsole.exceptions import InternalException
from fedlearner_webconsole.proto import serving_pb2
from fedlearner_webconsole.serving.models import ServingNegotiator
from fedlearner_webconsole.serving.services import NegotiatorServingService


class ParticipantFetcher:
    _TF_DT_INT_TYPE_SET = ['DT_INT32', 'DT_INT16', 'DT_UINT16', 'DT_INT8', 'DT_UINT8']

    def __init__(self, session: Session = None):
        self._session = session

    def fetch(self, serving_negotiator: ServingNegotiator, example_id: str) -> dict:
        if serving_negotiator.is_local:
            return {}
        resp = NegotiatorServingService(self._session).participant_serving_service_inference(
            serving_negotiator, example_id)
        if resp.code != serving_pb2.SERVING_SERVICE_SUCCESS:
            raise InternalException(resp.msg)
        data = MessageToDict(resp.data)
        participant_result = data['result']
        signature = serving_negotiator.serving_model.signature
        signature_dict = json.loads(signature)
        signature_extend = signature_dict['from_participants']
        assert len(signature_extend) == len(participant_result), \
            f'Dim not match, need {len(signature_extend)}, got {len(participant_result)}'
        result = {}
        for item_key in participant_result:
            if item_key not in signature_extend and len(participant_result) > 1:
                continue
            input_key = item_key
            if len(participant_result) == 1:
                input_key = list(signature_extend.keys())[0]
            dtype = participant_result[item_key]['dtype']
            result[input_key] = self._get_value_by_dtype(dtype, participant_result[item_key])
        return result

    def _get_value_by_dtype(self, dtype: str, input_data: dict):
        if dtype == 'DT_FLOAT':
            return input_data['floatVal']
        if dtype == 'DT_DOUBLE':
            return input_data['doubleVal']
        if dtype == self._TF_DT_INT_TYPE_SET:
            return input_data['intVal']
        if dtype == 'DT_INT64':
            return input_data['int64Val']
        if dtype == 'DT_UINT32':
            return input_data['uint32Val']
        if dtype == 'DT_UINT64':
            return input_data['uint64Val']
        if dtype == 'DT_STRING':
            return input_data['stringVal']
        if dtype == 'DT_BOOL':
            return input_data['boolVal']
        return ''
