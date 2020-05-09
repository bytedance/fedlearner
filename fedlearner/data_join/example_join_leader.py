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

from fedlearner.data_join.joiner_impl import create_example_joiner
from fedlearner.data_join.transmit_leader import TransmitLeader

class ExampleJoinLeader(TransmitLeader):
    class ImplContext(TransmitLeader.ImplContext):
        def __init__(self, etcd, data_source, raw_data_manifest,
                     example_joiner_options, raw_data_options,
                     data_block_builder_options):
            super(ExampleJoinLeader.ImplContext, self).__init__(
                    raw_data_manifest
                )
            self.example_joiner = create_example_joiner(
                    example_joiner_options, raw_data_options,
                    data_block_builder_options, etcd,
                    data_source, raw_data_manifest.partition_id,
                )

        def get_sync_content_by_next_index(self):
            next_index, _ = self.get_peer_index()
            assert next_index >= 0
            return self.example_joiner.get_data_block_meta_by_index(
                    next_index
                )

        def is_produce_finished(self):
            return not self.example_joiner.need_join()

        def make_producer(self):
            with self.example_joiner.make_example_joiner() as joiner:
                for meta in joiner:
                    yield meta

        def __getattr__(self, attr):
            return getattr(self.example_joiner, attr)

    def __init__(self, peer_client, master_client, rank_id,
                 etcd, data_source, raw_data_options,
                 data_block_builder_options, example_joiner_options):
        super(ExampleJoinLeader, self).__init__(peer_client, master_client,
                                                rank_id, etcd, data_source,
                                                'example_join_leader')
        self._raw_data_options = raw_data_options
        self._data_block_builder_options = data_block_builder_options
        self._example_joiner_options = example_joiner_options

    def _make_raw_data_request(self):
        return dj_pb.RawDataRequest(
                data_source_meta=self._data_source.data_source_meta,
                rank_id=self._rank_id,
                partition_id=-1,
                join_example=empty_pb2.Empty()
            )

    def _make_new_impl_ctx(self, raw_data_manifest):
        return ExampleJoinLeader.ImplContext(
                self._etcd, self._data_source,
                raw_data_manifest, self._example_joiner_options,
                self._raw_data_options, self._data_block_builder_options
            )

    def _process_producer_hook(self, impl_ctx):
        assert isinstance(impl_ctx, ExampleJoinLeader.ImplContext)
        self._sniff_join_data_finished(impl_ctx)

    def _sniff_join_data_finished(self, impl_ctx):
        assert isinstance(impl_ctx, ExampleJoinLeader.ImplContext)
        if not impl_ctx.is_sync_example_id_finished() or \
                not impl_ctx.is_raw_data_finished():
            req = dj_pb.RawDataRequest(
                    data_source_meta=self._data_source.data_source_meta,
                    rank_id=self._rank_id,
                    partition_id=impl_ctx.partition_id
                )
            manifest = self._master_client.QueryRawDataManifest(req)
            if manifest.sync_example_id_rep.state == \
                    dj_pb.SyncExampleIdState.Synced:
                impl_ctx.set_sync_example_id_finished()
            if manifest.finished:
                impl_ctx.set_raw_data_finished()

    def _serialize_sync_content(self, item):
        return dj_pb.SyncContent(data_block_meta=item).SerializeToString()

    def _make_finish_raw_data_request(self, impl_ctx):
        return dj_pb.RawDataRequest(
                data_source_meta=self._data_source.data_source_meta,
                rank_id=self._rank_id,
                partition_id=impl_ctx.partition_id,
                join_example=empty_pb2.Empty()
            )
