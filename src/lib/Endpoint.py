from typing import Optional
from socket import socket
from lib.Datagram import Datagram
from lib.Header import HEADER_SIZE

INITIAL_ACK_NUMBER = 0
INITIAL_SEQ_NUMBER = 0


class Endpoint:
    def __init__(
        self,
        window_size: int,
        mss: int,
        socket: socket,
        remote_addr: str
    ):
        self.ack = INITIAL_ACK_NUMBER
        self.seq = INITIAL_SEQ_NUMBER
        self.window_size = window_size
        self.buffer_size = mss + HEADER_SIZE
        self.socket = socket
        self.remote_addr = remote_addr
        self.last_msg = None

    last_msg: Optional[bytes]

    def increment_seq(self, value: int = 1):
        self.seq += value

    def increment_ack(self, value: int = 1):
        self.ack += value

    def update_window_size(self, new_size: int):
        self.window_size = new_size

    def update_last_msg(self, ack_datagram: Datagram):
        self.last_msg = ack_datagram

    def send_message(self, data: bytes):
        self.socket.sendto(data, self.remote_addr)

    def receive_message(self):
        data, _ = self.socket.recvfrom(self.buffer_size)
        return data

    def set_timeout(self, time: float):
        self.socket.settimeout(time)

    def send_last_message(self):
        self.send_message(self.last_msg)
