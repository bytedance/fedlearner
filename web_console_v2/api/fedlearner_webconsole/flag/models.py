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

#  coding: utf-8
import inspect
import json
import logging
from envs import Envs


class _Flag(object):
    FLAGS_DICT = json.loads(Envs.FLAGS)

    def __init__(self, name: str, fallback_value):
        self.name = name
        self.value = fallback_value
        self._merge()

    def _merge(self):
        """Merge fallback values with those ones set using env"""
        value_from_env = self.FLAGS_DICT.get(self.name)

        # update the value of a flag if env exists and it is of the correct type
        if value_from_env is not None:
            if isinstance(value_from_env, type(self.value)):
                self.value = value_from_env
                logging.info(f'Setting flag {self.name} to {self.value}.')

            else:
                logging.warning(f"""
                Flag {self.name} is set of the wrong type, falling back to {self.value}.
                Expected: {type(self.value)}; Got: {type(value_from_env)}
                """)


class Flag(object):
    WORKSPACE_ENABLED = _Flag('workspace_enabled', False)
    USER_MANAGEMENT_ENABLED = _Flag('user_management_enabled', True)
    PRESET_TEMPLATE_EDIT_ENABLED = _Flag('preset_template_edit_enabled', False)
    BCS_SUPPORT_ENABLED = _Flag('bcs_support_enabled', False)
    TRUSTED_COMPUTING_ENABLED = _Flag('trusted_computing_enabled', True)
    TEE_MACHINE_DEPLOYED = _Flag('tee_machine_deployed', False)
    DASHBOARD_ENABLED = _Flag('dashboard_enabled', False)
    OT_PSI_ENABLED = _Flag('ot_psi_enabled', True)
    DATASET_STATE_FIX_ENABLED = _Flag('dataset_state_fix_enabled', False)
    HASH_DATA_JOIN_ENABLED = _Flag('hash_data_join_enabled', False)
    HELP_DOC_URL = _Flag('help_doc_url', '')
    MODEL_JOB_GLOBAL_CONFIG_ENABLED = _Flag('model_job_global_config_enabled', False)
    REVIEW_CENTER_CONFIGURATION = _Flag('review_center_configuration', '{}')
    # show dataset with auth status but auto authority
    DATASET_AUTH_STATUS_ENABLED = _Flag('dataset_auth_status_enabled', True)
    # decide whether to check auth status when create dataset_job
    DATASET_AUTH_STATUS_CHECK_ENABLED = _Flag('dataset_auth_status_check_enabled', False)
    # set true after we implement this rpc func
    LIST_DATASETS_RPC_ENABLED = _Flag('list_datasets_rpc_enabled', True)
    # set true after we implement this rpc func
    PENDING_PROJECT_ENABLED = _Flag('pending_project_enabled', True)
    DATA_BATCH_RERUN_ENABLED = _Flag('data_batch_rerun_enabled', True)


def get_flags() -> dict:
    """Construct a dictionary for flags"""
    dct = {}

    # Gets flags (members of Flag)
    # Ref: https://stackoverflow.com/questions/9058305/getting-attributes-of-a-class
    attributes = inspect.getmembers(Flag, lambda a: not inspect.isroutine(a))
    flags = [a for a in attributes if not (a[0].startswith('__') and a[0].endswith('__'))]
    for _, flag in flags:
        dct[flag.name] = flag.value

    return dct
