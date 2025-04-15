from .RecoveryProtocol import RecoveryProtocol
from .ProtocolID import ProtocolID


class GoBackN(RecoveryProtocol):
    PROTOCOL_ID = ProtocolID.GO_BACK_N

    def copy(self) -> 'GoBackN':
        return GoBackN(self.socket, self.addr)

    def send(self, data: bytes):
        pass

    def receive(self):
        pass
