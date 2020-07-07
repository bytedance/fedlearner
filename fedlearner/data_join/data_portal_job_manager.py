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
import logging
from os import path
from fnmatch import fnmatch

from google.protobuf import text_format
from tensorflow.compat.v1 import gfile

from fedlearner.common import data_portal_service_pb2 as dp_pb

from fedlearner.data_join import common

class DataPortalJobManager(object):
    def __init__(self, etcd, portal_name, long_running):
        self._lock = threading.Lock()
        self._etcd = etcd
        self._portal_name = portal_name
        self._portal_manifest = None
        self._processing_job = None
        self._sync_portal_manifest()
        self._sync_processing_job()
        self._long_running = long_running
        assert self._portal_manifest is not None
        self._processed_fpath = set()
        for job_id in range(0, self._portal_manifest.next_job_id):
            job = self._sync_portal_job(job_id)
            assert job is not None and job.job_id == job_id
            for fpath in job.fpaths:
                self._processed_fpath.add(fpath)
        self._job_part_map = {}
        if self._portal_manifest.processing_job_id >= 0:
            self._check_processing_job_finished()
        if self._portal_manifest.processing_job_id < 0:
            self._launch_new_portal_job()

    def get_portal_manifest(self):
        with self._lock:
            return self._sync_portal_manifest()

    def alloc_task(self, rank_id):
        with self._lock:
            self._sync_processing_job()
            if self._processing_job is not None:
                partition_id = self._try_to_alloc_part(rank_id,
                                                       dp_pb.PartState.kInit,
                                                       dp_pb.PartState.kIdMap)
                if partition_id is not None:
                    return False, self._create_map_task(rank_id, partition_id)
                if self._all_job_part_mapped() and \
                        (self._portal_manifest.data_portal_type ==
                                dp_pb.DataPortalType.Streaming):
                    partition_id = self._try_to_alloc_part(
                            rank_id,
                            dp_pb.PartState.kIdMapped,
                            dp_pb.PartState.kEventTimeReduce
                        )
                    if partition_id is not None:
                        return False, self._create_reduce_task(partition_id)
                return (not self._long_running and
                            self._all_job_part_finished()), None
            return not self._long_running, None

    def finish_task(self, rank_id, partition_id, part_state):
        with self._lock:
            processing_job = self._sync_processing_job()
            if processing_job is None:
                return
            job_id = self._processing_job.job_id
            job_part = self._sync_job_part(job_id, partition_id)
            if job_part.rank_id == rank_id and \
                    job_part.part_state == part_state:
                if job_part.part_state == dp_pb.PartState.kIdMap:
                    self._finish_job_part(job_id, partition_id,
                                          dp_pb.PartState.kIdMap,
                                          dp_pb.PartState.kIdMapped)
                elif job_part.part_state == dp_pb.PartState.kEventTimeReduce:
                    self._finish_job_part(job_id, partition_id,
                                          dp_pb.PartState.kEventTimeReduce,
                                          dp_pb.PartState.kEventTimeReduced)
            self._check_processing_job_finished()

    def backgroup_task(self):
        with self._lock:
            if self._sync_processing_job() is not None:
                self._check_processing_job_finished()
            if self._sync_processing_job() is None and self._long_running:
                self._launch_new_portal_job()

    def _all_job_part_mapped(self):
        processing_job = self._sync_processing_job()
        assert processing_job is not None
        job_id = processing_job.job_id
        for partition_id in range(self._output_partition_num):
            job_part = self._sync_job_part(job_id, partition_id)
            if job_part.part_state <= dp_pb.PartState.kIdMap:
                return False
        return True

    def _all_job_part_finished(self):
        processing_job = self._sync_processing_job()
        assert processing_job is not None
        job_id = self._processing_job.job_id
        for partition_id in range(self._output_partition_num):
            job_part = self._sync_job_part(job_id, partition_id)
            if not self._is_job_part_finished(job_part):
                return False
        return True

    def _finish_job_part(self, job_id, partition_id, src_state, target_state):
        job_part = self._sync_job_part(job_id, partition_id)
        assert job_part is not None and job_part.part_state == src_state
        new_job_part = dp_pb.PortalJobPart()
        new_job_part.MergeFrom(job_part)
        new_job_part.part_state = target_state
        new_job_part.rank_id = -1
        self._update_job_part(new_job_part)

    def _create_map_task(self, rank_id, partition_id):
        assert self._processing_job is not None
        job = self._processing_job
        map_fpaths = []
        for fpath in job.fpaths:
            fname = path.basename(fpath)
            if hash(fname) % self._output_partition_num == partition_id:
                map_fpaths.append(fpath)
        return dp_pb.MapTask(fpaths=map_fpaths,
                             output_base_dir=self._map_output_dir(job.job_id),
                             output_partition_num=self._output_partition_num,
                             partition_id=partition_id)

    def _create_reduce_task(self, partition_id):
        assert self._processing_job is not None
        job = self._processing_job
        job_id = job.job_id
        return dp_pb.ReduceTask(map_base_dir=self._map_output_dir(job_id),
                                reduce_base_dir=self._reduce_output_dir(job_id),
                                partition_id=partition_id)

    def _try_to_alloc_part(self, rank_id, src_state, target_state):
        alloc_partition_id = None
        processing_job = self._sync_processing_job()
        assert processing_job is not None
        job_id = self._processing_job.job_id
        for partition_id in range(self._output_partition_num):
            part_job = self._sync_job_part(job_id, partition_id)
            if part_job.part_state == src_state and \
                    alloc_partition_id is None:
                alloc_partition_id = partition_id
            if part_job.part_state == target_state and \
                    part_job.rank_id == rank_id:
                alloc_partition_id = partition_id
                break
        if alloc_partition_id is None:
            return None
        part_job = self._job_part_map[alloc_partition_id]
        if part_job.part_state == src_state:
            new_job_part = dp_pb.PortalJobPart(job_id=job_id,
                                               rank_id=rank_id,
                                               partition_id=alloc_partition_id,
                                               part_state=target_state)
            self._update_job_part(new_job_part)
        return alloc_partition_id

    def _sync_portal_job(self, job_id):
        etcd_key = common.portal_job_etcd_key(self._portal_name, job_id)
        data = self._etcd.get_data(etcd_key)
        if data is not None:
            return text_format.Parse(data, dp_pb.DataPortalJob())
        return None

    def _sync_processing_job(self):
        assert self._sync_portal_manifest() is not None
        if self._portal_manifest.processing_job_id < 0:
            self._processing_job = None
        elif self._processing_job is None or \
                (self._processing_job.job_id !=
                    self._portal_manifest.processing_job_id):
            job_id = self._portal_manifest.processing_job_id
            self._processing_job = self._sync_portal_job(job_id)
            assert self._processing_job is not None
        return self._processing_job

    def _update_processing_job(self, job):
        self._processing_job = None
        etcd_key = common.portal_job_etcd_key(self._portal_name, job.job_id)
        self._etcd.set_data(etcd_key, text_format.MessageToString(job))
        self._processing_job = job

    def _sync_portal_manifest(self):
        if self._portal_manifest is None:
            etcd_key = common.portal_etcd_base_dir(self._portal_name)
            data = self._etcd.get_data(etcd_key)
            if data is not None:
                self._portal_manifest = \
                    text_format.Parse(data, dp_pb.DataPortalManifest())
        return self._portal_manifest

    def _update_portal_manifest(self, new_portal_manifest):
        self._portal_manifest = None
        etcd_key = common.portal_etcd_base_dir(self._portal_name)
        data = text_format.MessageToString(new_portal_manifest)
        self._etcd.set_data(etcd_key, data)
        self._portal_manifest = new_portal_manifest

    def _launch_new_portal_job(self):
        assert self._sync_processing_job() is None
        all_fpaths = self._list_input_dir()
        rest_fpaths = []
        for fpath in all_fpaths:
            if fpath not in self._processed_fpath:
                rest_fpaths.append(fpath)
        if len(rest_fpaths) == 0:
            logging.info("no file left for portal")
            return
        rest_fpaths.sort()
        portal_mainifest = self._sync_portal_manifest()
        new_job = dp_pb.DataPortalJob(job_id=portal_mainifest.next_job_id,
                                      finished=False,
                                      fpaths=rest_fpaths)
        self._update_processing_job(new_job)
        new_portal_manifest = dp_pb.DataPortalManifest()
        new_portal_manifest.MergeFrom(portal_mainifest)
        new_portal_manifest.next_job_id += 1
        new_portal_manifest.processing_job_id = new_job.job_id
        self._update_portal_manifest(new_portal_manifest)
        for partition_id in range(self._output_partition_num):
            self._sync_job_part(new_job.job_id, partition_id)

    def _list_input_dir(self):
        input_dir = self._portal_manifest.input_base_dir
        fnames = gfile.ListDirectory(input_dir)
        if len(self._portal_manifest.input_file_wildcard) > 0:
            wildcard = self._portal_manifest.input_file_wildcard
            fnames = [f for f in fnames if fnmatch(f, wildcard)]
        return [path.join(input_dir, f) for f in fnames]

    def _sync_job_part(self, job_id, partition_id):
        if partition_id not in self._job_part_map or \
                self._job_part_map[partition_id] is None or \
                self._job_part_map[partition_id].job_id != job_id:
            etcd_key = common.portal_job_part_etcd_key(self._portal_name,
                                                       job_id, partition_id)
            data = self._etcd.get_data(etcd_key)
            if data is None:
                self._job_part_map[partition_id] = dp_pb.PortalJobPart(
                        job_id=job_id, rank_id=-1,
                        partition_id=partition_id
                    )
            else:
                self._job_part_map[partition_id] = \
                    text_format.Parse(data, dp_pb.PortalJobPart())
        return self._job_part_map[partition_id]

    def _update_job_part(self, job_part):
        partition_id = job_part.partition_id
        if partition_id not in self._job_part_map or \
                self._job_part_map[partition_id] != job_part:
            self._job_part_map[partition_id] = None
            etcd_key = common.portal_job_part_etcd_key(self._portal_name,
                                                       job_part.job_id,
                                                       partition_id)
            data = text_format.MessageToString(job_part)
            self._etcd.set_data(etcd_key, data)
        self._job_part_map[partition_id] = job_part

    def _check_processing_job_finished(self):
        if not self._all_job_part_finished():
            return False
        finished_job = dp_pb.DataPortalJob()
        finished_job.MergeFrom(self._processing_job)
        finished_job.finished = True
        self._update_processing_job(finished_job)
        self._processing_job = None
        self._job_part_map = {}
        new_portal_manifest = dp_pb.DataPortalManifest()
        new_portal_manifest.MergeFrom(self._sync_portal_manifest())
        new_portal_manifest.processing_job_id = -1
        self._update_portal_manifest(new_portal_manifest)
        return True

    @property
    def _output_partition_num(self):
        return self._portal_manifest.output_partition_num

    def _is_job_part_finished(self, job_part):
        assert self._portal_manifest is not None
        if self._portal_manifest.data_portal_type == dp_pb.DataPortalType.PSI:
            return job_part.part_state == dp_pb.PartState.kIdMapped
        return job_part.part_state == dp_pb.PartState.kEventTimeReduced

    def _map_output_dir(self, job_id):
        return common.portal_map_output_dir(
                self._portal_manifest.output_base_dir,
                self._portal_manifest.name, job_id
            )

    def _reduce_output_dir(self, job_id):
        return common.portal_reduce_output_dir(
                self._portal_manifest.output_base_dir,
                self._portal_manifest.name, job_id
            )
