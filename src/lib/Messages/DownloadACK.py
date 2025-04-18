from .Message import Message


class DownloadACK(Message):
    def __init__(self, filesize: int, mss: int):
        self.filesize = filesize
        self.mss = mss

    def to_bytes(self) -> bytes:
        filesize_bytes = self.filesize.to_bytes(4, byteorder='big')
        mss_bytes = self.mss.to_bytes(2, byteorder='big')

        ack_segment = filesize_bytes + mss_bytes
        return ack_segment

    @staticmethod
    def from_bytes(bytes: bytes) -> 'DownloadACK':
        filesize = int.from_bytes(bytes[0:4], byteorder='big')
        bytes = bytes[4:]
        mss = int.from_bytes(bytes[:2], byteorder='big')

        return DownloadACK(filesize, mss)
