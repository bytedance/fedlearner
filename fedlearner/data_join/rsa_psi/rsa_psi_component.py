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
import hashlib
import random
import functools
import os
import concurrent.futures as concur_futures

from gmpy2 import powmod, divm # pylint: disable=no-name-in-module

from fedlearner.common import data_join_service_pb2_grpc as dj_grpc
from fedlearner.common import data_join_service_pb2 as dj_pb

from fedlearner.proxy.channel import make_insecure_channel, ChannelType

from fedlearner.data_join import visitor
from fedlearner.data_join.item_batch_seq_processor import \
        ItemBatch, ItemBatchSeqProcessor
from fedlearner.data_join.raw_data_iter_impl import create_raw_data_iter

class RawIdIndexMetaManager(visitor.IndexMetaManager):
    def __init__(self, input_fpaths):
        super(RawIdIndexMetaManager, self).__init__([])
        assert len(input_fpaths) > 0, "input file must not be empty"
        self._input_fpaths = input_fpaths

    def check_index_meta_by_process_index(self, process_index):
        return process_index < len(self._index_metas)

    def _new_index_meta(self, process_index, start_index):
        if process_index >= len(self._input_fpaths):
            return None
        return visitor.IndexMeta(process_index, start_index,
                                 self._input_fpaths[process_index])

class RawIdVisitor(visitor.Visitor):
    def __init__(self, input_file_paths):
        super(RawIdVisitor, self).__init__(
                "raw_id_visitor",
                RawIdIndexMetaManager(input_file_paths)
            )

    def _new_iter(self):
        return create_raw_data_iter(
                dj_pb.RawDataOptions(raw_data_iter='CSV_DICT')
            )

    def active_visitor(self):
        logging.debug("active visitor do nothing for raw id visitor")

class IdBatch(ItemBatch):
    def __init__(self, begin_index):
        self._begin_index = begin_index
        self._raw_ids = []

    def append(self, item):
        if 'raw_id' not in item.record:
            self._raw_ids.append('')
        else:
            self._raw_ids.append(item.record['raw_id'])

    @property
    def begin_index(self):
        return self._begin_index

    def __len__(self):
        return len(self._raw_ids)

    def __lt__(self, other):
        assert isinstance(other, IdBatch)
        return self.begin_index < other.begin_index

    def __iter__(self):
        return iter(self._raw_ids)

class IdBatchFetcher(ItemBatchSeqProcessor):
    def __init__(self, options):
        super(IdBatchFetcher, self).__init__(
                options.batch_processor_options.max_flying_item,
            )
        self._id_visitor = RawIdVisitor(options.input_file_paths)
        self._batch_size = options.batch_processor_options.batch_size

    @classmethod
    def name(cls):
        return 'IdBatchFetcher'

    def _make_item_batch(self, begin_index):
        return IdBatch(begin_index)

    def _make_inner_generator(self, next_index):
        assert next_index is not None
        if next_index == 0:
            self._id_visitor.reset()
        else:
            self._id_visitor.seek(next_index - 1)
        while not self._id_visitor.finished() and not self._fly_item_full():
            next_batch = self._make_item_batch(next_index)
            for (index, item) in self._id_visitor:
                if index != next_index:
                    logging.fatal("index of id visitor is not consecutive, "\
                                  "%d != %d", index, next_index)
                    os._exit(-1) # pylint: disable=protected-access
                next_batch.append(item)
                next_index += 1
                if len(next_batch) >= self._batch_size:
                    break
            yield next_batch, self._id_visitor.finished()
        yield None, self._id_visitor.finished()

class SignedIdBatch(ItemBatch):
    def __init__(self, begin_index):
        self._begin_index = begin_index
        self._ids = []
        self._signed_ids = []

    @property
    def begin_index(self):
        return self._begin_index

    def append(self, id_pair):
        self._ids.append(id_pair[0])
        self._signed_ids.append(id_pair[1])

    def __len__(self):
        assert len(self._ids) == len(self._signed_ids)
        return len(self._ids)

    def __lt__(self, other):
        assert isinstance(other, SignedIdBatch)
        return self.begin_index < other.begin_index

    def __iter__(self):
        assert len(self._ids) == len(self._signed_ids)
        item_cnt = len(self._ids)
        return iter(zip(self._ids, self._signed_ids,
                        list(range(self._begin_index,
                                   self._begin_index+item_cnt))))

class PsiRsaSigner(ItemBatchSeqProcessor):
    def __init__(self, id_batch_fetcher,
                 max_flying_item, process_pool_executor):
        super(PsiRsaSigner, self).__init__(max_flying_item)
        self._id_batch_fetcher = id_batch_fetcher
        self._next_index_to_fetch = None
        self._next_batch_index_hint = None
        self._process_pool_executor = process_pool_executor

    @classmethod
    def name(cls):
        return 'PsiRsaSigner'

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

    def _make_inner_generator(self, next_index):
        assert next_index is not None
        raw_id_batches, next_index = self._consum_raw_id_batch(next_index, 100)
        flying_batch_num = len(raw_id_batches)
        signed_batch_futures = self._promise_signed_batches(raw_id_batches)
        while len(signed_batch_futures) > 0:
            if signed_batch_futures[0].done() or \
                    len(signed_batch_futures) >= 100:
                signed_batch = signed_batch_futures[0].result()
                yield signed_batch, False
                signed_batch_futures = signed_batch_futures[1:]
            required_num = 100 - len(signed_batch_futures)
            raw_id_batches, next_index = \
                    self._consum_raw_id_batch(next_index, required_num)
            signed_batch_futures += self._promise_signed_batches(raw_id_batches)
        yield None, True
        with self._lock:
            self._next_index_to_fetch = next_index

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
            raw_id_batches.append(raw_id_batch)
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
    def _rsa_sign_list(items, d, n):
        return [powmod(x, d, n) for x in items]

class LeaderPsiRsaSigner(PsiRsaSigner):
    def __init__(self, id_batch_fetcher, max_flying_item,
                 process_pool_executor, private_key):
        super(LeaderPsiRsaSigner, self).__init__(id_batch_fetcher,
                                                 max_flying_item,
                                                 process_pool_executor)
        self._private_key = private_key

    @staticmethod
    def _leader_sign_func(raw_id_batch, d, n):
        hashed_ids = PsiRsaSigner._crypto_hash_list(raw_id_batch, True)
        assert len(hashed_ids) == len(raw_id_batch)
        signed_hashed_ids = PsiRsaSigner._rsa_sign_list(hashed_ids, d, n)
        assert len(signed_hashed_ids) == len(raw_id_batch)
        hashed_signed_hashed_ids = \
                PsiRsaSigner._crypto_hash_list(signed_hashed_ids)
        return hashed_signed_hashed_ids

    def _sign_callback(self, raw_id_batch, notify_future, exec_future):
        try:
            hashed_signed_hashed_ids = exec_future.result()
            assert len(hashed_signed_hashed_ids) == len(raw_id_batch)
            begin_index = raw_id_batch.begin_index
            signed_id_batch = self._make_item_batch(begin_index)
            for idx, raw_id in enumerate(raw_id_batch):
                join_id = hashed_signed_hashed_ids[idx]
                signed_id_batch.append((raw_id, join_id))
            notify_future.set_result(signed_id_batch)
        except Exception as e: # pylint: disable=broad-except
            notify_future.set_exception(e)

    def _make_sign_future(self, raw_id_batch):
        notify_future = concur_futures.Future()
        exec_future = self._process_pool_executor.submit(
                LeaderPsiRsaSigner._leader_sign_func, raw_id_batch,
                self._private_key.d, self._private_key.n
            )
        exec_cb = functools.partial(self._sign_callback,
                                    raw_id_batch, notify_future)
        exec_future.add_done_callback(exec_cb)
        return notify_future

class FollowerPsiRsaSigner(PsiRsaSigner):
    def __init__(self, id_batch_fetcher, max_flying_item,
                 process_pool_executor, public_key,
                 leader_signer_addr):
        super(FollowerPsiRsaSigner, self).__init__(id_batch_fetcher,
                                                   max_flying_item,
                                                   process_pool_executor)
        self._public_key = public_key
        channel = make_insecure_channel(leader_signer_addr,
                                        ChannelType.REMOTE)
        self._leader_signer_stub = dj_grpc.RsaPsiSignServiceStub(channel)

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
        hashed_ids = PsiRsaSigner._crypto_hash_list(raw_id_batch, True)
        blind_numbers = [random.SystemRandom().getrandbits(256)
                         for i in range(len(raw_id_batch))]
        blinded_hashed_ids = [(powmod(r, e, n) * x % n).digits()
                              for x, r in zip(hashed_ids, blind_numbers)]
        return (blinded_hashed_ids, blind_numbers)

    def _blind_callback(self, raw_id_batch, notify_future, blind_future):
        try:
            blinded_hashed_ids, blind_numbers = blind_future.result()
            assert len(blinded_hashed_ids) == len(raw_id_batch)
            assert len(blind_numbers) == len(raw_id_batch)
            self._rpc_sign_func(raw_id_batch, blind_numbers,
                                notify_future, blinded_hashed_ids)
        except Exception as e: # pylint: disable=broad-except
            notify_future.set_exception(e)

    def _rpc_sign_func(self, raw_id_batch, blind_numbers,
                       notify_future, blinded_hashed_ids):
        sign_future = self._leader_signer_stub.SignIds.future(
                dj_pb.SignIdsRequest(ids=blinded_hashed_ids)
            )
        sign_cb = functools.partial(self._rpc_sign_callback, raw_id_batch,
                                    blind_numbers, notify_future)
        sign_future.add_done_callback(sign_cb)

    def _rpc_sign_callback(self, raw_id_batch, blind_numbers,
                           notify_future, rpc_future):
        try:
            response = rpc_future.result()
            if response.status.code != 0:
                raise RuntimeError("Failed to call rpc for psi sign, "\
                                   "error code: {}, error message: {}".format(
                                        response.status.code,
                                        response.status.error_message))
            signed_blinded_hashed_ids = \
                    [int(item) for item in response.signed_ids]
            assert len(raw_id_batch) == len(signed_blinded_hashed_ids)
            self._deblind_signed_id_func(raw_id_batch, blind_numbers,
                                         signed_blinded_hashed_ids,
                                         notify_future)
        except Exception as e: # pylint: disable=broad-except
            notify_future.set_exception(e)

    def _deblind_signed_id_func(self, raw_id_batch, blind_numbers,
                                signed_blinded_hashed_ids, notify_future):
        n = self._public_key.n
        deblind_future = self._process_pool_executor.submit(
                FollowerPsiRsaSigner._deblind_signed_id_batch,
                signed_blinded_hashed_ids, blind_numbers, n
            )
        deblind_cb = functools.partial(self._deblind_callback,
                                       raw_id_batch, notify_future)
        deblind_future.add_done_callback(deblind_cb)

    def _deblind_callback(self, raw_id_batch, notify_future, deblind_future):
        try:
            begin_index = raw_id_batch.begin_index
            signed_id_batch = self._make_item_batch(begin_index)
            hashed_signed_hashed_ids = deblind_future.result()
            for idx, raw_id in enumerate(raw_id_batch):
                signed_id_batch.append((raw_id, hashed_signed_hashed_ids[idx]))
            notify_future.set_result(signed_id_batch)
        except Exception as e: # pylint: disable=broad-except
            notify_future.set_exception(e)

    @staticmethod
    def _deblind_signed_id_batch(signed_blinded_hashed_ids,
                                 blind_numbers, n):
        signed_hashed_ids = [divm(x, r, n).digits() for x, r in
                             zip(signed_blinded_hashed_ids, blind_numbers)]
        hashed_signed_hashed_ids = \
                PsiRsaSigner._crypto_hash_list(signed_hashed_ids)
        return hashed_signed_hashed_ids
