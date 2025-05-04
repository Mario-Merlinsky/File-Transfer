from .Message import Message


class DownloadACK(Message):
    def __init__(self, filesize: int):
        self.filesize = filesize

    def to_bytes(self) -> bytes:
        return self.filesize.to_bytes(4, byteorder='big')

    @staticmethod
    def from_bytes(bytes: bytes) -> 'DownloadACK':
        filesize = int.from_bytes(bytes[0:4], byteorder='big')

        return DownloadACK(filesize)
