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
import hashlib
import random
import functools
import os
import time
import bisect
import traceback
import concurrent.futures as concur_futures

from cityhash import CityHash64 # pylint: disable=no-name-in-module
from gmpy2 import powmod, divm # pylint: disable=no-name-in-module

from google.protobuf import empty_pb2

from fedlearner.common import data_join_service_pb2_grpc as dj_grpc
from fedlearner.common import data_join_service_pb2 as dj_pb

from fedlearner.proxy.channel import make_insecure_channel, ChannelType

from fedlearner.data_join.raw_data_visitor import \
        FileBasedMockRawDataVisitor, DBBasedMockRawDataVisitor
from fedlearner.data_join.item_batch_seq_processor import \
        ItemBatch, ItemBatchSeqProcessor
from fedlearner.data_join.common import int2bytes, bytes2int

class IdBatch(ItemBatch):
    def __init__(self, begin_index):
        self._begin_index = begin_index
        self._raw_ids = []
        self._items = []

    def append(self, item):
        self._raw_ids.append(item.raw_id)
        self._items.append(item)

    @property
    def raw_ids(self):
        return self._raw_ids

    @property
    def items(self):
        return self._items

    @property
    def begin_index(self):
        return self._begin_index

    def __len__(self):
        return len(self._items)

    def __lt__(self, other):
        assert isinstance(other, IdBatch)
        return self.begin_index < other.begin_index

    def __iter__(self):
        return iter(zip(self._raw_ids, self._items))

class IdBatchFetcher(ItemBatchSeqProcessor):
    def __init__(self, kvstore, options):
        super(IdBatchFetcher, self).__init__(
                options.batch_processor_options.max_flying_item,
            )
        self._kvstore = kvstore
        self._options = options
        self._id_visitor = None
        self._batch_size = options.batch_processor_options.batch_size

    @classmethod
    def name(cls):
        return 'IdBatchFetcher'

    def cleanup_visitor_meta_data(self):
        with self._lock:
            if self._id_visitor is not None:
                self._id_visitor.cleanup_meta_data()

    def _make_item_batch(self, begin_index):
        return IdBatch(begin_index)

    def _make_inner_generator(self, next_index):
        id_visitor = self._get_id_visitor()
        assert next_index is not None
        if next_index == 0:
            id_visitor.reset()
        else:
            id_visitor.seek(next_index - 1)
        while not id_visitor.finished() and not self._fly_item_full():
            next_batch = self._make_item_batch(next_index)
            for (index, item) in id_visitor:
                if index != next_index:
                    logging.fatal("index of id visitor is not consecutive, "\
                                  "%d != %d", index, next_index)
                    traceback.print_stack()
                    os._exit(-1) # pylint: disable=protected-access
                next_batch.append(item)
                next_index += 1
                if len(next_batch) >= self._batch_size:
                    break
            yield next_batch, id_visitor.finished()
        yield self._make_item_batch(next_index), id_visitor.finished()

    def _get_id_visitor(self):
        if len(self._options.input_file_subscribe_dir) == 0:
            if self._id_visitor is None:
                self._id_visitor = self._create_file_based_mock_visitor()
                self.set_input_finished()
        else:
            if self._id_visitor is None:
                self._id_visitor = self._create_kvstore_based_mock_visitor()
            self._id_visitor.active_visitor()
            if self._id_visitor.is_input_data_finish():
                self.set_input_finished()
        return self._id_visitor

    def _create_file_based_mock_visitor(self):
        return FileBasedMockRawDataVisitor(
                self._kvstore,
                self._options.input_raw_data,
                '{}-rsa_psi_proprocessor-mock-data-source-{:04}'.format(
                    self._options.preprocessor_name,
                    self._options.partition_id
                ),
                self._options.input_file_paths
            )

    def _create_kvstore_based_mock_visitor(self):
        return DBBasedMockRawDataVisitor(
                self._kvstore,
                self._options.input_raw_data,
                '{}-rsa_psi_proprocessor-mock-data-source-{:04}'.format(
                    self._options.preprocessor_name,
                    self._options.partition_id
                ),
                self._options.input_file_subscribe_dir,
                self._options.partition_id
            )

class SignedIdBatch(ItemBatch):
    def __init__(self, begin_index):
        self._begin_index = begin_index
        self._items = []
        self._signed_ids = []

    @property
    def begin_index(self):
        return self._begin_index

    def append(self, id_pair):
        self._signed_ids.append(id_pair[0])
        self._items.append(id_pair[1])

    def __len__(self):
        assert len(self._items) == len(self._signed_ids)
        return len(self._items)

    def __lt__(self, other):
        assert isinstance(other, SignedIdBatch)
        return self.begin_index < other.begin_index

    def __iter__(self):
        assert len(self._items) == len(self._signed_ids)
        item_cnt = len(self._items)
        return iter(zip(self._signed_ids, self._items,
                        list(range(self._begin_index,
                                   self._begin_index+item_cnt))))

class PsiRsaSigner(ItemBatchSeqProcessor):
    def __init__(self, id_batch_fetcher, max_flying_item,
                 max_flying_sign_batch, slow_sign_threshold,
                 process_pool_executor):
        super(PsiRsaSigner, self).__init__(max_flying_item)
        self._id_batch_fetcher = id_batch_fetcher
        self._next_index_to_fetch = None
        self._next_batch_index_hint = None
        self._max_flying_sign_batch = max_flying_sign_batch
        self._process_pool_executor = process_pool_executor
        self._slow_sign_threshold = slow_sign_threshold
        self._total_sign_duration = .0
        self._total_pending_duration = .0
        self._sign_batch_num = 0
        self._slow_sign_batch_num = 0
        self._total_slow_sign_duration = .0
        self._total_slow_pending_duration = .0
        self._total_retry_cnt = 0
        self._total_slow_sign_retry_cnt = 0
        self._yield_batch_num = 0

    @classmethod
    def name(cls):
        return 'PsiRsaSigner'

    def say_signer_bye(self):
        raise NotImplementedError("say_signer_bye not implemented "\
                                  "in base PsiRsaSigner")

    def _make_item_batch(self, begin_index):
        return SignedIdBatch(begin_index)

    def get_next_index_to_fetch(self):
        with self._lock:
            return self._next_index_to_fetch

    def update_next_batch_index_hint(self, evit_batch_cnt):
        with self._lock:
            if self._next_batch_index_hint is not None and \
                    self._next_batch_index_hint >= evit_batch_cnt:
                self._next_batch_index_hint -= evit_batch_cnt

    def additional_item_mem_usage(self):
        raise NotImplementedError("additional_item_mem_usage not "\
                                  "implemented in base PsiRsaSigner")

    def _add_sign_stats(self, duration, pending_duration, retry_cnt):
        with self._lock:
            self._total_retry_cnt += retry_cnt
            self._sign_batch_num += 1
            self._total_sign_duration += duration
            self._total_pending_duration += pending_duration
            if duration >= self._slow_sign_threshold:
                self._total_slow_sign_duration += duration
                self._slow_sign_batch_num += 1
                self._total_slow_sign_retry_cnt += retry_cnt
                self._total_slow_pending_duration += pending_duration

    def _get_sign_stats(self):
        with self._lock:
            avg_duration = self._total_sign_duration \
                    / self._sign_batch_num
            avg_retry_cnt = self._total_retry_cnt \
                    / self._sign_batch_num
            avg_pending_duration = self._total_pending_duration \
                    / self._sign_batch_num
            slow_avg_duration = 0.0
            slow_avg_retry_cnt = 0.0
            slow_avg_pending_duration = 0.0
            if self._slow_sign_batch_num > 0:
                slow_avg_duration = self._total_slow_sign_duration \
                        / self._slow_sign_batch_num
                slow_avg_retry_cnt = self._total_slow_sign_retry_cnt \
                        / self._slow_sign_batch_num
                slow_avg_pending_duration = self._total_slow_pending_duration \
                        / self._slow_sign_batch_num
            return self._slow_sign_batch_num, self._sign_batch_num, \
                    avg_duration, avg_retry_cnt, avg_pending_duration, \
                    slow_avg_duration, slow_avg_retry_cnt, avg_pending_duration

    def _make_inner_generator(self, next_index):
        assert next_index is not None
        max_flying_sign_batch = self._max_flying_sign_batch
        raw_id_batches, next_index = self._consum_raw_id_batch(
                next_index, max_flying_sign_batch
            )
        flying_batch_num = len(raw_id_batches)
        signed_batch_futures = self._promise_signed_batches(raw_id_batches)
        wait4batch = False
        while len(signed_batch_futures) > 0:
            if signed_batch_futures[0].done() or wait4batch or \
                    len(signed_batch_futures) >= max_flying_sign_batch:
                signed_batch = signed_batch_futures[0].result()
                self._yield_batch_num += 1
                if self._yield_batch_num % 32 == 0:
                    slow_sign_batch_num, sign_batch_num, avg_duration, \
                        avg_retry_cnt, avg_pending_duration, \
                        slow_avg_duration, slow_avg_retry_cnt, \
                        slow_avg_pending_duration = self._get_sign_stats()
                    logging.warning("%d/%d batch sign cost more than %d "\
                                    "second, avg duration: %f for each batch,"\
                                    "avg retry cnt: %f. avg pending duration "\
                                    "%f, slow avg duration %f, slow avg retry"\
                                    " cnt %f, slow avg pending duration %f",
                                    slow_sign_batch_num, sign_batch_num,
                                    self._slow_sign_threshold,
                                    avg_duration, avg_retry_cnt,
                                    avg_pending_duration, slow_avg_duration,
                                    slow_avg_retry_cnt,
                                    slow_avg_pending_duration)
                yield signed_batch, False
                signed_batch_futures = signed_batch_futures[1:]
            required_num = max_flying_sign_batch - len(signed_batch_futures)
            raw_id_batches, next_index = \
                    self._consum_raw_id_batch(next_index, required_num)
            wait4batch = len(raw_id_batches) == 0
            signed_batch_futures += self._promise_signed_batches(raw_id_batches)
        yield self._make_item_batch(next_index), True

    def _consum_raw_id_batch(self, next_index, required_num):
        raw_id_batches = []
        while len(raw_id_batches) < required_num:
            batch_index_hint = self._get_next_batch_index_hint()
            fetch_finished, raw_id_batch, new_index_hint = \
                    self._id_batch_fetcher.fetch_item_batch_by_index(
                            next_index, batch_index_hint
                        )
            self._set_next_batch_index_hint(new_index_hint)
            if fetch_finished:
                self.set_input_finished()
            if raw_id_batch is None:
                break
            assert next_index == raw_id_batch.begin_index
            next_index += len(raw_id_batch)
            if len(raw_id_batch) > 0:
                raw_id_batches.append(raw_id_batch)
        with self._lock:
            self._next_index_to_fetch = next_index
        return raw_id_batches, next_index

    def _promise_signed_batches(self, raw_id_batches):
        futures = []
        for raw_id_batch in raw_id_batches:
            futures.append(self._make_sign_future(raw_id_batch))
        return futures

    def _make_sign_future(self, raw_id_batch):
        raise NotImplementedError("_make_sign_future is not Implemented "\
                                  "in base PsiRsaSigner")

    def _get_next_batch_index_hint(self):
        with self._lock:
            return self._next_batch_index_hint

    def _set_next_batch_index_hint(self, batch_index_hint):
        with self._lock:
            self._next_batch_index_hint = batch_index_hint

    @staticmethod
    def _crypto_hash(value):
        return hashlib.sha256(bytes(str(value), encoding='utf-8')).hexdigest()

    @staticmethod
    def _crypto_hash_list(items, ret_int=False):
        if ret_int:
            return [int(PsiRsaSigner._crypto_hash(item), 16)
                    for item in items]
        return [PsiRsaSigner._crypto_hash(item) for item in items]

    @staticmethod
    def _oneway_hash_list(items):
        return [hex(CityHash64(str(item)))[2:] for item in items]

    @staticmethod
    def _rsa_sign_list(items, d, n):
        return [int(powmod(x, d, n).digits()) for x in items]

class LeaderPsiRsaSigner(PsiRsaSigner):
    def __init__(self, id_batch_fetcher, max_flying_item,
                 max_flying_sign_batch, slow_sign_threshold,
                 process_pool_executor, private_key):
        super(LeaderPsiRsaSigner, self).__init__(id_batch_fetcher,
                                                 max_flying_item,
                                                 max_flying_sign_batch,
                                                 slow_sign_threshold,
                                                 process_pool_executor)
        self._private_key = private_key
        self._item_additional_cost = 256 // 8 + \
                                     self._private_key.n.bit_length() // 8

    def additional_item_mem_usage(self):
        return self._item_additional_cost


    def say_signer_bye(self):
        logging.warning("leader signer has no peer signer")

    @staticmethod
    def _leader_sign_func(raw_id_batch, d, n):
        hashed_ids = PsiRsaSigner._crypto_hash_list(
                raw_id_batch.raw_ids, True
            )
        assert len(hashed_ids) == len(raw_id_batch)
        signed_hashed_ids = PsiRsaSigner._rsa_sign_list(hashed_ids, d, n)
        assert len(signed_hashed_ids) == len(raw_id_batch)
        hashed_signed_hashed_ids = \
                PsiRsaSigner._oneway_hash_list(signed_hashed_ids)
        return hashed_signed_hashed_ids

    def _sign_callback(self, raw_id_batch, start_tm,
                       notify_future, exec_future):
        try:
            hashed_signed_hashed_ids = exec_future.result()
            self._add_sign_stats(time.time()-start_tm, 0, 0)
            assert len(hashed_signed_hashed_ids) == len(raw_id_batch)
            begin_index = raw_id_batch.begin_index
            signed_id_batch = self._make_item_batch(begin_index)
            for idx, item in enumerate(raw_id_batch.items):
                join_id = hashed_signed_hashed_ids[idx]
                signed_id_batch.append((join_id, item))
            notify_future.set_result(signed_id_batch)
        except Exception as e: # pylint: disable=broad-except
            notify_future.set_exception(e)

    def _make_sign_future(self, raw_id_batch):
        notify_future = concur_futures.Future()
        start_tm = time.time()
        exec_future = self._process_pool_executor.submit(
                LeaderPsiRsaSigner._leader_sign_func, raw_id_batch,
                self._private_key.d, self._private_key.n
            )
        exec_cb = functools.partial(self._sign_callback, raw_id_batch,
                                    start_tm, notify_future)
        exec_future.add_done_callback(exec_cb)
        return notify_future

class FollowerPsiRsaSigner(PsiRsaSigner):
    class SignerStub(object):
        def __init__(self, addr):
            self._lock = threading.Lock()
            self._channel = make_insecure_channel(
                    addr, ChannelType.REMOTE,
                    options=[('grpc.max_send_message_length', 2**31-1),
                             ('grpc.max_receive_message_length', 2**31-1)]
                )
            self._stub = dj_grpc.RsaPsiSignServiceStub(self._channel)
            self._serial_fail_cnt = 0
            self._rpc_ref_cnt = 0
            self._mark_error = False

        def mark_rpc_failed(self):
            with self._lock:
                self._serial_fail_cnt += 1
                self._mark_error = self._serial_fail_cnt > 16

        def mark_rpc_success(self):
            with self._lock:
                if not self._mark_error:
                    self._serial_fail_cnt = 0

        def marked_error(self):
            with self._lock:
                return self._mark_error

        def rpc_ref(self):
            with self._lock:
                self._rpc_ref_cnt += 1

        def rpc_unref(self):
            with self._lock:
                self._rpc_ref_cnt -= 1
                return self._rpc_ref_cnt == 0

        def close(self):
            self._channel.close()

        def __getattr__(self, attr):
            return getattr(self._stub, attr)

    class RpcSignCtx(object):
        def __init__(self, raw_id_batch, blind_numbers,
                     blinded_hashed_ids, notify_future):
            self.raw_id_batch = raw_id_batch
            self.blind_numbers = blind_numbers
            self.notify_future = notify_future
            self.rpc_req = dj_pb.SignIdsRequest(
                    ids=blinded_hashed_ids,
                    begin_index=raw_id_batch.begin_index
                )
            self.retry_cnt = 0
            self.start_tm = time.time()
            self.pending_tm = None
            self.pending_duration = .0
            self.finish_tm = 0

        def __lt__(self, other):
            return self.raw_id_batch.begin_index < \
                    other.raw_id_batch.begin_index

        def trigger_rpc_pending(self):
            if self.pending_tm is None:
                self.pending_tm = time.time()

        def trigger_rpc_sign(self):
            if self.pending_tm is not None:
                self.pending_duration += time.time() - self.pending_tm
            self.pending_tm = None

        def trigger_rpc_finished(self):
            self.finish_tm = time.time()

        def trigger_retry(self):
            self.retry_cnt += 1

        def rpc_sign_duration(self):
            return self.finish_tm - self.start_tm

        def rpc_pending_duration(self):
            return self.pending_duration

    def __init__(self, id_batch_fetcher, max_flying_item,
                 max_flying_sign_batch, max_flying_sign_rpc,
                 sign_rpc_timeout_ms, slow_sign_threshold,
                 stub_fanout, process_pool_executor,
                 callback_submitter, public_key, leader_signer_addr):
        super(FollowerPsiRsaSigner, self).__init__(id_batch_fetcher,
                                                   max_flying_item,
                                                   max_flying_sign_batch,
                                                   slow_sign_threshold,
                                                   process_pool_executor)
        self._public_key = public_key
        self._leader_signer_addr = leader_signer_addr
        self._perfer_stub_cursor = 0
        self._max_flying_sign_rpc = max_flying_sign_rpc
        self._flying_sign_rpc_threshold = max_flying_sign_rpc
        self._sign_rpc_timeout_ms = sign_rpc_timeout_ms
        self._active_stubs = \
                [FollowerPsiRsaSigner.SignerStub(leader_signer_addr)
                 for _ in range(stub_fanout)]
        self._pending_rpc_sign_ctx = []
        self._flying_rpc_num = 0
        self._callback_submitter = callback_submitter
        self._item_additional_cost = 256 * 2 // 8 + \
                                     self._public_key.n.bit_length() // 8

    def additional_item_mem_usage(self):
        return self._item_additional_cost

    def say_signer_bye(self):
        stub = self._get_active_stub()
        try:
            stub.Bye(empty_pb2.Empty())
        except Exception as e: # pylint: disable=broad-except
            self._revert_stub(stub, True)
            logging.error("Failed to say Bye to rsa signer: %s, "\
                          "reason: %s", self._leader_signer_addr, e)
            raise
        self._revert_stub(stub, False)

    def _get_active_stub(self):
        with self._lock:
            stub_num = len(self._active_stubs)
            assert stub_num > 0
            stub = self._active_stubs[self._perfer_stub_cursor % stub_num]
            self._perfer_stub_cursor += 1
            stub.rpc_ref()
            return stub

    def _revert_stub(self, stub, rpc_failed):
        with self._lock:
            if rpc_failed:
                stub.mark_rpc_failed()
                new_threshold = self._flying_sign_rpc_threshold // 2
                if new_threshold < 12:
                    new_threshold = 12
                if new_threshold != self._flying_sign_rpc_threshold:
                    logging.warning("reduce the flying sign rpc threshold "\
                                    "as %d since rpc error", new_threshold)
                self._flying_sign_rpc_threshold = new_threshold
            else:
                stub.mark_rpc_success()
                new_threshold = int(self._flying_sign_rpc_threshold * 1.1 + 1)
                if new_threshold > self._max_flying_sign_rpc:
                    new_threshold = self._max_flying_sign_rpc
                if new_threshold != self._flying_sign_rpc_threshold:
                    logging.warning("increase the flying sign rpc threshold "\
                                    "as %d since rpc success", new_threshold)
                self._flying_sign_rpc_threshold = new_threshold
            if stub.marked_error():
                for idx, stub2 in enumerate(self._active_stubs):
                    if stub is stub2:
                        self._active_stubs[idx] = \
                                FollowerPsiRsaSigner.SignerStub(
                                        self._leader_signer_addr
                                    )
                        break
                if stub.rpc_unref():
                    stub.close()

    @staticmethod
    def _generate_blind_number(item_num, blind_len=256):
        return [random.SystemRandom().getrandbits(blind_len)
                for i in range(item_num)]

    def _make_sign_future(self, raw_id_batch):
        notify_future = concur_futures.Future()
        self._blind_raw_id_func(raw_id_batch, notify_future)
        return notify_future

    def _blind_raw_id_func(self, raw_id_batch, notify_future):
        e, n = self._public_key.e, self._public_key.n
        blind_future = self._process_pool_executor.submit(
                FollowerPsiRsaSigner._blind_raw_id_batch,
                raw_id_batch, e, n
            )
        blind_cb = functools.partial(self._blind_callback,
                                     raw_id_batch, notify_future)
        blind_future.add_done_callback(blind_cb)

    @staticmethod
    def _blind_raw_id_batch(raw_id_batch, e, n):
        hashed_ids = PsiRsaSigner._crypto_hash_list(
                raw_id_batch.raw_ids, True
            )
        blind_numbers = [random.SystemRandom().getrandbits(256)
                         for i in range(len(raw_id_batch))]
        byte_len = n.bit_length() // 8
        blinded_hashed_ids = [int2bytes((powmod(r, e, n) * x % n).digits(),
                                        byte_len)
                              for x, r in zip(hashed_ids, blind_numbers)]
        return (blinded_hashed_ids, blind_numbers)

    def _blind_callback(self, raw_id_batch, notify_future, blind_future):
        try:
            blinded_hashed_ids, blind_numbers = blind_future.result()
            assert len(blinded_hashed_ids) == len(raw_id_batch)
            assert len(blind_numbers) == len(raw_id_batch)
            ctx = FollowerPsiRsaSigner.RpcSignCtx(raw_id_batch,
                                                  blind_numbers,
                                                  blinded_hashed_ids,
                                                  notify_future)
            self._rpc_sign_func(ctx)
        except Exception as e: # pylint: disable=broad-except
            notify_future.set_exception(e)

    def _rpc_sign_func(self, ctx):
        with self._lock:
            if self._flying_rpc_num >= self._flying_sign_rpc_threshold:
                if len(self._pending_rpc_sign_ctx) == 0:
                    self._pending_rpc_sign_ctx.append(ctx)
                else:
                    idx = bisect.bisect_left(self._pending_rpc_sign_ctx, ctx)
                    self._pending_rpc_sign_ctx.insert(idx, ctx)
                ctx.trigger_rpc_pending()
                return
            self._flying_rpc_num += 1
        stub = self._get_active_stub()
        timeout = None if self._sign_rpc_timeout_ms <= 0 \
                else self._sign_rpc_timeout_ms / 1000.0
        ctx.trigger_rpc_sign()
        sign_future = stub.SignIds.future(ctx.rpc_req, timeout)
        sign_cb = functools.partial(self._rpc_sign_callback, ctx, stub)
        sign_future.add_done_callback(sign_cb)

    def _rpc_sign_callback(self, ctx, stub, rpc_future):
        try:
            response = rpc_future.result()
            if response.status.code != 0:
                raise RuntimeError("Failed to call rpc for psi sign, "\
                                   "error code: {}, error message: {}".format(
                                        response.status.code,
                                        response.status.error_message))
            ctx.trigger_rpc_finished()
            self._add_sign_stats(ctx.rpc_sign_duration(),
                                 ctx.rpc_pending_duration(),
                                 ctx.retry_cnt)
            self._revert_stub(stub, False)
            signed_blinded_hashed_ids = [bytes2int(item) for
                                         item in response.signed_ids]
            assert len(ctx.raw_id_batch) == len(signed_blinded_hashed_ids)
            self._callback_submitter.submit(self._deblind_signed_id_func,
                                            ctx, signed_blinded_hashed_ids)
            next_ctxs = []
            with self._lock:
                assert self._flying_rpc_num > 0
                self._flying_rpc_num -= 1
                req_num = self._flying_sign_rpc_threshold - self._flying_rpc_num
                if req_num > 0:
                    next_ctxs = self._pending_rpc_sign_ctx[:req_num]
                    self._pending_rpc_sign_ctx = \
                            self._pending_rpc_sign_ctx[req_num:]
            for nctx in next_ctxs:
                self._rpc_sign_func(nctx)
        except Exception as e: # pylint: disable=broad-except
            self._revert_stub(stub, True)
            begin_index = ctx.raw_id_batch.begin_index
            end_index = begin_index + len(ctx.raw_id_batch)
            logging.warning("psi signer batch[%d, %d) sign "\
                            "failed for %d times, reson:%s. "\
                            "retry again", begin_index,
                            end_index, ctx.retry_cnt, e)
            with self._lock:
                assert self._flying_rpc_num > 0
                self._flying_rpc_num -= 1
            ctx.trigger_retry()
            self._rpc_sign_func(ctx)

    def _deblind_signed_id_func(self, ctx, signed_blinded_hashed_ids):
        n = self._public_key.n
        deblind_future = self._process_pool_executor.submit(
                FollowerPsiRsaSigner._deblind_signed_id_batch,
                signed_blinded_hashed_ids, ctx.blind_numbers, n
            )
        deblind_cb = functools.partial(self._deblind_callback,
                                       ctx.raw_id_batch, ctx.notify_future)
        deblind_future.add_done_callback(deblind_cb)

    def _deblind_callback(self, raw_id_batch, notify_future, deblind_future):
        try:
            begin_index = raw_id_batch.begin_index
            signed_id_batch = self._make_item_batch(begin_index)
            hashed_signed_hashed_ids = deblind_future.result()
            for idx, item in enumerate(raw_id_batch.items):
                join_id = hashed_signed_hashed_ids[idx]
                signed_id_batch.append((join_id, item))
            notify_future.set_result(signed_id_batch)
        except Exception as e: # pylint: disable=broad-except
            notify_future.set_exception(e)

    @staticmethod
    def _deblind_signed_id_batch(signed_blinded_hashed_ids,
                                 blind_numbers, n):
        signed_hashed_ids = [int(divm(x, r, n).digits()) for x, r in
                             zip(signed_blinded_hashed_ids, blind_numbers)]
        hashed_signed_hashed_ids = \
                PsiRsaSigner._oneway_hash_list(signed_hashed_ids)
        return hashed_signed_hashed_ids
