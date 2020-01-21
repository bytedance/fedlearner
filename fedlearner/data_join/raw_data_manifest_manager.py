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
import os
from google.protobuf import text_format

from fedlearner.common import data_join_service_pb2 as dj_pb

class RawDataManifestManager(object):
    def __init__(self, etcd, data_source):
        self._lock = threading.Lock()
        self._local_manifest = {}
        self._etcd = etcd
        self._data_source = data_source
        self._partition_num = data_source.data_source_meta.partition_num
        if self._partition_num <= 0:
            raise ValueError(
                "partition num must be positive: {}".format(self._partition_num)
            )
        for partition_id in range(self._partition_num):
            self._init_manifest(partition_id)

    def alloc_unallocated_partition(self, rank_id, partition_id=None):
        if partition_id is not None:
            self._check_partition_id(partition_id)
        with self._lock:
            return self._alloc_partition(
                    dj_pb.RawDataState.UnAllocated,
                    dj_pb.RawDataState.Syncing,
                    rank_id,
                    partition_id
                )

    def alloc_synced_partition(self, rank_id, partition_id=None):
        if partition_id is not None:
            self._check_partition_id(partition_id)
        with self._lock:
            return self._alloc_partition(
                    dj_pb.RawDataState.Synced,
                    dj_pb.RawDataState.Joining,
                    rank_id,
                    partition_id
                )

    def finish_sync_partition(self, rank_id, partition_id):
        self._check_partition_id(partition_id)
        with self._lock:
            self._finish_partition(
                rank_id,
                partition_id,
                dj_pb.RawDataState.Syncing,
                dj_pb.RawDataState.Synced,
            )

    def finish_join_partition(self, rank_id, partition_id):
        self._check_partition_id(partition_id)
        with self._lock:
            self._finish_partition(
                rank_id,
                partition_id,
                dj_pb.RawDataState.Joining,
                dj_pb.RawDataState.Done,
            )

    def list_all_manifest(self):
        with self._lock:
            manifest_map = {}
            for partition_id in self._local_manifest:
                self._sync_manifest(partition_id)
                manifest_map[partition_id] = self._local_manifest[partition_id]
            return manifest_map

    def get_manifest(self, partition_id):
        self._check_partition_id(partition_id)
        with self._lock:
            self._sync_manifest(partition_id)
            return self._local_manifest[partition_id]

    def _alloc_partition(self, src_state, dst_state, rank_id, target_partition):
        finished = True
        if target_partition is None:
            for partition_id in self._local_manifest:
                self._sync_manifest(partition_id)
                manifest = self._local_manifest[partition_id]
                if manifest.state < src_state:
                    finished = False
                assert manifest is not None
                if (manifest.state == dst_state and
                        manifest.allocated_rank_id == rank_id):
                    return manifest, False
                if manifest.state == src_state and target_partition is None:
                    target_partition = partition_id
        if target_partition is not None:
            self._sync_manifest(target_partition)
            manifest = self._local_manifest[target_partition]
            if manifest.state == dst_state:
                if (manifest.allocated_rank_id != rank_id and
                        manifest.allocated_rank_id >= 0):
                    raise RuntimeError(
                            "partition has been allcate to %d as state %d" %\
                            manifest.allcated_id, dst_state
                        )
                return manifest, False
            if manifest.state != src_state:
                raise RuntimeError("partition not in state %d" % src_state)
            manifest.state = dst_state
            manifest.allocated_rank_id = rank_id
            self._update_manifest(target_partition, manifest)
            return self._local_manifest[target_partition], False
        return None, finished

    def _finish_partition(self, rank_id, partition_id, src_state, dst_state):
        manifest = self._get_manifest(partition_id)
        if manifest.state < src_state:
            raise RuntimeError("partition-%d manifest at state %d" %\
                                partition_id, manifest.state)
        if manifest.state == src_state:
            if manifest.allocated_rank_id != rank_id:
                raise RuntimeError("partition-%d has been allocated to %d" %\
                                    partition_id, manifest.allocated_rank_id)
            manifest.state = dst_state
            manifest.allocated_rank_id = -1
            self._update_manifest(partition_id, manifest)

    def _init_manifest(self, partition_id):
        mainfest = self._get_manifest(partition_id)
        if mainfest is None:
            manifest = dj_pb.RawDataManifest()
            manifest.state = dj_pb.RawDataState.UnAllocated
            manifest.partition_id = partition_id
            manifest.allocated_rank_id = -1
            self._update_manifest(partition_id, manifest)
        self._local_manifest[partition_id] = mainfest

    def _get_manifest_etcd_key(self, partition_id):
        return os.path.join(self._data_source.data_source_meta.name,
                            'raw_data_dir',
                            'partition_{}'.format(partition_id))

    def _get_manifest(self, partition_id):
        manifest_etcd_key = self._get_manifest_etcd_key(partition_id)
        manifest_data = self._etcd.get_data(manifest_etcd_key)
        if manifest_data is not None:
            return text_format.Parse(manifest_data, dj_pb.RawDataManifest())
        return None

    def _update_manifest(self, partition_id, manifest):
        manifest_etcd_key = self._get_manifest_etcd_key(partition_id)
        self._local_manifest[partition_id] = None
        self._etcd.set_data(manifest_etcd_key,
                            text_format.MessageToString(manifest))
        self._local_manifest[partition_id] = manifest

    def _sync_manifest(self, partition_id):
        if (partition_id in self._local_manifest and
                self._local_manifest[partition_id] is None):
            manifest = self._get_manifest(partition_id)
            self._local_manifest[partition_id] = manifest

    def _check_partition_id(self, partition_id):
        if partition_id < 0 or partition_id >= self._partition_num:
            raise IndexError(
                    "partition id {} is out of range".format(partition_id)
                )
