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

import unittest

from fedlearner.common import etcd_client
from fedlearner.common import data_join_service_pb2 as dj_pb
from fedlearner.common import common_pb2 as common_pb
from fedlearner.data_join import raw_data_manifest_manager

class TestRawDataManifestManager(unittest.TestCase):
    def test_raw_data_manifest_manager(self):
        cli = etcd_client.EtcdClient('test_cluster', 'localhost:2379',
                                     'fedlearner', True)
        partition_num = 4
        rank_id = 2
        data_source = common_pb.DataSource()
        data_source.data_source_meta.name = "milestone-x"
        data_source.data_source_meta.partition_num = partition_num
        data_source.role = common_pb.FLRole.Leader
        cli.delete_prefix(data_source.data_source_meta.name)
        manifest_manager = raw_data_manifest_manager.RawDataManifestManager(
            cli, data_source)
        manifest_map = manifest_manager.list_all_manifest()
        for i in range(partition_num):
            self.assertTrue(i in manifest_map)
            self.assertEqual(
                manifest_map[i].sync_example_id_rep.state,
                dj_pb.SyncExampleIdState.UnSynced
            )
            self.assertEqual(manifest_map[i].sync_example_id_rep.rank_id, -1)
            self.assertEqual(
                manifest_map[i].join_example_rep.state,
                dj_pb.JoinExampleState.UnJoined
            )
            self.assertEqual(manifest_map[i].join_example_rep.rank_id, -1)
            self.assertFalse(manifest_map[i].finished)

        manifest = manifest_manager.alloc_sync_exampld_id(rank_id)
        self.assertNotEqual(manifest, None)
        partition_id = manifest.partition_id
        manifest_map = manifest_manager.list_all_manifest()
        for i in range(partition_num):
            self.assertTrue(i in manifest_map)
            if i != partition_id:
                self.assertEqual(
                    manifest_map[i].sync_example_id_rep.state,
                    dj_pb.SyncExampleIdState.UnSynced
                )
                self.assertEqual(manifest_map[i].sync_example_id_rep.rank_id, -1)
                self.assertEqual(
                    manifest_map[i].join_example_rep.state,
                    dj_pb.JoinExampleState.UnJoined
                )
                self.assertEqual(manifest_map[i].join_example_rep.rank_id, -1)
            else:
                self.assertEqual(
                    manifest_map[i].sync_example_id_rep.state,
                    dj_pb.SyncExampleIdState.Syncing
                )
                self.assertEqual(manifest_map[i].sync_example_id_rep.rank_id, rank_id)
                self.assertEqual(
                    manifest_map[i].join_example_rep.state,
                    dj_pb.JoinExampleState.UnJoined
                )
                self.assertEqual(manifest_map[i].join_example_rep.rank_id, -1)
            self.assertFalse(manifest_map[i].finished)

        partition_id2 = 3 - partition_id
        rank_id2 = 100
        manifest = manifest_manager.alloc_join_example(rank_id2, partition_id2)
        manifest_map = manifest_manager.list_all_manifest()
        for i in range(partition_num):
            self.assertTrue(i in manifest_map)
            if i == partition_id:
                self.assertEqual(
                    manifest_map[i].sync_example_id_rep.state,
                    dj_pb.SyncExampleIdState.Syncing
                )
                self.assertEqual(manifest_map[i].sync_example_id_rep.rank_id, rank_id)
            else:
                self.assertEqual(
                    manifest_map[i].sync_example_id_rep.state,
                    dj_pb.SyncExampleIdState.UnSynced
                )
                self.assertEqual(manifest_map[i].sync_example_id_rep.rank_id, -1)
            if i == partition_id2:
                self.assertEqual(
                    manifest_map[i].join_example_rep.state,
                    dj_pb.JoinExampleState.Joining
                )
                self.assertEqual(manifest_map[i].join_example_rep.rank_id, rank_id2)
            else:
                self.assertEqual(
                    manifest_map[i].join_example_rep.state,
                    dj_pb.JoinExampleState.UnJoined
                )
                self.assertEqual(manifest_map[i].join_example_rep.rank_id, -1)
            self.assertFalse(manifest_map[i].finished)

        self.assertRaises(Exception,  manifest_manager.finish_join_example,
                rank_id, partition_id)
        self.assertRaises(Exception,  manifest_manager.finish_join_example,
                rank_id2, partition_id2)
        self.assertRaises(Exception,  manifest_manager.finish_sync_example_id,
                -rank_id, partition_id)
        self.assertRaises(Exception,  manifest_manager.finish_sync_example_id,
                rank_id2, partition_id2)
        rank_id3 = 0
        manifest = manifest_manager.alloc_join_example(rank_id3, partition_id)
        manifest_map = manifest_manager.list_all_manifest()
        for i in range(partition_num):
            self.assertTrue(i in manifest_map)
            if i == partition_id:
                self.assertEqual(
                    manifest_map[i].sync_example_id_rep.state,
                    dj_pb.SyncExampleIdState.Syncing
                )
                self.assertEqual(manifest_map[i].sync_example_id_rep.rank_id, rank_id)
            else:
                self.assertEqual(
                    manifest_map[i].sync_example_id_rep.state,
                    dj_pb.SyncExampleIdState.UnSynced
                )
                self.assertEqual(manifest_map[i].sync_example_id_rep.rank_id, -1)
            if i == partition_id:
                self.assertEqual(
                    manifest_map[i].join_example_rep.state,
                    dj_pb.JoinExampleState.Joining
                )
                self.assertEqual(manifest_map[i].join_example_rep.rank_id, rank_id3)
            elif i == partition_id2:
                self.assertEqual(
                    manifest_map[i].join_example_rep.state,
                    dj_pb.JoinExampleState.Joining
                )
                self.assertEqual(manifest_map[i].join_example_rep.rank_id, rank_id2)
            else:
                self.assertEqual(
                    manifest_map[i].join_example_rep.state,
                    dj_pb.JoinExampleState.UnJoined
                )
                self.assertEqual(manifest_map[i].join_example_rep.rank_id, -1)
            self.assertFalse(manifest_map[i].finished)

        self.assertRaises(Exception, manifest_manager.finish_sync_example_id, 
                          rank_id, partition_id)
        self.assertRaises(Exception, manifest_manager.add_raw_data, 
                          partition_id, ['a', 'a', 'b'], False)
        manifest_manager.add_raw_data(partition_id, ['a', 'a', 'b'], True)
        manifest = manifest_manager.get_manifest(partition_id)
        self.assertEqual(manifest.next_process_index, 2)
        manifest_manager.add_raw_data(partition_id, ['a', 'a', 'b', 'c', 'd'], True)
        manifest_map = manifest_manager.list_all_manifest()
        for i in range(partition_num):
            self.assertTrue(i in manifest_map)
            if i == partition_id:
                self.assertEqual(manifest_map[i].next_process_index, 4)
            else:
                self.assertEqual(manifest_map[i].next_process_index, 0)
        manifest_manager.finish_raw_data(partition_id)
        manifest_manager.finish_raw_data(partition_id)
        self.assertRaises(Exception, manifest_manager.add_raw_data, partition_id, 200)
        manifest_manager.finish_sync_example_id(rank_id, partition_id)
        manifest_manager.finish_sync_example_id(rank_id, partition_id)
        manifest_map = manifest_manager.list_all_manifest()
        for i in range(data_source.data_source_meta.partition_num):
            self.assertTrue(i in manifest_map)
            if i == partition_id:
                self.assertEqual(
                    manifest_map[i].sync_example_id_rep.state,
                    dj_pb.SyncExampleIdState.Synced
                )
                self.assertEqual(manifest_map[i].sync_example_id_rep.rank_id, rank_id)
                self.assertTrue(manifest_map[i].finished)
            else:
                self.assertEqual(
                    manifest_map[i].sync_example_id_rep.state,
                    dj_pb.SyncExampleIdState.UnSynced
                )
                self.assertEqual(manifest_map[i].sync_example_id_rep.rank_id, -1)
            if i == partition_id:
                self.assertEqual(
                    manifest_map[i].join_example_rep.state,
                    dj_pb.JoinExampleState.Joining
                )
                self.assertEqual(manifest_map[i].join_example_rep.rank_id, rank_id3)
            elif i == partition_id2:
                self.assertEqual(
                    manifest_map[i].join_example_rep.state,
                    dj_pb.JoinExampleState.Joining
                )
                self.assertEqual(manifest_map[i].join_example_rep.rank_id, rank_id2)
            else:
                self.assertEqual(
                    manifest_map[i].join_example_rep.state,
                    dj_pb.JoinExampleState.UnJoined
                )
                self.assertEqual(manifest_map[i].join_example_rep.rank_id, -1)

        manifest_manager.finish_join_example(rank_id3, partition_id)
        manifest_manager.finish_join_example(rank_id3, partition_id)
        manifest_map = manifest_manager.list_all_manifest()
        for i in range(data_source.data_source_meta.partition_num):
            self.assertTrue(i in manifest_map)
            if i == partition_id:
                self.assertEqual(
                    manifest_map[i].sync_example_id_rep.state,
                    dj_pb.SyncExampleIdState.Synced
                )
                self.assertEqual(manifest_map[i].sync_example_id_rep.rank_id, rank_id)
            else:
                self.assertEqual(
                    manifest_map[i].sync_example_id_rep.state,
                    dj_pb.SyncExampleIdState.UnSynced
                )
                self.assertEqual(manifest_map[i].sync_example_id_rep.rank_id, -1)
            if i == partition_id:
                self.assertEqual(
                    manifest_map[i].join_example_rep.state,
                    dj_pb.JoinExampleState.Joined
                )
                self.assertEqual(manifest_map[i].join_example_rep.rank_id, rank_id3)
            elif i == partition_id2:
                self.assertEqual(
                    manifest_map[i].join_example_rep.state,
                    dj_pb.JoinExampleState.Joining
                )
                self.assertEqual(manifest_map[i].join_example_rep.rank_id, rank_id2)
            else:
                self.assertEqual(
                    manifest_map[i].join_example_rep.state,
                    dj_pb.JoinExampleState.UnJoined
                )
                self.assertEqual(manifest_map[i].join_example_rep.rank_id, -1)

        cli.destory_client_pool()

if __name__ == '__main__':
    unittest.main()
