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

from pp_lite.utils.tools import print_named_dict


class Handler(object):

    def emit_counter(self, key: str, value: int):
        """
        Different handler has different count strategy.
        This version is intended to be implemented by subclasses so raises a NotImplementedError.
        """
        raise NotImplementedError('Emit must be implemented by Handler subclasses')


class AuditHandler(Handler):

    def __init__(self, interval: int = 50):
        super().__init__()
        self._audit_metrics = {}
        self._step = 0
        self._INTERVAL = interval

    def emit_counter(self, key: str, value: int):
        self._audit_metrics[key] = self._audit_metrics.get(key, 0) + value
        self._step += 1
        if self._step % self._INTERVAL == 0:
            self.show_audit_info()

    def get_value(self, key: str) -> int:
        return self._audit_metrics.get(key, 0)

    def show_audit_info(self):
        if not self._audit_metrics:
            return
        print_named_dict(name='Audit', target_dict=self._audit_metrics)


_audit_client = AuditHandler()

emit_counter = _audit_client.emit_counter
get_audit_value = _audit_client.get_value
show_audit_info = _audit_client.show_audit_info
