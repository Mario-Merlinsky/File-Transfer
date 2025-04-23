from .Header import Header, HEADER_SIZE
from .Flags import Flags


class Datagram:

    def __init__(
        self, header: Header, data: bytes
    ):
        self.header = header
        self.data = data

    def to_bytes(self):
        return self.header.to_bytes() + self.data

    # -> Mensaje
    def analyze(self):
        return self.header.analyze(self.data)

    def get_sequence_number(self) -> int:
        return self.header.sequence_number

    def get_ack_number(self) -> int:
        return self.header.acknowledgment_number

    def get_payload_size(self) -> int:
        return self.header.payload_size

    def is_fin(self) -> bool:
        return self.header.flags == Flags.FIN

    def is_ack(self) -> bool:
        return self.header.flags == Flags.ACK

    def is_error(self) -> bool:
        return self.header.flags == Flags.ERROR

    def is_download_ack(self) -> bool:
        return self.header.flags == Flags.ACK_DOWNLOAD

    def is_upload_ack(self) -> bool:
        return self.header.flags == Flags.ACK_UPLOAD

    @staticmethod
    def from_bytes(datagram) -> 'Datagram':
        header = Header.from_bytes(datagram)
        return Datagram(
            header,
            datagram[HEADER_SIZE:HEADER_SIZE + header.payload_size]
        )

    @staticmethod
    def make_error_datagram(
        seq_number: int, ack_number, payload: bytes
    ) -> 'Datagram':
        header = Header(len(payload), 0, seq_number, ack_number, Flags.ERROR)
        return Datagram(header, payload)
