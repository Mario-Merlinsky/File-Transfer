from io import BufferedWriter
from queue import Queue
from abc import ABC, abstractmethod
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
