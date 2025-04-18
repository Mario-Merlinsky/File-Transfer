from .Message import Message


class Download(Message):
    def __init__(self, sequence_number: int, data: bytes):
        self.sequence_number = sequence_number
        self.data = data

    def to_bytes(self) -> bytes:
        seq_num_bytes = self.sequence_number.to_bytes(4, byteorder='big')
        data_length = len(self.data).to_bytes(2, byteorder='big')
        upload_segment = seq_num_bytes + data_length + self.data
        return upload_segment

    @staticmethod
    def from_bytes(bytes: bytes) -> 'Download':
        seq_number = int.from_bytes(bytes[0:4], byteorder='big')
        bytes = bytes[4:]
        data_length = int.from_bytes(bytes[0:2], byteorder='big')
        bytes = bytes[2:]
        data = bytes[:data_length]

        return Download(seq_number, data)
