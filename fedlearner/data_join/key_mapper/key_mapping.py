class BaseKeyMapper(object):
    def leader_mapping(self, item) -> dict:
        raise NotImplementedError

    def follower_mapping(self, item) -> dict:
        raise NotImplementedError

    @classmethod
    def name(cls):
        return "BASE_KEY_MAPPER"
