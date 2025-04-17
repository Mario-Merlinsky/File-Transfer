from time import time
from .Flags import Flags
from .Header import Header, HEADER_SIZE
from .Datagram import Datagram
from .Messages.UploadACK import UploadACK
from .Messages.UploadSYN import UploadSYN
from .Messages.DownloadACK import DownloadACK
from .Messages.DownloadSYN import DownloadSYN
from .RecoveryProtocol import RecoveryProtocol
from .Endpoint import Endpoint
from .Util import read_file

MSS = 1024
INITIAL_RTT = 1
INITIAL_SEQ_NUMBER = 0
INITIAL_ACK_NUMBER = 0
TIMEOUT_COEFFICIENT = 1.5


class Client(Endpoint):
    def __init__(
        self,
        recovery_protocol: RecoveryProtocol,
        filepath: str,
        filename: str,
        dest_addr: tuple[str, int],
        dest_sock: int,
    ):
        super().__init__(recovery_protocol)
        self.recovery_protocol = recovery_protocol
        self.filepath = filepath
        self.filename = filename
        self.destination_addr = dest_addr
        self.destination_socket = dest_sock

    def handshake(self, syn_payload, flags: Flags):
        header = Header(
            len(syn_payload),
            (MSS + HEADER_SIZE) * self.recovery_protocol.PROTOCOL_ID,
            INITIAL_SEQ_NUMBER,
            INITIAL_ACK_NUMBER,
            flags,
        )

        datagram = Datagram(header, syn_payload).to_bytes()
        self.destination_socket.sendto(datagram, self.destination_addr)
        data, _ = self.destination_socket.recvfrom(MSS)
        return Datagram.from_bytes(data)

    def start_upload(self):
        try:
            file_data = read_file(self.filepath)
            self.destination_socket.settimeout(INITIAL_RTT)

            syn_payload = UploadSYN(
                self.filename,
                len(file_data),
                MSS,
                self.recovery_protocol.PROTOCOL_ID
            ).to_bytes()

            flags = Flags.SYN_UPLOAD

            start = time()
            syn_ack = self.handshake(syn_payload, flags)
            end = time()
            rtt = end - start
            self.destination_socket.settimeout(rtt * TIMEOUT_COEFFICIENT)

            ack_payload = syn_ack.analyze()

            if not isinstance(ack_payload, UploadACK):
                print(ack_payload.msg)
                return

        except Exception as e:
            print(f"Error al recibir ACK: {e}")
            return

        self.recovery_protocol.send(self, file_data, ack_payload.mss)

    def start_download(self):
        socket = self.recovery_protocol.socket
        server_adrr = self.recovery_protocol.addr
        socket.settimeout(INITIAL_RTT)
        payload = DownloadSYN(
            self.filename,
            MSS,
            self.recovery_protocol.PROTOCOL_ID
        ).to_bytes()
        flags = Flags.SYN_DOWNLOAD
        header = Header(
            len(payload),
            (MSS + HEADER_SIZE) * self.recovery_protocol.PROTOCOL_ID,
            INITIAL_SEQ_NUMBER,
            INITIAL_ACK_NUMBER,
            flags,
        )
        datagram = Datagram(header, payload).to_bytes()
        start = time()
        socket.sendto(datagram, server_adrr)
        try:
            data, _ = socket.recvfrom(MSS)
            end = time()
            rtt = end - start
            socket.settimeout(rtt * TIMEOUT_COEFFICIENT)
            ack_datagram = Datagram.from_bytes(data)
            ack_payload = ack_datagram.analyze()
            if not isinstance(ack_payload, DownloadACK):
                print(ack_payload.msg)
                return

        except socket.timeout:
            print("TIMEOUT: No se recibió un ACK")
            return
        except Exception as e:
            print(f"Error al recibir ACK: {e}")
            return

        self.recovery_protocol.receive()
