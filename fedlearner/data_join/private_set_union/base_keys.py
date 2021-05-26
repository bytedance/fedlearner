class BaseKeys:
    def hash_func(self, item: [bytes, str, int]) -> bytes:
        raise NotImplementedError

    def encrypt_func1(self, item: bytes) -> bytes:
        raise NotImplementedError

    def encrypt_func2(self, item: bytes) -> bytes:
        raise NotImplementedError
