from io import BufferedWriter
from queue import Queue
import socket
from abc import ABC, abstractmethod
from .ProtocolID import ProtocolID
from .Datagram import Datagram  # Ensure Datagram is imported or defined


class RecoveryProtocol(ABC):
    def __init__(self, socket: socket.socket, addr: tuple[str, int] = None):
        self.socket = socket
        self.addr = addr

    @abstractmethod
    def send(self, endpoint, data: bytes, mss: int):
        pass

    @abstractmethod
    def receive(
        self,
        endpoint,
        file: BufferedWriter,
        queue: Queue,
        file_size: int,
        last_ack: Datagram
    ) -> bytes:
        pass

    @abstractmethod
    def copy(self) -> 'RecoveryProtocol':
        pass

    PROTOCOL_ID: ProtocolID = 0
