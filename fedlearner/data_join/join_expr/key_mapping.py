class BaseKeyMapper(object):
    def leader_mapping(self, item) -> dict:
        raise NotImplementedError

    def follower_mapping(self, item) -> dict:
        raise NotImplementedError

    @classmethod
    def name(cls):
        raise NotImplementedError

class DefaultKeyMapper(BaseKeyMapper):
    def leader_mapping(self, item) -> dict:
        return dict()

    def follower_mapping(self, item) -> dict:
        return dict()

    @classmethod
    def name(cls):
        return "DEFAULT"
