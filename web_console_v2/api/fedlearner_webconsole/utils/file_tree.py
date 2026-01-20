# Copyright 2023 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
from typing import List
from fedlearner_webconsole.utils.file_manager import FileManager
from fedlearner_webconsole.proto.algorithm_pb2 import FileTreeNode


# TODO(hangweiqiang): make it object oriented
class FileTreeBuilder:

    def __init__(self, path: str, relpath: bool = False):
        self.file_manager = FileManager()
        self.path = path
        self.relpath = relpath

    def _recursive_build(self, path: str) -> List[FileTreeNode]:
        files = self.file_manager.ls(path, include_directory=True)
        file_nodes = []
        for file in files:
            filename = os.path.split(file.path)[-1]
            filepath = file.path  # filepath has protocol
            relpath = os.path.relpath(filepath, self.path)  # relative path does not have protocol
            tree_node = FileTreeNode(filename=filename,
                                     path=relpath if self.relpath else filepath,
                                     mtime=file.mtime,
                                     size=file.size,
                                     is_directory=file.is_directory)
            if file.is_directory:
                dir_path = os.path.join(self.path, relpath)  # dir_path has protocol
                files = self._recursive_build(path=dir_path)  # path needs protocol
                tree_node.files.extend(files)
            file_nodes.append(tree_node)
        return file_nodes

    def build(self) -> List[FileTreeNode]:
        return self._recursive_build(self.path)

    def build_with_root(self) -> FileTreeNode:
        info = self.file_manager.info(self.path)
        filename = os.path.split(self.path)[-1]
        root = FileTreeNode(filename=filename,
                            mtime=int(info['mtime'] if 'mtime' in info else info['last_modified_time']),
                            size=info['size'],
                            is_directory=(info['type'] == 'directory'))
        root.files.extend(self._recursive_build(path=self.path))
        return root

    def _get_size(self, tree_node: FileTreeNode):
        file_size = tree_node.size
        if tree_node.is_directory:
            for file in tree_node.files:
                file_size += self._get_size(file)
        return file_size

    def size(self):
        tree_nodes = self.build()
        return sum([self._get_size(node) for node in tree_nodes])
