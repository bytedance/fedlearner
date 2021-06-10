import typing


class BaseKeys:
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
