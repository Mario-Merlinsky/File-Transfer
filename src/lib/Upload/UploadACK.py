class UploadACK:
    def __init__(self, mss: int):
        self.mss = mss

    def to_bytes(self) -> bytes:
        mss_bytes = self.mss.to_bytes(2, byteorder='big')
        ack_segment = mss_bytes
        return ack_segment

    def get_bytes(Self, bytes: bytes) -> 'UploadACK':
        mss = int.from_bytes(bytes[:2])
        return UploadACK(mss)
