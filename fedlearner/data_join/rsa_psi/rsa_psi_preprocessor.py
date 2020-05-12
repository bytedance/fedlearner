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

import argparse
import logging
import threading

import concurrent.futures as concur_futures
import rsa

from tensorflow.compat.v1 import gfile

from fedlearner.common import common_pb2 as common_pb
from fedlearner.common import data_join_service_pb2 as dj_pb

from fedlearner.data_join.routine_worker import RoutineWorker
from fedlearner.data_join.raw_data_publisher import RawDataPublisher
from fedlearner.data_join.rsa_psi.rsa_psi_component import \
        IdBatchFetcher, LeaderPsiRsaSigner, FollowerPsiRsaSigner
from fedlearner.data_join.rsa_psi.sort_run_dumper import SortRunDumper
from fedlearner.data_join.rsa_psi.sort_run_merger import SortRunMerger

class RsaPsiPreProcessor(object):
    def __init__(self, options, etcd_name, etcd_addrs,
                 etcd_base_dir, use_mock_etcd=False):
        self._lock = threading.Condition()
        self._options = options
        self._publisher = RawDataPublisher(
                etcd_name, etcd_addrs, etcd_base_dir,
                self._options.raw_data_publish_dir, use_mock_etcd
            )
        self._process_pool_executor = \
                concur_futures.ProcessPoolExecutor(
                        options.offload_processor_number
                    )
        self._id_batch_fetcher = IdBatchFetcher(self._options)
        self._id_batch_fetcher.set_input_finished()
        max_flying_item = options.batch_processor_options.max_flying_item
        if self._options.role == common_pb.FLRole.Leader:
            private_key = None
            with gfile.GFile(options.rsa_key_file_path, 'rb') as f:
                file_content = f.read()
                private_key = rsa.PrivateKey.load_pkcs1(file_content)
            self._psi_rsa_signer = LeaderPsiRsaSigner(
                    self._id_batch_fetcher, max_flying_item,
                    self._process_pool_executor, private_key,
                )
            self._repr = 'leader-' + 'rsa_psi_preprocessor'
        else:
            public_key = None
            with gfile.GFile(options.rsa_key_file_path, 'rb') as f:
                file_content = f.read()
                public_key = rsa.PublicKey.load_pkcs1(file_content)
            self._psi_rsa_signer = FollowerPsiRsaSigner(
                    self._id_batch_fetcher, max_flying_item,
                    self._process_pool_executor, public_key,
                    self._options.leader_rsa_psi_signer_addr
                )
            self._repr = 'follower-' + 'rsa_psi_preprocessor'
        self._sort_run_dumper = SortRunDumper(options)
        self._sort_run_merger = SortRunMerger(
                self._sort_run_dumper.sort_run_dump_dir, self._options
            )
        self._worker_map = {}
        self._started = False

    def start_process(self):
        with self._lock:
            if not self._started:
                self._worker_map = {
                    self._id_batch_fetcher_name(): RoutineWorker(
                    self._id_batch_fetcher_name(),
                    self._id_batch_fetch_fn,
                    self._id_batch_fetch_cond, 5),

                    self._psi_rsa_signer_name(): RoutineWorker(
                    self._psi_rsa_signer_name(),
                    self._psi_rsa_sign_fn,
                    self._psi_rsa_sign_cond, 5),

                    self._sort_run_dumper_name(): RoutineWorker(
                    self._sort_run_dumper_name(),
                    self._sort_run_dump_fn,
                    self._sort_run_dump_cond, 5),

                    self._sort_run_merger_name(): RoutineWorker(
                    self._sort_run_merger_name(),
                    self._sort_run_merge_fn,
                    self._sort_run_merge_cond, 5)
                }
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

    def wait_for_finished(self):
        while not self._sort_run_merger.is_merged_finished():
            with self._lock:
                self._lock.wait()
        self.stop_routine_workers()
        self._process_pool_executor.shutdown()

    def _id_batch_fetcher_name(self):
        return self._repr + ':id_batch_fetcher'

    def _wakeup_id_batch_fetcher(self):
        self._worker_map[self._id_batch_fetcher_name()].wakeup()

    def _id_batch_fetch_fn(self):
        next_index = self._psi_rsa_signer.get_next_index_to_fetch()
        for batch in self._id_batch_fetcher.make_processor(next_index):
            logging.debug("%s fetch batch begin at %d, len %d. wakeup %s",
                          self._id_batch_fetcher_name(), batch.begin_index,
                          len(batch), self._psi_rsa_signer_name())
            self._wakeup_psi_rsa_signer()

    def _id_batch_fetch_cond(self):
        next_index = self._psi_rsa_signer.get_next_index_to_fetch()
        return self._id_batch_fetcher.need_process(next_index)

    def _psi_rsa_signer_name(self):
        return self._repr + ':psi_rsa_signer'

    def _wakeup_psi_rsa_signer(self):
        self._worker_map[self._psi_rsa_signer_name()].wakeup()

    def _psi_rsa_sign_fn(self):
        next_index = self._sort_run_dumper.get_next_index_to_dump()
        for signed_batch in self._psi_rsa_signer.make_processor(next_index):
            logging.debug("%s sign batch begin at %d, len %d. wakeup %s",
                          self._psi_rsa_signer_name(),
                          signed_batch.begin_index, len(signed_batch),
                          self._sort_run_dumper_name())
            self._wakeup_sort_run_dumper()
        staless_index = self._sort_run_dumper.get_next_index_to_dump() - 1
        evict_batch_cnt = self._id_batch_fetcher.evict_staless_item_batch(
                staless_index
            )
        self._psi_rsa_signer.update_next_batch_index_hint(evict_batch_cnt)

    def _psi_rsa_sign_cond(self):
        next_index = self._sort_run_dumper.get_next_index_to_dump()
        return self._psi_rsa_signer.need_process(next_index)

    def _sort_run_dumper_name(self):
        return self._repr + ':sort_run_dumper'

    def _wakeup_sort_run_dumper(self):
        self._worker_map[self._sort_run_dumper_name()].wakeup()

    def _load_sorted_items_from_rsa_signer(self):
        sort_run_dumper = self._sort_run_dumper
        rsi_signer = self._psi_rsa_signer
        next_index = sort_run_dumper.get_next_index_to_dump()
        hint_index = None
        items_buffer = []
        signed_finished = False
        total_item_num = 0
        max_flying_item = self._options.batch_processor_options.max_flying_item
        sort_run_size = max_flying_item // 4
        while True and total_item_num < sort_run_size:
            signed_finished, batch, hint_index = \
                rsi_signer.fetch_item_batch_by_index(next_index, hint_index)
            if batch is None:
                break
            assert next_index == batch.begin_index
            for item in batch:
                items_buffer.append(item)
            next_index += len(batch)
            total_item_num += len(batch)
        sorted_items_buffer = sorted(items_buffer, key=lambda item: item[1])
        return signed_finished, sorted_items_buffer, next_index

    def _sort_run_dump_fn(self):
        signed_finished, items_buffer, next_index = \
                self._load_sorted_items_from_rsa_signer()
        sort_run_dumper = self._sort_run_dumper
        if len(items_buffer) > 0:
            def producer(items_buffer):
                for raw_id, signed_id, index in items_buffer:
                    join_id = signed_id
                    raw = {'join_id': join_id, 'raw_id': raw_id}
                    yield join_id, index, raw
            sort_run_dumper.dump_sort_runs(producer(items_buffer))
        if next_index is not None:
            self._psi_rsa_signer.evict_staless_item_batch(next_index-1)
        if signed_finished:
            sort_run_dumper.finish_dump_sort_run()

    def _sort_run_dump_cond(self):
        sort_run_dumper = self._sort_run_dumper
        rsa_signer = self._psi_rsa_signer
        next_index = sort_run_dumper.get_next_index_to_dump()
        max_flying_item = self._options.batch_processor_options.max_flying_item
        dump_finished = sort_run_dumper.is_dump_finished()
        signed_finished = rsa_signer.get_process_finished()
        flying_item_cnt = rsa_signer.get_flying_item_count()
        flying_begin_index = rsa_signer.get_flying_begin_index()
        return not dump_finished and \
                flying_begin_index is not None and \
                (flying_begin_index <= next_index <
                    flying_begin_index + flying_item_cnt) and \
                (flying_item_cnt-(next_index-flying_begin_index) >=
                    max_flying_item // 4 or signed_finished)

    def _sort_run_merger_name(self):
        return self._repr + ':sort_run_merger'

    def _sort_run_merge_fn(self):
        sort_runs = self._sort_run_dumper.get_all_sort_runs()
        self._sort_run_merger.merge_sort_runs(sort_runs)
        fpaths = [self._sort_run_merger.get_merged_sort_run_fpath()]
        self._publisher.publish_raw_data(self._options.partition_id,
                                         fpaths, True)
        self._sort_run_merger.set_merged_finished()

    def _sort_run_merge_cond(self):
        if self._sort_run_merger.is_merged_finished():
            with self._lock:
                self._lock.notify()
            return False
        return self._sort_run_dumper.is_dump_finished()

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    parser = argparse.ArgumentParser(description='Rsa Psi Preprocessor!')
    parser.add_argument('-r', '--psi_role', type=str, required=True,
                        choices=['leader', 'follower'],
                        help='the role of rsa psi(leader/follower)')
    parser.add_argument('--rsa_key_file_path', type=str, required=True,
                        help='the file path for the rsa key')
    parser.add_argument('--input_file_paths', type=str, nargs='+',
                        help='the file path input rsa psi preprocessor')
    parser.add_argument('--output_file_dir', type=str, required=True,
                        help='the directory to store the result of processor')
    parser.add_argument('--raw_data_publish_dir', type=str, required=True,
                        help='the etcd base dir to publish new raw data')
    parser.add_argument('--leader_rsa_psi_signer_addr', type=str,
                        help='the ras psi follower should set give '\
                             'the addr of rsa psi signer of leader')
    parser.add_argument('--process_batch_size', type=int, default=1024,
                        help='the batch size for preprocessor')
    parser.add_argument('--max_flying_item', type=int, default=1<<20,
                        help='the process buffer size')
    parser.add_argument('--offload_processor_number', type=int, default=1,
                        help='the number of processor to offload rsa compute')
    parser.add_argument('--partition_id', type=int, required=True,
                        help='the partition id will be processed')
    parser.add_argument('--etcd_name', type=str,
                        default='test_etcd', help='the name of etcd')
    parser.add_argument('--etcd_addrs', type=str,
                        default='localhost:2379', help='the addrs of etcd')
    parser.add_argument('--etcd_base_dir', type=str, default='fedlearner_test',
                        help='the namespace of etcd key')

    args = parser.parse_args()
    preprocessor_options = dj_pb.RsaPsiPreProcessorOptions(
            role=common_pb.FLRole.Leader if args.psi_role == 'leader' \
                                         else common_pb.FLRole.Follower,
            rsa_key_file_path=args.rsa_key_file_path,
            input_file_paths=args.input_file_paths,
            output_file_dir=args.output_file_dir,
            raw_data_publish_dir=args.raw_data_publish_dir,
            partition_id=args.partition_id,
            leader_rsa_psi_signer_addr=args.leader_rsa_psi_signer_addr,
            offload_processor_number=args.offload_processor_number,
            batch_processor_options=dj_pb.BatchProcessorOptions(
                batch_size=args.process_batch_size,
                max_flying_item=args.max_flying_item
            )
        )
    preprocessor = RsaPsiPreProcessor(preprocessor_options, args.etcd_name,
                                      args.etcd_addrs, args.etcd_base_dir)
    preprocessor.start_process()
    logging.info("PreProcessor launched for %s of RSA PSI", args.psi_role)
    preprocessor.wait_for_finished()
    logging.info("PreProcessor finished for %s of RSA PSI", args.psi_role)
