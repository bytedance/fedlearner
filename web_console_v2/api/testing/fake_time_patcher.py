# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
import time
from datetime import datetime, timezone
from unittest.mock import patch
import freezegun


class FakeTimePatcher:

    def start(self, initial_time: datetime = datetime.now(timezone.utc)):

        def _prod_fake_sleep(seconds: int):
            time.sleep(seconds / 1000)

        self.sleep_path = patch('fedlearner_webconsole.utils.pp_time.sleep', _prod_fake_sleep)
        self.sleep_path.start()
        # Freezegun will freeze all datetime used,
        # sometimes it's desired to ignore FreezeGun behaviour for particular packages.
        # (It will ignore some builtin packages such as Thread by default.)
        freezegun.configure(extend_ignore_list=['tensorflow'])
        self.freezer = freezegun.freeze_time(initial_time)
        self.fake_clock = self.freezer.start()
        # Freezegun can not patch func.now automatically,
        # so you should add patcher like follower to patch func.now.
        # TODO(xiangyuxuan.prs): remove func.now in composer model.
        self.patch_func_now = patch('fedlearner_webconsole.composer.composer.func.now', datetime.now)
        self.patch_func_now.start()
        self.patch_model_func_now = patch('fedlearner_webconsole.composer.composer_service.func.now', datetime.now)
        self.patch_model_func_now.start()

    def stop(self):
        self.patch_func_now.stop()
        self.patch_model_func_now.stop()
        self.freezer.stop()
        self.sleep_path.stop()

    def interrupt(self, seconds: int):
        self.fake_clock.tick(seconds)
        time.sleep(2)
