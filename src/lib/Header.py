import struct

from .Flags import Flags
from .Messages.UploadACK import UploadACK
from .Messages.UploadSYN import UploadSYN
from .Messages.DownloadACK import DownloadACK
from .Messages.DownloadSYN import DownloadSYN
from .Messages.Error import Error

HEADER_SIZE = struct.calcsize("!HIIB")


class Header:
    def __init__(
        self, payload_size, sequence_number,
        acknowledgment_number, flags
    ):
        self.payload_size = payload_size
        self.sequence_number = sequence_number
        self.acknowledgment_number = acknowledgment_number
        self.flags = flags

    def to_bytes(self) -> bytes:
        return struct.pack(
            "!HIIB",
            self.payload_size,
            self.sequence_number,
            self.acknowledgment_number,
            self.flags
        )

    def analyze(self, data: bytes):
        match self.flags:
            case Flags.SYN_UPLOAD:
                return UploadSYN.from_bytes(data)
            case Flags.ACK_UPLOAD:
                return UploadACK.from_bytes(data)
            case Flags.SYN_DOWNLOAD:
                return DownloadSYN.from_bytes(data)
            case Flags.ACK_DOWNLOAD:
                return DownloadACK.from_bytes(data)
            case Flags.ERROR:
                return Error.from_bytes(data)

    @staticmethod
    def from_bytes(bytes) -> 'Header':
        header = struct.unpack("!HIIB", bytes[:HEADER_SIZE])
        payload_size, sequence_number, ack_number, flags = header
        return Header(
            payload_size, sequence_number, ack_number, flags
        )
