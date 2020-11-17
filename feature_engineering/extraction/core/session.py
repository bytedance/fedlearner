class Session:
    def __init__(self, graph):
        ## 后面可以做分布式扩展
        self.graph = graph

    def run(self, feature_name: str) -> ProtoMessage:
        return self.graph.run(feature_name, args)
