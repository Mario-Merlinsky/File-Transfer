from .Message import Message


class Data(Message):
    def __init__(self, data: bytes):
        self.data = data

    def to_bytes(self) -> bytes:
        return self.data

    @staticmethod
    def from_bytes(bytes: bytes) -> 'Data':
        return Data(bytes)
