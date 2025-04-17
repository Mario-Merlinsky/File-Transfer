from typing import Optional
from lib.Header import Header
from lib.Datagram import Datagram
from lib.Flags import Flags
from .RecoveryProtocol import RecoveryProtocol

INITIAL_ACK_NUMBER = 0
INITIAL_SEQ_NUMBER = 0
MSS = 1024
HEADER_SIZE = 20


class Endpoint:
    def __init__(self, recovery_protocol: RecoveryProtocol):
        self.ack = INITIAL_ACK_NUMBER
        self.seq = INITIAL_SEQ_NUMBER
        self.window_size = (MSS + HEADER_SIZE) * recovery_protocol.PROTOCOL_ID
        self.reciving_queue = []

    last_ack: Optional[Datagram] = None

    def increment_seq(self, value: int = 1):
        self.seq += value

    def increment_ack(self, value: int = 1):
        self.ack += value

    def update_window_size(self, new_size: int):
        self.window_size = new_size

    def update_last_ack(self, ack_datagram: Datagram):
        self.last_ack = ack_datagram

    def create_ack_header(self, flags: Flags = Flags.ACK) -> Header:
        return Header(
            payload_size=0,
            window_size=self.window_size,
            sequence_number=self.seq,
            acknowledgment_number=self.ack,
            flags=flags
        )
