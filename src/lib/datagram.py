import struct
from flags import Flags
from Upload import UploadACK, UploadSYN
from Download import DownloadACK, DownloadSYN

HEADER_SIZE = struct.calcsize("!HHIIB")


class Datagram:

    def __init__(
        self, payload_size, window_size, sequence_number,
        acknowledgment_number, flags, data
    ):
        self.payload_size = payload_size
        self.window_size = window_size
        self.sequence_number = sequence_number
        self.acknowledgment_number = acknowledgment_number
        self.flags = flags
        self.data = data

    def to_bytes(self):
        return struct.pack(
            "!HHIIB",
            self.payload_size,
            self.window_size,
            self.sequence_number,
            self.acknowledgment_number,
            self.flags
        ) + self.data

    def from_bytes(Self, datagram) -> 'Datagram':
        header = struct.unpack("!HHIIB", datagram[:HEADER_SIZE])
        payload_size, window_size, sequence_number, ack_number, flags = header
        return Datagram(
            payload_size,
            window_size,
            sequence_number,
            ack_number,
            flags,
            datagram[HEADER_SIZE:HEADER_SIZE + payload_size]
        )

    # -> Mensaje
    def analyze(self):
        match self.flags:
            case Flags.SYN | Flags.UPLOAD:
                return UploadSYN.from_bytes(self.data)
            case Flags.ACK | Flags.UPLOAD:
                return UploadACK.from_bytes(self.data)
            case Flags.SYN | Flags.DOWNLOAD:
                return DownloadSYN.from_bytes(self.data)
            case Flags.ACK | Flags.DOWNLOAD:
                return DownloadACK.from_bytes(self.data)
