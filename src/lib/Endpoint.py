from typing import Optional
from socket import socket
from lib.Header import HEADER_SIZE
from lib.Datagram import Datagram

from .RecoveryProtocol import RecoveryProtocol

INITIAL_ACK_NUMBER = 0
INITIAL_SEQ_NUMBER = 0


class Endpoint:
    def __init__(
        self,
        recovery_protocol: RecoveryProtocol,
        mss: int,
        socket: socket,
        remote_addr: str
    ):
        self.ack = INITIAL_ACK_NUMBER
        self.seq = INITIAL_SEQ_NUMBER
        if recovery_protocol.PROTOCOL_ID == 1:
            self.window_size = (
                (mss + HEADER_SIZE)
                * recovery_protocol.PROTOCOL_ID
            )
        else:
            self.window_size = recovery_protocol.PROTOCOL_ID
        # self.window_size =
        # (mss + HEADER_SIZE) * recovery_protocol.PROTOCOL_ID
        self.socket = socket
        self.remote_addr = remote_addr

    last_ack: Optional[Datagram] = None

    def increment_seq(self, value: int = 1):
        self.seq += value

    def increment_ack(self, value: int = 1):
        self.ack += value

    def update_window_size(self, new_size: int):
        self.window_size = new_size

    def update_last_ack(self, ack_datagram: Datagram):
        self.last_ack = ack_datagram

    def send_message(self, data: bytes):
        self.socket.sendto(data, self.remote_addr)

    def receive_message(self, buffer_size: int):
        data, _ = self.socket.recvfrom(buffer_size)
        return data

    def set_timeout(self, time: float):
        self.socket.settimeout(time)
