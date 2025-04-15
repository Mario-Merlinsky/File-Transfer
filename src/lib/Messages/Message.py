from abc import ABC, abstractmethod


class Message(ABC):
    @abstractmethod
    def to_bytes(self):
        pass

    @staticmethod
    @abstractmethod
    def from_bytes():
        pass
