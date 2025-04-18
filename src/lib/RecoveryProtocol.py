from io import BufferedWriter
from queue import Queue
import socket
from abc import ABC, abstractmethod
from .ProtocolID import ProtocolID


class RecoveryProtocol(ABC):
    def __init__(self, socket: socket.socket, addr: tuple[str, int] = None):
        self.socket = socket
        self.addr = addr

    @abstractmethod
    def send(self, endpoint, data: bytes, receiver_mss: int):
        pass

    @abstractmethod
    def receive(
        self,
        endpoint,
        file: BufferedWriter,
        queue: Queue,
        file_size: int
    ) -> bytes:
        pass

    @abstractmethod
    def copy(self) -> 'RecoveryProtocol':
        pass

    PROTOCOL_ID: ProtocolID = 0
