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

import abc
from typing import Union
from sqlalchemy.orm import Session

from fedlearner_webconsole.dataset.models import DatasetJobKind
from fedlearner_webconsole.dataset.job_configer.base_configer import BaseConfiger
from fedlearner_webconsole.dataset.job_configer.import_source_configer import ImportSourceConfiger
from fedlearner_webconsole.dataset.job_configer.data_alignment_configer import DataAlignmentConfiger
from fedlearner_webconsole.dataset.job_configer.rsa_psi_data_join_configer import RsaPsiDataJoinConfiger
from fedlearner_webconsole.dataset.job_configer.export_configer import ExportConfiger
from fedlearner_webconsole.dataset.job_configer.light_client_rsa_psi_data_join_configer import \
    LightClientRsaPsiDataJoinConfiger
from fedlearner_webconsole.dataset.job_configer.ot_psi_data_join_configer import OtPsiDataJoinConfiger
from fedlearner_webconsole.dataset.job_configer.light_client_ot_psi_data_join_configer import \
    LightClientOtPsiDataJoinConfiger
from fedlearner_webconsole.dataset.job_configer.hash_data_join_configer import HashDataJoinConfiger
from fedlearner_webconsole.dataset.job_configer.analyzer_configer import AnalyzerConfiger


class DatasetJobConfiger(metaclass=abc.ABCMeta):

    @classmethod
    def from_kind(cls, kind: Union[DatasetJobKind, str], session: Session) -> BaseConfiger:
        hanlders_mapper = {
            DatasetJobKind.IMPORT_SOURCE: ImportSourceConfiger,
            DatasetJobKind.DATA_ALIGNMENT: DataAlignmentConfiger,
            DatasetJobKind.RSA_PSI_DATA_JOIN: RsaPsiDataJoinConfiger,
            DatasetJobKind.EXPORT: ExportConfiger,
            DatasetJobKind.LIGHT_CLIENT_RSA_PSI_DATA_JOIN: LightClientRsaPsiDataJoinConfiger,
            DatasetJobKind.OT_PSI_DATA_JOIN: OtPsiDataJoinConfiger,
            DatasetJobKind.LIGHT_CLIENT_OT_PSI_DATA_JOIN: LightClientOtPsiDataJoinConfiger,
            DatasetJobKind.HASH_DATA_JOIN: HashDataJoinConfiger,
            DatasetJobKind.ANALYZER: AnalyzerConfiger,
        }

        if isinstance(kind, str):
            kind = DatasetJobKind(kind)

        return hanlders_mapper[kind](session)
