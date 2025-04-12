class UploadSYN:
    def __init__(self, filename: str, file_size: int, mss: int):
        self.filename = filename
        self.file_size = file_size
        self.mss = mss

    def to_bytes(self) -> bytes:
        filename_bytes = self.filename.encode('utf-8')
        filename_length = len(filename_bytes).to_bytes(2, byteorder='big')
        file_size_bytes = self.file_size.to_bytes(4, byteorder='big')
        mss_bytes = self.mss.to_bytes(2, byteorder='big')

        syn_segment = filename_length + filename_bytes + file_size_bytes
        + mss_bytes

        return syn_segment

    def get_bytes(Self, bytes: bytes) -> 'UploadSYN':
        filename_lenght = int.from_bytes(bytes[0:2])
        bytes = bytes[2:]
        filename = bytes[:filename_lenght].decode('utf-8')
        bytes = bytes[filename_lenght:]
        file_size = int.from_bytes(bytes[:4])
        bytes = bytes[4:]
        mss = int.from_bytes(bytes[:2])

        return UploadSYN(filename, file_size, mss)
