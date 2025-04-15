from .Message import Message


class DownloadSYN(Message):
    def __init__(self, filename: str, mss: int, recovery_protocol: int):
        self.filename = filename
        self.mss = mss
        self.recovery_protocol = recovery_protocol

    def to_bytes(self) -> bytes:
        filename_bytes = self.filename.encode('utf-8')
        filename_length = len(filename_bytes).to_bytes(2, byteorder='big')
        mss_bytes = self.mss.to_bytes(2, byteorder='big')
        recovery_bytes = self.recovery_protocol.to_bytes(1, byteorder='big')

        syn_segment = (
            filename_length + filename_bytes + mss_bytes + recovery_bytes
        )
        return syn_segment

    def from_bytes(bytes: bytes) -> 'DownloadSYN':
        filename_lenght = int.from_bytes(bytes[0:2])
        bytes = bytes[2:]
        filename = bytes[:filename_lenght].decode('utf-8')
        bytes = bytes[filename_lenght:]
        mss = int.from_bytes(bytes[:2])
        bytes = bytes[2:]
        recovery_protocol = int.from_bytes(bytes[:2])

        return DownloadSYN(filename, mss, recovery_protocol)
