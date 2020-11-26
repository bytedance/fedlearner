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
import tensorflow_io # pylint: disable=unused-import
from tensorflow.compat.v1 import gfile

from fedlearner.common import data_portal_service_pb2 as dp_pb

from fedlearner.data_join import common
from fedlearner.data_join.raw_data_publisher import RawDataPublisher
from fedlearner.data_join.sort_run_merger import MergedSortRunMeta

class DataPortalJobManager(object):
    def __init__(self, kvstore, portal_name, long_running, check_success_tag):
        self._lock = threading.Lock()
        self._kvstore = kvstore
        self._portal_name = portal_name
        self._check_success_tag = check_success_tag
        self._portal_manifest = None
        self._processing_job = None
        self._sync_portal_manifest()
        self._sync_processing_job()
        self._publisher = \
            RawDataPublisher(kvstore,
                self._portal_manifest.raw_data_publish_dir)
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
                        return False, self._create_reduce_task(rank_id,
                                                               partition_id)
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
                    logging.info("Data portal worker-%d finish map task "\
                                 "for partition %d of job %d",
                                 rank_id, partition_id, job_id)
                elif job_part.part_state == dp_pb.PartState.kEventTimeReduce:
                    self._finish_job_part(job_id, partition_id,
                                          dp_pb.PartState.kEventTimeReduce,
                                          dp_pb.PartState.kEventTimeReduced)
                    logging.info("Data portal worker-%d finish reduce task "\
                                 "for partition %d of job %d",
                                 rank_id, partition_id, job_id)
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
            if hash(fpath) % self._output_partition_num == partition_id:
                map_fpaths.append(fpath)
        task_name = '{}-dp_portal_job_{:08}-part-{:04}-map'.format(
                self._portal_manifest.name, job.job_id, partition_id
            )
        logging.info("Data portal worker-%d is allocated map task %s for "\
                     "partition %d of job %d. the map task has %d files"\
                     "-----------------\n", rank_id, task_name,
                     partition_id, job.job_id, len(map_fpaths))
        for seq, fpath in enumerate(map_fpaths):
            logging.info("%d. %s", seq, fpath)
        logging.info("---------------------------------\n")
        manifset = self._sync_portal_manifest()
        return dp_pb.MapTask(task_name=task_name,
                             fpaths=map_fpaths,
                             output_base_dir=self._map_output_dir(job.job_id),
                             output_partition_num=self._output_partition_num,
                             partition_id=partition_id,
                             part_field=self._get_part_field(),
                             data_portal_type=manifset.data_portal_type)

    def _get_part_field(self):
        portal_mainifest = self._sync_portal_manifest()
        if portal_mainifest.data_portal_type == dp_pb.DataPortalType.PSI:
            return 'raw_id'
        assert portal_mainifest.data_portal_type == \
                dp_pb.DataPortalType.Streaming
        return 'example_id'

    def _create_reduce_task(self, rank_id, partition_id):
        assert self._processing_job is not None
        job = self._processing_job
        job_id = job.job_id
        task_name = '{}-dp_portal_job_{:08}-part-{:04}-reduce'.format(
                self._portal_manifest.name, job_id, partition_id
            )
        logging.info("Data portal worker-%d is allocated reduce task %s for "\
                     "partition %d of job %d. the reduce base dir %s"\
                     "-----------------\n", rank_id, task_name,
                     partition_id, job_id, self._reduce_output_dir(job_id))
        return dp_pb.ReduceTask(task_name=task_name,
                                map_base_dir=self._map_output_dir(job_id),
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
        kvstore_key = common.portal_job_kvstore_key(self._portal_name, job_id)
        data = self._kvstore.get_data(kvstore_key)
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
        kvstore_key = common.portal_job_kvstore_key(self._portal_name,
                                                    job.job_id)
        self._kvstore.set_data(kvstore_key, text_format.MessageToString(job))
        self._processing_job = job

    def _sync_portal_manifest(self):
        if self._portal_manifest is None:
            kvstore_key = common.portal_kvstore_base_dir(self._portal_name)
            data = self._kvstore.get_data(kvstore_key)
            if data is not None:
                self._portal_manifest = \
                    text_format.Parse(data, dp_pb.DataPortalManifest())
        return self._portal_manifest

    def _update_portal_manifest(self, new_portal_manifest):
        self._portal_manifest = None
        kvstore_key = common.portal_kvstore_base_dir(self._portal_name)
        data = text_format.MessageToString(new_portal_manifest)
        self._kvstore.set_data(kvstore_key, data)
        self._portal_manifest = new_portal_manifest

    def _launch_new_portal_job(self):
        assert self._sync_processing_job() is None
        rest_fpaths = self._list_input_dir()
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
        logging.info("Data Portal job %d has lanuched. %d files will be"\
                     "processed\n------------\n",
                     new_job.job_id, len(new_job.fpaths))
        for seq, fpath in enumerate(new_job.fpaths):
            logging.info("%d. %s", seq, fpath)
        logging.info("---------------------------------\n")

    def _list_input_dir(self):
        all_inputs = []
        wildcard = self._portal_manifest.input_file_wildcard
        dirs = [self._portal_manifest.input_base_dir]

        num_dirs = 0
        num_files = 0
        num_target_files = 0
        while len(dirs) > 0:
            fdir = dirs[0]
            dirs = dirs[1:]
            fnames = gfile.ListDirectory(fdir)
            for fname in fnames:
                fpath = path.join(fdir, fname)
                # OSS does not retain folder structure.
                # For example, if we have file oss://test/1001/a.txt
                # list(oss://test) returns 1001/a.txt instead of 1001
                basename = path.basename(fpath)
                if basename == '_SUCCESS':
                    continue
                if gfile.IsDirectory(fpath):
                    dirs.append(fpath)
                    num_dirs += 1
                    continue
                num_files += 1
                if len(wildcard) == 0 or fnmatch(basename, wildcard):
                    num_target_files += 1
                    if self._check_success_tag:
                        has_succ = gfile.Exists(
                            path.join(path.dirname(fpath), '_SUCCESS'))
                        if not has_succ:
                            logging.warning(
                                'File %s skipped because _SUCCESS file is '
                                'missing under %s',
                                fpath, fdir)
                            continue
                    all_inputs.append(fpath)

        rest_fpaths = []
        for fpath in all_inputs:
            if fpath not in self._processed_fpath:
                rest_fpaths.append(fpath)
        logging.info(
            'Listing %s: found %d dirs, %d files, %d files matching wildcard, '
            '%d files with success tag, %d new files to process',
            self._portal_manifest.input_base_dir, num_dirs, num_files,
            num_target_files, len(all_inputs), len(rest_fpaths))
        return rest_fpaths

    def _sync_job_part(self, job_id, partition_id):
        if partition_id not in self._job_part_map or \
                self._job_part_map[partition_id] is None or \
                self._job_part_map[partition_id].job_id != job_id:
            kvstore_key = common.portal_job_part_kvstore_key(self._portal_name,
                                                       job_id, partition_id)
            data = self._kvstore.get_data(kvstore_key)
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
            kvstore_key = common.portal_job_part_kvstore_key(self._portal_name,
                                                       job_part.job_id,
                                                       partition_id)
            data = text_format.MessageToString(job_part)
            self._kvstore.set_data(kvstore_key, data)
        self._job_part_map[partition_id] = job_part

    def _check_processing_job_finished(self):
        if not self._all_job_part_finished():
            return False
        processing_job = self._sync_processing_job()
        if not processing_job.finished:
            finished_job = dp_pb.DataPortalJob()
            finished_job.MergeFrom(self._processing_job)
            finished_job.finished = True
            self._update_processing_job(finished_job)
        for fpath in processing_job.fpaths:
            self._processed_fpath.add(fpath)
        self._processing_job = None
        self._job_part_map = {}
        portal_mainifest = self._sync_portal_manifest()
        if portal_mainifest.processing_job_id >= 0:
            self._publish_raw_data(portal_mainifest.processing_job_id)
            new_portal_manifest = dp_pb.DataPortalManifest()
            new_portal_manifest.MergeFrom(self._sync_portal_manifest())
            new_portal_manifest.processing_job_id = -1
            self._update_portal_manifest(new_portal_manifest)
        if processing_job is not None:
            logging.info("Data Portal job %d has finished. Processed %d "\
                         "following fpaths\n------------\n",
                         processing_job.job_id, len(processing_job.fpaths))
            for seq, fpath in enumerate(processing_job.fpaths):
                logging.info("%d. %s", seq, fpath)
            logging.info("---------------------------------\n")
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
                self._portal_manifest.output_base_dir, job_id
            )

    def _reduce_output_dir(self, job_id):
        return common.portal_reduce_output_dir(
                self._portal_manifest.output_base_dir, job_id
            )

    def _publish_raw_data(self, job_id):
        portal_manifest = self._sync_portal_manifest()
        output_dir = None
        if portal_manifest.data_portal_type == dp_pb.DataPortalType.PSI:
            output_dir = common.portal_map_output_dir(
                    portal_manifest.output_base_dir, job_id
                )
        else:
            output_dir = common.portal_reduce_output_dir(
                    portal_manifest.output_base_dir, job_id
                )
        for partition_id in range(self._output_partition_num):
            dpath = path.join(output_dir, common.partition_repr(partition_id))
            fnames = []
            if gfile.Exists(dpath) and gfile.IsDirectory(dpath):
                fnames = [f for f in gfile.ListDirectory(dpath)
                          if f.endswith(common.RawDataFileSuffix)]
            publish_fpaths = []
            if portal_manifest.data_portal_type == dp_pb.DataPortalType.PSI:
                publish_fpaths = self._publish_psi_raw_data(partition_id,
                                                            dpath, fnames)
            else:
                publish_fpaths = self._publish_streaming_raw_data(partition_id,
                                                                 dpath, fnames)
            logging.info("Data Portal Master publish %d file for partition "\
                         "%d of streaming job %d\n----------\n",
                         len(publish_fpaths), partition_id, job_id)
            for seq, fpath in enumerate(publish_fpaths):
                logging.info("%d. %s", seq, fpath)
            logging.info("------------------------------------------\n")

    def _publish_streaming_raw_data(self, partition_id, dpath, fnames):
        metas = [MergedSortRunMeta.decode_sort_run_meta_from_fname(fname)
                 for fname in fnames]
        metas.sort()
        fpaths = [path.join(dpath, meta.encode_merged_sort_run_fname())
                  for meta in metas]
        self._publisher.publish_raw_data(partition_id, fpaths)
        return fpaths

    def _publish_psi_raw_data(self, partition_id, dpath, fnames):
        fpaths = [path.join(dpath, fname) for fname in fnames]
        self._publisher.publish_raw_data(partition_id, fpaths)
        self._publisher.finish_raw_data(partition_id)
        return fpaths
