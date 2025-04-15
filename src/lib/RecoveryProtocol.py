import socket
from abc import ABC, abstractmethod
from .ProtocolID import ProtocolID


class RecoveryProtocol(ABC):
    def __init__(self, socket: socket.socket, addr: tuple[str, int] = None):
        self.socket = socket
        self.addr = addr
        self.ack = 0
        self.seq = 0
        self.window_size = 0

    @abstractmethod
    def send(self, data: bytes, mss: int):
        pass

    @abstractmethod
    def receive(self) -> bytes:
        pass

    @abstractmethod
    def copy(self) -> 'RecoveryProtocol':
        pass

    PROTOCOL_ID: ProtocolID = 0
