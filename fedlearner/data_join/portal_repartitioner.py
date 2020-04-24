# Copyright 2020 The FedLearner Authors. All Rights Reserved.
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

import threading
import bisect
from datetime import timedelta

from tensorflow.compat.v1 import gfile

from fedlearner.common import common_pb2 as common_pb
import fedlearner.data_join.portal_hourly_input_reducer as portal_reducer
import fedlearner.data_join.portal_hourly_output_mapper as portal_mapper
from fedlearner.data_join.routine_worker import RoutineWorker
from fedlearner.data_join import common

class PortalRepartitioner(object):
    def __init__(self, etcd, portal_manifest, portal_options):
        self._lock = threading.Lock()
        self._etcd = etcd
        self._portal_manifest = portal_manifest
        self._portal_options = portal_options
        self._started = False
        self._input_ready_datetime = []
        self._output_finished_datetime = []
        self._worker_map = {}

    def start_routine_workers(self):
        with self._lock:
            if not self._started:
                self._worker_map = {
                    self._input_data_ready_sniffer_name(): RoutineWorker(
                    self._input_data_ready_sniffer_name(),
                    self._input_data_ready_sniff_fn,
                    self._input_data_ready_sniff_cond, 5),

                    self._repart_executor_name(): RoutineWorker(
                    self._repart_executor_name(),
                    self._repart_execute_fn,
                    self._repart_execute_cond, 5),

                    self._committed_datetime_forwarder_name(): RoutineWorker(
                    self._committed_datetime_forwarder_name(),
                    self._committed_datetime_forward_fn,
                    self._committed_datetime_forward_cond, 5)
                }
                self._started = True
                for _, w in self._worker_map.items():
                    w.start_routine()
                self._started = True

    def stop_routine_workers(self):
        wait_join = True
        with self._lock:
            if self._started:
                wait_join = True
                self._started = False
        if wait_join:
            for w in self._worker_map.values():
                w.stop_routine()

    @classmethod
    def _input_data_ready_sniffer_name(cls):
        return 'input-data-ready-sniffer'

    @classmethod
    def _repart_executor_name(cls):
        return 'repart-executor'

    @classmethod
    def _committed_datetime_forwarder_name(cls):
        return 'committed-datetime-forwarder'

    def _ready_input_data_count(self):
        with self._lock:
            return len(self._input_ready_datetime)

    def _check_datetime_stale(self, date_time):
        with self._lock:
            committed_datetime = common.convert_timestamp_to_datetime(
                    common.trim_timestamp_by_hourly(
                        self._portal_manifest.committed_timestamp
                    )
                )
            if date_time > committed_datetime:
                idx = bisect.bisect_left(self._input_ready_datetime,
                                         date_time)
                if idx < len(self._input_ready_datetime) and \
                        self._input_ready_datetime[idx] == date_time:
                    return True
                idx = bisect.bisect_left(self._output_finished_datetime,
                                         date_time)
                if idx < len(self._output_finished_datetime) and \
                        self._output_finished_datetime[idx] == date_time:
                    return True
                return False
            return True

    def _check_input_data_ready(self, date_time):
        finish_tag = common.encode_portal_hourly_finish_tag(
                self._portal_manifest.input_data_base_dir, date_time
            )
        return gfile.Exists(finish_tag)

    def _check_output_data_finish(self, date_time):
        finish_tag = common.encode_portal_hourly_finish_tag(
                self._portal_manifest.output_data_base_dir, date_time
            )
        return gfile.Exists(finish_tag)

    def _put_input_ready_datetime(self, date_time):
        with self._lock:
            idx = bisect.bisect_left(self._input_ready_datetime, date_time)
            if idx == len(self._input_ready_datetime) or \
                    self._input_ready_datetime[idx] != date_time:
                self._input_ready_datetime.insert(idx, date_time)

    def _get_potral_manifest(self):
        with self._lock:
            return self._portal_manifest

    @classmethod
    def _get_required_datetime(cls, portal_manifest):
        committed_datetime = common.convert_timestamp_to_datetime(
                common.trim_timestamp_by_hourly(
                    portal_manifest.committed_timestamp
                )
            )
        begin_datetime = common.convert_timestamp_to_datetime(
                common.trim_timestamp_by_hourly(
                    portal_manifest.begin_timestamp
                )
            )
        if begin_datetime >= committed_datetime + timedelta(hours=1):
            return begin_datetime
        return committed_datetime + timedelta(hours=1)

    def _wakeup_input_data_ready_sniffer(self):
        self._worker_map[self._input_data_ready_sniffer_name()].wakeup()

    def _input_data_ready_sniff_fn(self):
        committed_datetime = None
        date_time = None
        end_datetime = None
        with self._lock:
            date_time = self._get_required_datetime(self._portal_manifest)
            end_datetime = date_time + timedelta(days=1)
        assert date_time is not None and end_datetime is not None
        while date_time < end_datetime:
            if not self._check_datetime_stale(date_time) and \
                    self._check_input_data_ready(date_time):
                self._put_input_ready_datetime(date_time)
            date_time += timedelta(hours=1)
        if self._ready_input_data_count() > 0:
            self._wakeup_repart_executor()

    def _input_data_ready_sniff_cond(self):
        return self._ready_input_data_count() < 24

    def _get_next_input_ready_datetime(self):
        while self._ready_input_data_count() > 0:
            date_time = None
            with self._lock:
                if len(self._input_ready_datetime) == 0:
                    break
                date_time = self._input_ready_datetime[0]
            if not self._check_output_data_finish(date_time):
                return date_time
            self._transform_datetime_finished(date_time)
        return None

    def _transform_datetime_finished(self, date_time):
        with self._lock:
            idx = bisect.bisect_left(self._input_ready_datetime, date_time)
            if idx == len(self._input_ready_datetime) or \
                    self._input_ready_datetime[idx] != date_time:
                return
            self._input_ready_datetime.pop(idx)
            idx = bisect.bisect_left(self._output_finished_datetime,
                                     date_time)
            if idx == len(self._output_finished_datetime) or \
                    self._output_finished_datetime[idx] != date_time:
                self._output_finished_datetime.insert(idx, date_time)

    def _update_portal_commited_timestamp(self, new_committed_datetime):
        new_manifest = None
        with self._lock:
            old_committed_datetime = common.convert_timestamp_to_datetime(
                    common.trim_timestamp_by_hourly(
                        self._portal_manifest.committed_timestamp
                    )
                )
            assert new_committed_datetime > old_committed_datetime
            new_manifest = common_pb.DataJoinPortalManifest()
            new_manifest.MergeFrom(self._portal_manifest)
        assert new_manifest is not None
        new_manifest.committed_timestamp.MergeFrom(
                common.trim_timestamp_by_hourly(
                    common.convert_datetime_to_timestamp(
                        new_committed_datetime
                    )
                )
            )
        common.commit_portal_manifest(self._etcd, new_manifest)
        return new_manifest

    def _wakeup_repart_executor(self):
        self._worker_map[self._repart_executor_name()].wakeup()

    def _repart_execute_fn(self):
        while True:
            date_time = self._get_next_input_ready_datetime()
            if date_time is None:
                break
            repart_reducer = portal_reducer.PotralHourlyInputReducer(
                    self._get_potral_manifest(),
                    self._portal_options, date_time
                )
            repart_mapper = portal_mapper.PotralHourlyOutputMapper(
                    self._get_potral_manifest(),
                    self._portal_options, date_time
                )
            for item in repart_reducer.make_reducer():
                repart_mapper.map_data(item)
            repart_mapper.finish_map()
            self._transform_datetime_finished(date_time)
            self._wakeup_committed_datetime_forwarder()
            self._wakeup_input_data_ready_sniffer()

    def _repart_execute_cond(self):
        with self._lock:
            return len(self._input_ready_datetime) > 0

    def _wakeup_committed_datetime_forwarder(self):
        self._worker_map[self._committed_datetime_forwarder_name()].wakeup()

    def _committed_datetime_forward_fn(self):
        new_committed_datetime = None
        updated = False
        with self._lock:
            required_datetime = self._get_required_datetime(
                    self._portal_manifest
                )
            idx = bisect.bisect_left(self._output_finished_datetime,
                                     required_datetime)
            for date_time in self._output_finished_datetime[idx:]:
                required_datetime = date_time
                if date_time != required_datetime:
                    break
                new_committed_datetime = required_datetime
                required_datetime += timedelta(hours=1)
                updated = True
        if updated:
            assert new_committed_datetime is not None
            updated_manifest = \
                    self._update_portal_commited_timestamp(
                            new_committed_datetime
                        )
            with self._lock:
                self._portal_manifest = updated_manifest
                skip_cnt = 0
                for date_time in self._output_finished_datetime:
                    if date_time <= new_committed_datetime:
                        skip_cnt += 1
                self._output_finished_datetime = \
                        self._output_finished_datetime[skip_cnt:]
            self._wakeup_input_data_ready_sniffer()

    def _committed_datetime_forward_cond(self):
        with self._lock:
            required_datetime = \
                    self._get_required_datetime(self._portal_manifest)
            idx = bisect.bisect_left(self._output_finished_datetime,
                                     required_datetime)
            return idx < len(self._output_finished_datetime) and \
                    self._output_finished_datetime[idx] == required_datetime
