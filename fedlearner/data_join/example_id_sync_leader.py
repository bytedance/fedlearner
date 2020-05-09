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

from google.protobuf import empty_pb2

from fedlearner.common import data_join_service_pb2 as dj_pb

from fedlearner.data_join.example_id_batch_fetcher import ExampleIdBatchFetcher
from fedlearner.data_join.transmit_leader import TransmitLeader

class ExampleIdSyncLeader(TransmitLeader):
    class ImplContext(TransmitLeader.ImplContext):
        def __init__(self, etcd, data_source, raw_data_manifest,
                     raw_data_options, batch_processor_options):
            super(ExampleIdSyncLeader.ImplContext, self).__init__(
                    raw_data_manifest
                )
            self.example_id_batch_fetcher = ExampleIdBatchFetcher(
                    etcd, data_source, raw_data_manifest.partition_id,
                    raw_data_options, batch_processor_options
                )
            if raw_data_manifest.finished:
                self.example_id_batch_fetcher.set_input_finished()
            self._hint_idx = None

        @property
        def partition_id(self):
            return self.raw_data_manifest.partition_id

        def is_produce_finished(self):
            peer_finished = self.is_peer_finished()
            next_index, _ = self.get_peer_index()
            return peer_finished or \
                not self.example_id_batch_fetcher.need_process(next_index)

        def make_producer(self):
            next_index, _ = self.get_peer_index()
            return self.example_id_batch_fetcher.make_processor(next_index)

        def get_sync_content_by_next_index(self):
            next_index, dumped_index = self.get_peer_index()
            fetcher = self.example_id_batch_fetcher
            fetch_finished, item, self._hint_idx = \
                fetcher.fetch_item_batch_by_index(next_index, self._hint_idx)
            skip_cnt = fetcher.evict_staless_item_batch(dumped_index)
            if self._hint_idx is not None:
                self._hint_idx -= skip_cnt
                self._hint_idx += 0 if item is None else 1
            return fetch_finished, item

        def is_raw_data_finished(self):
            return self.example_id_batch_fetcher.is_input_finished()

        def set_raw_data_finished(self):
            self.example_id_batch_fetcher.set_input_finished()

    def __init__(self, peer_client, master_client, rank_id, etcd,
                 data_source, raw_data_options, batch_processor_options):
        super(ExampleIdSyncLeader, self).__init__(peer_client, master_client,
                                                  rank_id, etcd, data_source,
                                                  'example_id_syner_leader')
        self._raw_data_options = raw_data_options
        self._batch_processor_options = batch_processor_options

    def _make_raw_data_request(self):
        return dj_pb.RawDataRequest(
                data_source_meta=self._data_source.data_source_meta,
                rank_id=self._rank_id,
                partition_id=-1,
                sync_example_id=empty_pb2.Empty()
            )

    def _make_new_impl_ctx(self, raw_data_manifest):
        return ExampleIdSyncLeader.ImplContext(
                self._etcd, self._data_source, raw_data_manifest,
                self._raw_data_options, self._batch_processor_options
            )

    def _process_producer_hook(self, impl_ctx):
        self._sniff_raw_data_finished(impl_ctx)

    def _sniff_raw_data_finished(self, impl_ctx):
        assert isinstance(impl_ctx, ExampleIdSyncLeader.ImplContext)
        if not impl_ctx.is_raw_data_finished():
            req = dj_pb.RawDataRequest(
                    data_source_meta=self._data_source.data_source_meta,
                    rank_id=self._rank_id,
                    partition_id=impl_ctx.partition_id
                )
            manifest = self._master_client.QueryRawDataManifest(req)
            if manifest.finished:
                impl_ctx.set_raw_data_finished()

    def _serialize_sync_content(self, item):
        sync_ctnt = dj_pb.SyncContent(lite_example_ids=item.lite_example_ids)
        return sync_ctnt.SerializeToString()

    def _make_finish_raw_data_request(self, impl_ctx):
        return dj_pb.RawDataRequest(
                data_source_meta=self._data_source.data_source_meta,
                rank_id=self._rank_id,
                partition_id=impl_ctx.partition_id,
                sync_example_id=empty_pb2.Empty()
            )
