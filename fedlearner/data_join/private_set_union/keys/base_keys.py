import typing
import fedlearner.common.private_set_union_pb2 as psu_pb


class BaseKeys:
    def __init__(self, key_info: psu_pb.KeyInfo):
        self.key_info = key_info
        self._key_path = key_info.path

    @classmethod
    def key_type(cls):
        return psu_pb.BaseKey

    def encode(self, item: typing.Any) -> bytes:
        raise NotImplementedError

    def decode(self, item: bytes) -> typing.Any:
        raise NotImplementedError

    def hash(self, item: [bytes, str, int]) -> typing.Any:
        raise NotImplementedError

    def encrypt_1(self, item: typing.Any) -> typing.Any:
        raise NotImplementedError

    def encrypt_2(self, item: typing.Any) -> typing.Any:
        raise NotImplementedError
