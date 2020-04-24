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
from google.protobuf import text_format
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common import common_pb2 as common_pb
from fedlearner.data_join import common

class RawDataManifestManager(object):
    def __init__(self, etcd, data_source):
        self._lock = threading.Lock()
        self._local_manifest = {}
        self._etcd = etcd
        self._data_source = data_source
        self._existed_fpath = {}
        self._raw_data_latest_timestamp = {}
        self._partition_num = data_source.data_source_meta.partition_num
        if self._partition_num <= 0:
            raise ValueError(
                "partition num must be positive: {}".format(self._partition_num)
            )
        for partition_id in range(self._partition_num):
            self._local_manifest[partition_id] = None
            self._raw_data_latest_timestamp[partition_id] = None
            self._sync_manifest(partition_id)

    def alloc_sync_exampld_id(self, rank_id, partition_id=None):
        if partition_id is not None:
            self._check_partition_id(partition_id)
        with self._lock:
            return self._alloc_partition(
                    'sync_example_id_rep', dj_pb.SyncExampleIdState.UnSynced,
                     dj_pb.SyncExampleIdState.Syncing, rank_id, partition_id
                )

    def alloc_join_example(self, rank_id, partition_id=None):
        if partition_id is not None:
            self._check_partition_id(partition_id)
        with self._lock:
            return self._alloc_partition(
                    'join_example_rep', dj_pb.JoinExampleState.UnJoined,
                     dj_pb.JoinExampleState.Joining, rank_id, partition_id
                )

    def finish_sync_example_id(self, rank_id, partition_id):
        self._check_partition_id(partition_id)
        with self._lock:
            if self._is_data_join_leader():
                manifest = self._sync_manifest(partition_id)
                if not manifest.finished:
                    raise RuntimeError(
                            "Failed to finish sync example id for " \
                            "partition {} since raw data is not " \
                            "finished".format(partition_id)
                        )
            self._finish_partition(
                    'sync_example_id_rep', dj_pb.SyncExampleIdState.Syncing,
                     dj_pb.SyncExampleIdState.Synced, rank_id, partition_id
                )

    def finish_join_example(self, rank_id, partition_id):
        self._check_partition_id(partition_id)
        with self._lock:
            manifest = self._sync_manifest(partition_id)
            assert manifest is not None, \
                "manifest must be not None for a valid partition"
            if manifest.sync_example_id_rep.state != \
                    dj_pb.SyncExampleIdState.Synced:
                raise RuntimeError(
                        "not allow finish join example for " \
                        "partition {} since sync example id is " \
                        "not finished".format(partition_id)
                    )
            if not self._is_data_join_leader() and not manifest.finished:
                raise RuntimeError(
                        "Failed to finish join example for partition {} "\
                        "since raw data is not finished".format(partition_id)
                    )
            self._finish_partition(
                    'join_example_rep', dj_pb.JoinExampleState.Joining,
                     dj_pb.JoinExampleState.Joined, rank_id, partition_id
                )

    def finish_raw_data(self, partition_id):
        self._check_partition_id(partition_id)
        with self._lock:
            manifest = self._sync_manifest(partition_id)
            if not manifest.finished:
                manifest.finished = True
                self._update_manifest(manifest)

    def add_raw_data(self, partition_id, raw_data_metas, dedup):
        self._check_partition_id(partition_id)
        with self._lock:
            manifest = self._sync_manifest(partition_id)
            if manifest.finished:
                raise RuntimeError("forbid add raw data since partition {} "\
                                    "has finished!".format(partition_id))
            input_fpath = set()
            add_candidates = []
            for raw_date_meta in raw_data_metas:
                if raw_date_meta.file_path in self._existed_fpath or \
                        raw_date_meta.file_path in input_fpath:
                    if not dedup:
                        raise RuntimeError("file {} has been added"\
                                           .format(raw_date_meta.file_path))
                    continue
                input_fpath.add(raw_date_meta.file_path)
                add_candidates.append(raw_date_meta)
            self._local_manifest[partition_id] = None
            process_index = manifest.next_process_index
            for raw_date_meta in add_candidates:
                etcd_key = common.raw_data_meta_etcd_key(
                        self._data_source.data_source_meta.name,
                        partition_id, process_index
                    )
                raw_date_meta.start_index = -1
                data = text_format.MessageToString(raw_date_meta)
                self._etcd.set_data(etcd_key, data)
                self._existed_fpath[raw_date_meta.file_path] = \
                        (partition_id, process_index)
                self._update_raw_data_latest_timestamp(
                        partition_id, raw_date_meta.timestamp
                    )
                process_index += 1
            if manifest.next_process_index != process_index:
                manifest.next_process_index = process_index
                self._update_manifest(manifest)
            else:
                self._local_manifest[partition_id] = manifest

    def forward_peer_dumped_index(self, partition_id, peer_dumped_index):
        self._check_partition_id(partition_id)
        with self._lock:
            manifest = self._sync_manifest(partition_id)
            if manifest.peer_dumped_index < peer_dumped_index:
                manifest.peer_dumped_index = peer_dumped_index
                self._update_manifest(manifest)

    def list_all_manifest(self):
        with self._lock:
            manifest_map = {}
            for partition_id in self._local_manifest:
                manifest_map[partition_id] = self._sync_manifest(partition_id)
            return manifest_map

    def get_manifest(self, partition_id):
        self._check_partition_id(partition_id)
        with self._lock:
            return self._sync_manifest(partition_id)

    def get_raw_date_latest_timestamp(self, partition_id):
        self._check_partition_id(partition_id)
        with self._lock:
            self._sync_manifest(partition_id)
            return self._raw_data_latest_timestamp[partition_id]

    def _is_data_join_leader(self):
        return self._data_source.role == common_pb.FLRole.Leader

    def _alloc_partition(self, field_name, src_state,
                         target_state, rank_id, partition_id=None):
        if partition_id is None:
            for ptn_id in self._local_manifest:
                manifest = self._sync_manifest(ptn_id)
                assert manifest is not None, \
                    "manifest must be not None for a valid partition"
                field = getattr(manifest, field_name)
                if field.state == target_state and field.rank_id == rank_id:
                    partition_id = ptn_id
                    break
                if field.state == src_state and partition_id is None:
                    partition_id = ptn_id
        if partition_id is not None:
            manifest = self._sync_manifest(partition_id)
            field = getattr(manifest, field_name)
            if field.state == src_state:
                field.state = target_state
                field.rank_id = rank_id
                self._update_manifest(manifest)
            elif field.state == target_state:
                if field.rank_id != rank_id:
                    raise RuntimeError(
                            "field {} of partition {} has been allcate " \
                            "to {} as state {}".format(field_name, partition_id,
                            field.rank_id, field.state)
                        )
            else:
                raise RuntimeError(
                        "field {} of partition {} at state {}".format(
                            field_name, partition_id, field.state)
                    )
            return manifest
        return None

    def _finish_partition(self, field_name, src_state,
                          target_state, rank_id, partition_id):
        manifest = self._sync_manifest(partition_id)
        field = getattr(manifest, field_name)
        if field.state == target_state:
            return
        if field.state != src_state:
            raise RuntimeError(
                    "partition {} is not allow finished".format(partition_id)
                )
        if field.rank_id != rank_id:
            raise RuntimeError(
                    "partition {} has been allocated to {}".format(
                    partition_id, field.rank_id)
                )
        field.state = target_state
        self._update_manifest(manifest)

    def _get_manifest(self, partition_id):
        manifest_etcd_key = common.partition_manifest_etcd_key(
                self._data_source.data_source_meta.name,
                partition_id
            )
        manifest_data = self._etcd.get_data(manifest_etcd_key)
        if manifest_data is not None:
            return text_format.Parse(manifest_data, dj_pb.RawDataManifest())
        return None

    def _update_manifest(self, manifest):
        partition_id = manifest.partition_id
        manifest_etcd_key = common.partition_manifest_etcd_key(
                self._data_source.data_source_meta.name,
                partition_id
            )
        self._local_manifest[partition_id] = None
        self._etcd.set_data(manifest_etcd_key,
                            text_format.MessageToString(manifest))
        self._local_manifest[partition_id] = manifest

    def _sync_manifest(self, partition_id):
        assert partition_id in self._local_manifest, \
            "partition {} should in local manifest".format(partition_id)
        if self._local_manifest[partition_id] is None:
            manifest = self._get_manifest(partition_id)
            if manifest is None:
                manifest = dj_pb.RawDataManifest()
                manifest.sync_example_id_rep.rank_id = -1
                manifest.join_example_rep.rank_id = -1
                manifest.partition_id = partition_id
                self._update_manifest(manifest)
            self._process_next_process_index(partition_id, manifest)
        return self._local_manifest[partition_id]

    def _check_partition_id(self, partition_id):
        if partition_id < 0 or partition_id >= self._partition_num:
            raise IndexError(
                    "partition id {} is out of range".format(partition_id)
                )

    def _process_next_process_index(self, partition_id, manifest):
        assert manifest is not None and manifest.partition_id == partition_id
        next_process_index = manifest.next_process_index
        while True:
            meta_etcd_key = \
                    common.raw_data_meta_etcd_key(
                            self._data_source.data_source_meta.name,
                            partition_id, next_process_index
                        )
            data = self._etcd.get_data(meta_etcd_key)
            if data is None:
                break
            meta = text_format.Parse(data, dj_pb.RawDataMeta())
            self._existed_fpath[meta.file_path] = \
                    (partition_id, next_process_index)
            self._update_raw_data_latest_timestamp(partition_id,
                                                   meta.timestamp)
            next_process_index += 1
        if next_process_index != manifest.next_process_index:
            manifest.next_process_index = next_process_index
            self._update_manifest(manifest)
        else:
            self._local_manifest[partition_id] = manifest

    def _update_raw_data_latest_timestamp(self, partition_id, ntimestamp):
        otimestamp = self._raw_data_latest_timestamp[partition_id]
        if otimestamp is None or \
                (ntimestamp.seconds > otimestamp.seconds or
                    (ntimestamp.seconds == otimestamp.seconds and
                     ntimestamp.nanos > otimestamp.nanos)):
            self._raw_data_latest_timestamp[partition_id] = ntimestamp
