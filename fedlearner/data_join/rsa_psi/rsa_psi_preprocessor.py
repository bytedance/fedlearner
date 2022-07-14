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
import concurrent.futures as concur_futures
import os
import gc
import time
import traceback
import rsa

from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common import common_pb2 as common_pb
from fedlearner.common.db_client import DBClient

from fedlearner.data_join.routine_worker import RoutineWorker
from fedlearner.data_join.raw_data_publisher import RawDataPublisher
from fedlearner.data_join.rsa_psi.rsa_psi_component import \
        IdBatchFetcher, LeaderPsiRsaSigner, FollowerPsiRsaSigner
from fedlearner.data_join.sort_run_dumper import SortRunDumper
from fedlearner.data_join.sort_run_merger import SortRunMerger
from fedlearner.data_join.common import partition_repr, get_heap_mem_stats

class RsaPsiPreProcessor(object):
    def __init__(self, options, kvstore_type,
                 use_mock_etcd=False):
        self._lock = threading.Condition()
        self._options = options
        kvstore = DBClient(kvstore_type, use_mock_etcd)
        pub_dir = self._options.raw_data_publish_dir
        self._publisher = RawDataPublisher(kvstore, pub_dir)
        self._process_pool_executor = \
                concur_futures.ProcessPoolExecutor(
                        options.offload_processor_number
                    )
        self._callback_submitter = None
        # pre fock sub processor before launch grpc client
        self._process_pool_executor.submit(min, 1, 2).result()
        self._id_batch_fetcher = IdBatchFetcher(kvstore, self._options)
        if self._options.role == common_pb.FLRole.Leader:
            private_key = rsa.PrivateKey.load_pkcs1(options.rsa_key_pem)
            self._psi_rsa_signer = LeaderPsiRsaSigner(
                    self._id_batch_fetcher,
                    options.batch_processor_options.max_flying_item,
                    self._options.max_flying_sign_batch,
                    self._options.slow_sign_threshold,
                    self._process_pool_executor, private_key,
                )
            self._repr = 'leader-' + 'rsa_psi_preprocessor'
        else:
            public_key = rsa.PublicKey.load_pkcs1(options.rsa_key_pem)
            self._callback_submitter = concur_futures.ThreadPoolExecutor(1)
            self._psi_rsa_signer = FollowerPsiRsaSigner(
                    self._id_batch_fetcher,
                    options.batch_processor_options.max_flying_item,
                    self._options.max_flying_sign_batch,
                    self._options.max_flying_sign_rpc,
                    self._options.sign_rpc_timeout_ms,
                    self._options.slow_sign_threshold,
                    self._options.stub_fanout,
                    self._process_pool_executor,
                    self._callback_submitter, public_key,
                    self._options.leader_rsa_psi_signer_addr
                )
            self._repr = 'follower-' + 'rsa_psi_preprocessor'
        self._sort_run_dumper = SortRunDumper(options)
        self._sort_run_merger = SortRunMerger(
                dj_pb.SortRunMergerOptions(
                    merger_name='sort_run_merger_'+\
                                partition_repr(options.partition_id),
                    reader_options=dj_pb.RawDataOptions(
                        raw_data_iter=options.writer_options.output_writer,
                        compressed_type=options.writer_options.compressed_type,
                        read_ahead_size=\
                            options.sort_run_merger_read_ahead_buffer,
                        read_batch_size=\
                            options.sort_run_merger_read_batch_size
                    ),
                    writer_options=options.writer_options,
                    output_file_dir=options.output_file_dir,
                    partition_id=options.partition_id
                ),
                self._merger_comparator
            )
        self._produce_item_cnt = 0
        self._comsume_item_cnt = 0
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
        if self._callback_submitter is not None:
            self._callback_submitter.shutdown()
        self._id_batch_fetcher.cleanup_visitor_meta_data()
        self._bye_for_signer()

    def _bye_for_signer(self):
        for rnd in range(60):
            try:
                self._psi_rsa_signer.say_signer_bye()
                logging.info("Success to say bye to signer at round "\
                             "%d, rsa_psi_preprocessor will exit", rnd)
                return
            except Exception as e: # pylint: disable=broad-except
                logging.warning("Failed to say bye to signer at "\
                                "round %d, sleep 10s and retry", rnd)
            time.sleep(10)
        logging.warning("Give up to say bye to signer after try 60"\
                        "times, rsa_psi_preprocessor will exit as -1")
        traceback.print_stack()
        os._exit(-1) # pylint: disable=protected-access

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
            self._produce_item_cnt += len(batch)
            self._wakeup_psi_rsa_signer()
            if self._stop_fetch_id():
                break

    def _id_batch_fetch_cond(self):
        next_index = self._psi_rsa_signer.get_next_index_to_fetch()
        return self._id_batch_fetcher.need_process(next_index) and \
                not self._stop_fetch_id() and \
                not self._sort_run_dumper.is_dump_finished()

    def _stop_fetch_id(self):
        total_flying_item = self._produce_item_cnt - self._comsume_item_cnt
        if total_flying_item >= 5 << 20:
            logging.warning("stop fetch id since flying item "\
                            "reach to %d > 5m, produce_item_cnt: %d; "\
                            "consume_item_cnt: %d", total_flying_item,
                            self._produce_item_cnt, self._comsume_item_cnt)
            return True
        potential_mem_incr = total_flying_item * \
                             self._psi_rsa_signer.additional_item_mem_usage()
        if get_heap_mem_stats(None).CheckOomRisk(total_flying_item, 0.80,
                                                 potential_mem_incr):
            logging.warning("stop fetch id since has oom risk for 0.80, "\
                            "flying item reach to %d", total_flying_item)
            return True
        return False

    def _psi_rsa_signer_name(self):
        return self._repr + ':psi_rsa_signer'

    def _wakeup_psi_rsa_signer(self):
        self._worker_map[self._psi_rsa_signer_name()].wakeup()

    def _transmit_signed_batch(self, signed_index):
        evict_batch_cnt = self._id_batch_fetcher.evict_staless_item_batch(
                signed_index
            )
        self._psi_rsa_signer.update_next_batch_index_hint(evict_batch_cnt)
        self._wakeup_sort_run_dumper()

    def _psi_rsa_sign_fn(self):
        next_index = self._sort_run_dumper.get_next_index_to_dump()
        sign_cnt = 0
        signed_index = None
        for signed_batch in self._psi_rsa_signer.make_processor(next_index):
            logging.debug("%s sign batch begin at %d, len %d. wakeup %s",
                          self._psi_rsa_signer_name(),
                          signed_batch.begin_index, len(signed_batch),
                          self._sort_run_dumper_name())
            sign_cnt += 1
            if signed_batch is not None:
                signed_index = signed_batch.begin_index + len(signed_batch) - 1
            if sign_cnt % 16 == 0:
                self._transmit_signed_batch(signed_index)
        self._transmit_signed_batch(signed_index)

    def _psi_rsa_sign_cond(self):
        next_index = self._sort_run_dumper.get_next_index_to_dump()
        return self._psi_rsa_signer.need_process(next_index) and \
                not self._sort_run_dumper.is_dump_finished()

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
        sort_run_size = max_flying_item // 2
        while sort_run_size <= 0 or total_item_num < sort_run_size:
            signed_finished, batch, hint_index = \
                rsi_signer.fetch_item_batch_by_index(next_index, hint_index)
            if batch is None:
                break
            assert next_index == batch.begin_index
            for item in batch:
                items_buffer.append(item)
            next_index += len(batch)
            total_item_num += len(batch)
        sorted_items_buffer = sorted(items_buffer, key=lambda item: item[0])
        return signed_finished, sorted_items_buffer, next_index

    def _sort_run_dump_fn(self):
        signed_finished, items_buffer, next_index = \
                self._load_sorted_items_from_rsa_signer()
        sort_run_dumper = self._sort_run_dumper
        if len(items_buffer) > 0:
            def producer(items_buffer):
                for signed_id, item, index in items_buffer:
                    item.add_extra_fields({'example_id':signed_id})
                    yield signed_id, index, item
            sort_run_dumper.dump_sort_runs(producer(items_buffer))
        if next_index is not None:
            self._psi_rsa_signer.evict_staless_item_batch(next_index-1)
        if signed_finished:
            sort_run_dumper.finish_dump_sort_run()
        dump_cnt = len(items_buffer)
        self._comsume_item_cnt += dump_cnt
        del items_buffer
        logging.warning("dump %d item in sort run, and gc %d objects.",
                        dump_cnt, gc.collect())

    def _sort_run_dump_cond(self):
        sort_run_dumper = self._sort_run_dumper
        rsa_signer = self._psi_rsa_signer
        next_index = sort_run_dumper.get_next_index_to_dump()
        max_flying_item = self._options.batch_processor_options.max_flying_item
        dump_finished = sort_run_dumper.is_dump_finished()
        signed_finished = rsa_signer.get_process_finished()
        flying_item_cnt = rsa_signer.get_flying_item_count()
        flying_begin_index = rsa_signer.get_flying_begin_index()
        dump_cands_num = 0
        if flying_begin_index is not None and next_index is not None and \
                (flying_begin_index <= next_index <
                    flying_begin_index + flying_item_cnt):
            dump_cands_num = flying_item_cnt - (next_index - flying_begin_index)
        return not dump_finished and \
                (signed_finished or
                 (dump_cands_num >= (2 << 20) or
                  (max_flying_item > 2 and
                    dump_cands_num > max_flying_item // 2)) or
                  self._dump_for_forward(dump_cands_num))

    def _dump_for_forward(self, dump_cands_num):
        if self._stop_fetch_id():
            total_flying_item = self._produce_item_cnt - self._comsume_item_cnt
            return dump_cands_num > 0 and \
                    dump_cands_num >= total_flying_item // 2
        return False

    def _sort_run_merger_name(self):
        return self._repr + ':sort_run_merger'

    def _sort_run_merge_fn(self):
        sort_runs = self._sort_run_dumper.get_all_sort_runs()
        input_dir = self._sort_run_dumper.sort_run_dump_dir()
        input_fpaths = [os.path.join(input_dir,
                                     partition_repr(self._options.partition_id),
                                     sort_run.encode_sort_run_fname())
                        for sort_run in sort_runs]
        output_fpaths = self._sort_run_merger.merge_sort_runs(input_fpaths)
        self._publisher.publish_raw_data(self._options.partition_id,
                                         output_fpaths)
        self._publisher.finish_raw_data(self._options.partition_id)
        self._sort_run_merger.set_merged_finished()

    def _sort_run_merge_cond(self):
        if self._sort_run_merger.is_merged_finished():
            with self._lock:
                self._lock.notify()
            return False
        return self._sort_run_dumper.is_dump_finished()

    @staticmethod
    def _merger_comparator(a, b):
        return a.example_id < b.example_id
