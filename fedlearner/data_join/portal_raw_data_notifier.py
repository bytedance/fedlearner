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

import logging
import threading
from datetime import timedelta

from tensorflow.compat.v1 import gfile
from google.protobuf import empty_pb2

from fedlearner.common import data_join_service_pb2_grpc as dj_grpc
from fedlearner.proxy.channel import make_insecure_channel, ChannelType

from fedlearner.data_join import common
from fedlearner.data_join.raw_data_controller import RawDataController
from fedlearner.data_join.routine_worker import RoutineWorker

class PortalRawDataNotifier(object):
    class NotifyCtx(object):
        def __init__(self, master_addr):
            self._master_addr = master_addr
            channel = make_insecure_channel(master_addr, ChannelType.INTERNAL)
            self._master_cli = dj_grpc.DataJoinMasterServiceStub(channel)
            self._data_source = None
            self._raw_date_ctl = None
            self._raw_data_updated_datetime = {}

        @property
        def data_source(self):
            if self._data_source is None:
                self._data_source = \
                        self._master_cli.GetDataSource(empty_pb2.Empty())
            return self._data_source

        def get_raw_data_updated_datetime(self, partition_id):
            if partition_id not in self._raw_data_updated_datetime:
                ts = self._raw_date_controller.get_raw_data_latest_timestamp(
                        partition_id
                    )
                if ts.seconds > 3600:
                    ts.seconds -= 3600
                else:
                    ts.seconds = 0
                self._raw_data_updated_datetime[partition_id] = \
                        common.convert_timestamp_to_datetime(
                                common.trim_timestamp_by_hourly(ts)
                            )
            return self._raw_data_updated_datetime[partition_id]

        def add_raw_data(self, partition_id, fpaths, timestamps, end_ts):
            assert len(fpaths) == len(timestamps), \
                "the number of raw data path and timestamp should same"
            if len(fpaths) > 0:
                self._raw_date_controller.add_raw_data(partition_id, fpaths,
                                                       True, timestamps)
                self._raw_data_updated_datetime[partition_id] = end_ts

        @property
        def data_source_master_addr(self):
            return self._master_addr

        @property
        def _raw_date_controller(self):
            if self._raw_date_ctl is None:
                self._raw_date_ctl = RawDataController(self.data_source,
                                                       self._master_cli)
            return self._raw_date_ctl

    def __init__(self, etcd, portal_name, downstream_data_source_masters):
        self._lock = threading.Lock()
        self._etcd = etcd
        self._portal_name = portal_name
        assert len(downstream_data_source_masters) > 0, \
            "PortalRawDataNotifier launched when has master to notify"
        self._master_notify_ctx = {}
        for addr in downstream_data_source_masters:
            self._master_notify_ctx[addr] = \
                    PortalRawDataNotifier.NotifyCtx(addr)
        self._notify_worker = None
        self._started = False

    def start_notify_worker(self):
        with self._lock:
            if not self._started:
                assert self._notify_worker is None, \
                    "notify worker should be None if not started"
                self._notify_worker = RoutineWorker(
                        'potral-raw_data-notifier',
                        self._raw_data_notify_fn,
                        self._raw_data_notify_cond, 5
                    )
                self._notify_worker.start_routine()
                self._started = True
            self._notify_worker.wakeup()

    def stop_notify_worker(self):
        notify_worker = None
        with self._lock:
            notify_worker = self._notify_worker
            self._notify_worker = None
        if notify_worker is not None:
            notify_worker.stop_routine()

    def _check_partition_num(self, notify_ctx, portal_manifest):
        assert isinstance(notify_ctx, PortalRawDataNotifier.NotifyCtx)
        data_source = notify_ctx.data_source
        ds_partition_num = data_source.data_source_meta.partition_num
        if portal_manifest.output_partition_num % ds_partition_num != 0:
            raise ValueError(
                    "the partition number({}) of down stream data source "\
                    "{} should be divised by output partition of "\
                    "portatl({})".format(ds_partition_num,
                    data_source.data_source_meta.name,
                    portal_manifest.output_partition_num)
                )

    def _add_raw_data_impl(self, notify_ctx, portal_manifest, ds_pid):
        dt = notify_ctx.get_raw_data_updated_datetime(ds_pid) + \
                timedelta(hours=1)
        begin_dt = common.convert_timestamp_to_datetime(
                common.trim_timestamp_by_hourly(
                    portal_manifest.begin_timestamp
                )
            )
        if dt < begin_dt:
            dt = begin_dt
        committed_dt = common.convert_timestamp_to_datetime(
                portal_manifest.committed_timestamp
            )
        fpaths = []
        timestamps = []
        ds_ptnum = notify_ctx.data_source.data_source_meta.partition_num
        while dt <= committed_dt:
            for pt_pid in range(ds_pid,
                                portal_manifest.output_partition_num,
                                ds_ptnum):
                fpath = common.encode_portal_hourly_fpath(
                        portal_manifest.output_data_base_dir,
                        dt, pt_pid
                    )
                if gfile.Exists(fpath):
                    fpaths.append(fpath)
                    timestamps.append(common.convert_datetime_to_timestamp(dt))
            if len(fpaths) > 32 or dt == committed_dt:
                break
            dt += timedelta(hours=1)
        notify_ctx.add_raw_data(ds_pid, fpaths, timestamps, dt)
        logging.info("add %d raw data file for partition %d of data "\
                     "source %s. latest updated datetime %s",
                      len(fpaths), ds_pid,
                      notify_ctx.data_source.data_source_meta.name, dt)
        return dt >= committed_dt

    def _notify_one_data_source(self, notify_ctx, portal_manifest):
        assert isinstance(notify_ctx, PortalRawDataNotifier.NotifyCtx)
        try:
            self._check_partition_num(notify_ctx, portal_manifest)
            ds_ptnum = notify_ctx.data_source.data_source_meta.partition_num
            pt_ptnum = portal_manifest.output_partition_num
            add_finished = False
            while not add_finished:
                add_finished = True
                for ds_pid in range(ds_ptnum):
                    if not self._add_raw_data_impl(notify_ctx,
                                                   portal_manifest,
                                                   ds_pid):
                        add_finished = False
        except Exception as e: # pylint: disable=broad-except
            logging.error("Failed to notify data source[master-addr: %s] "\
                          "new raw data added, reason %s",
                          notify_ctx.data_source_master_addr, e)

    def _raw_data_notify_fn(self):
        portal_manifest = common.retrieve_portal_manifest(
                self._etcd, self._portal_name
            )
        for _, notify_ctx in self._master_notify_ctx.items():
            self._notify_one_data_source(notify_ctx, portal_manifest)

    def _raw_data_notify_cond(self):
        return True
