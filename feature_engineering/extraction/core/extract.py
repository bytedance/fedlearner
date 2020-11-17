import logging
from queue import Queue
from collections import defaultdict

_operator_registry = {}


class Operator:
    def __init__(self, feature_name: str, args_name: [str]):
        if feature_name not in _operator_registry:
            _operator_registry[feature_name] = self
        self.feature_name = feature_name

    def __call__(self, *args):
        # 特征提取逻辑实现
        # TODO
        ## 做实际的计算
        pass


class FeatureNode:
    # 跟具体的特征处理算子关联
    def __init__(self, feature_name: str, extract_fn_name: str, depend_features: [Feature]):
        self.name = feature_name
        self.operator = _operator_registry[extract_fn_name]
        self.input_features = depend_features if depend_features else []
        self.in_degree = len(self.input_features)
        self.out = []
        self._init_input_out()
        ##找到对应的方法实例

    def extract(self, feed_dict, db):
        input_dict = {}
        for input_feature in self.input_features:
            input_dict[input_feature.name] = feed_dict[input_feature.name]
        feature_result = self.operator(input_dict)
        feed_dict[self.name] = feature_result

    def _init_input_out(self):
        for depend in self.input_features:
            depend.out.append(self)

    def reset_in_degree(self):
        self.in_degree = len(self.input_features)

# class Node:
#     def __init__(self, graph: Graph, feature: FeatureNode, index):
#         self.feature = feature
#         # 1. 找到op的依赖的op。
#         self.inputs = _find_depends(graph, op)
#         self.index = index
#
#     def run(self, feed_dict):
#         return self.feature.extract(feed_dict)
#
#     def backward(self):
#         pass


class Graph:
    def __init__(self, columns: [str], db):
        self.column_list = columns
        self.db = db
        self.nodes = {}

    def add_feature(self, feature: FeatureNode):
        if feature.name in self.nodes:
            logging.info('Another feature with the same name has been added to Graph:'
                         '{}, with depends: {}.'.format(self.nodes[feature.name],
                                                        self.nodes[feature.name].input_features))
            return
        for depend in feature.input_features:
            if depend.name not in self.nodes:
                raise ValueError('Depend {} of feature {} is not added to Graph.'.format(depend.name, feature.name))
        self.nodes[feature.name] = feature

    def _extract_sub_graph(self, name: str):
        bfs_queue = Queue()
        visited = defaultdict(int)
        sub_graph = set()
        leaf = set()
        node = self.nodes[name]
        if len(node.input_features) > 0:
            sub_graph.add(node)
        else:
            leaf.add(node)
        visited[node.name] = 1
        bfs_queue.put(node)
        while not bfs_queue.empty():
            node = bfs_queue.get()
            for depend in node.input_features:
                if not visited[depend.name]:
                    visited[depend.name] = 1
                    if len(depend.input_features) > 0:
                        sub_graph.add(depend)
                        bfs_queue.put(depend)
                    else:
                        leaf.add(depend)
        return sub_graph, leaf

    def _sort(self, sub_graph, leaf):
        _sorted = Queue()
        unsorted = Queue(leaf)
        while not unsorted.empty():
            node = unsorted.get()
            if node not in leaf:
                _sorted.put(node)
            for out in node.out:
                if out in sub_graph:
                    out.in_degree -= 1
                    if out.in_degree == 0:
                        out.reset_in_degree()
                        unsorted.put(out)
        return _sorted

    def _post_order_traverse(self, feature_name: str):
        sub_graph, leaf = self._extract_sub_graph(feature_name)
        _sorted = self._sort(sub_graph, leaf)
        return _sorted, leaf

    def _retrieve_data_from_db(self, leaf: set) -> dict:
        pass

    def _forward(self, _sorted: Queue, feed_dict: dict):
        while not _sorted.empty():
            node = _sorted.get()
            node.extract(feed_dict)

    def run(self, name, persistent=False) -> ProtoMessage:
        # 1. 检查参数
        # 2. 前向图计算
        _sorted, leaf = self._post_order_traverse(name)
        feed_dict = self._retrieve_data_from_db(leaf)
        self._forward(_sorted, feed_dict)
        result = feed_dict[name]
        return ProtoMessage(result)
