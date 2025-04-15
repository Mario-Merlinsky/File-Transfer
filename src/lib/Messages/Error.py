from .Message import Message


class Error(Message):
    def __init__(self, msg: str):
        self.msg = msg

    def to_bytes(self):
        return self.msg.encode('utf-8')

    def from_bytes(data: bytes) -> 'Error':
        return Error(data.decode('utf-8'))
