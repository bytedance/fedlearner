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

from typing import Optional

from sqlalchemy.orm import Session

from fedlearner_webconsole.exceptions import NotFoundException
from fedlearner_webconsole.mmgr.models import Model
from fedlearner_webconsole.serving.models import ServingNegotiator


def get_model(model_id: int, session: Session) -> Model:
    model = session.query(Model).get(model_id)
    if model is None:
        raise NotFoundException(f'[Serving] model {model_id} is not found')
    return model


def get_serving_negotiator_by_serving_model_id(serving_model_id: int, session: Session) -> Optional[ServingNegotiator]:
    serving_negotiator = session.query(ServingNegotiator).filter_by(serving_model_id=serving_model_id).one_or_none()
    return serving_negotiator
