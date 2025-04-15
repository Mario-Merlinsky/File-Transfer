from .Message import Message


class UploadSYN(Message):
    def __init__(
        self, filename: str, file_size: int, mss: int, recovery_protocol: int
    ):
        self.filename = filename
        self.file_size = file_size
        self.mss = mss
        self.recovery_protocol = recovery_protocol

    def to_bytes(self) -> bytes:
        filename_bytes = self.filename.encode('utf-8')
        filename_length = len(filename_bytes).to_bytes(2, byteorder='big')
        file_size_bytes = self.file_size.to_bytes(4, byteorder='big')
        mss_bytes = self.mss.to_bytes(2, byteorder='big')
        recovery_bytes = self.recovery_protocol.to_bytes(1, byteorder='big')
        syn_segment = (
            filename_length + filename_bytes + file_size_bytes +
            mss_bytes + recovery_bytes
        )

        return syn_segment

    @staticmethod
    def from_bytes(bytes: bytes) -> 'UploadSYN':
        filename_lenght = int.from_bytes(bytes[0:2])
        bytes = bytes[2:]
        filename = bytes[:filename_lenght].decode('utf-8')
        bytes = bytes[filename_lenght:]
        file_size = int.from_bytes(bytes[:4])
        bytes = bytes[4:]
        mss = int.from_bytes(bytes[:2])
        bytes = bytes[2:]
        recovery_protocol = int.from_bytes(bytes[:2])

        return UploadSYN(filename, file_size, mss, recovery_protocol)
