from fedlearner.data_join.key_mapper.key_mapping import BaseKeyMapper
class DefaultKeyMapper(BaseKeyMapper):
    def leader_mapping(self, item) -> dict:
        return dict()

    def follower_mapping(self, item) -> dict:
        return dict()

    @classmethod
    def name(cls):
        return "DEFAULT"
