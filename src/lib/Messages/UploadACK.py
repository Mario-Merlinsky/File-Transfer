from .Message import Message


class UploadACK(Message):
    def __init__(self, mss: int):
        self.mss = mss

    def to_bytes(self) -> bytes:
        return self.mss.to_bytes(2, byteorder='big')

    @staticmethod
    def from_bytes(bytes: bytes) -> 'UploadACK':
        mss = int.from_bytes(bytes[:2], byteorder='big')
        return UploadACK(mss)
