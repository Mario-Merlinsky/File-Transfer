from io import BufferedWriter
from queue import Queue
from abc import ABC, abstractmethod
from .ProtocolID import ProtocolID
from .Flags import Flags


class RecoveryProtocol(ABC):

    @abstractmethod
    def send(self, endpoint, data: bytes, receiver_mss: int):
        pass

    @abstractmethod
    def receive(
        self,
        endpoint,
        file: BufferedWriter,
        queue: Queue,
        file_size: int,
        flag: Flags
    ):
        pass

    @abstractmethod
    def copy(self) -> 'RecoveryProtocol':
        pass

    PROTOCOL_ID: ProtocolID = 0
