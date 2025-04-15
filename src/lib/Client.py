from time import time
from .Flags import Flags
from .Header import Header, HEADER_SIZE
from .Datagram import Datagram
from .Messages.UploadACK import UploadACK
from .Messages.UploadSYN import UploadSYN
from .Messages.DownloadACK import DownloadACK
from .Messages.DownloadSYN import DownloadSYN
from .RecoveryProtocol import RecoveryProtocol
from .util import read_file

MSS = 1024
INITIAL_RTT = 1
INITIAL_SEQ_NUMBER = 0
INITIAL_ACK_NUMBER = 0
TIMEOUT_COEFFICIENT = 1.5


class Client:
    def __init__(
        self,
        recovery_protocol: RecoveryProtocol,
        filepath: str,
        filename: str,
    ):
        self.recovery_protocol = recovery_protocol
        self.filepath = filepath
        self.filename = filename

    def start_upload(self):
        self.recovery_protocol.seq = INITIAL_SEQ_NUMBER
        self.recovery_protocol.ack = INITIAL_ACK_NUMBER
        self.recovery_protocol.window_size = (
            (MSS + HEADER_SIZE) * self.recovery_protocol.PROTOCOL_ID
        )
        socket = self.recovery_protocol.socket
        server_addr = self.recovery_protocol.addr
        file_data = read_file(self.filepath)
        socket.settimeout(INITIAL_RTT)
        payload = UploadSYN(
            self.filename,
            len(file_data),
            MSS,
            self.recovery_protocol.PROTOCOL_ID
        ).to_bytes()
        flags = Flags.SYN_UPLOAD
        header = Header(
            len(payload),
            (MSS + HEADER_SIZE) * self.recovery_protocol.PROTOCOL_ID,
            INITIAL_SEQ_NUMBER,
            INITIAL_ACK_NUMBER,
            flags,
        )
        self.recovery_protocol.seq += 1
        datagram = Datagram(header, payload).to_bytes()
        start = time()
        print("Iniciando conexion con el servidor")
        socket.sendto(
            datagram, server_addr
        )
        try:
            data, _ = socket.recvfrom(MSS)
            end = time()
            rtt = end - start
            socket.settimeout(rtt * TIMEOUT_COEFFICIENT)
            ack_datagram = Datagram.from_bytes(data)
            ack_payload = ack_datagram.analyze()

            if not isinstance(ack_payload, UploadACK):
                print(ack_payload.msg)
                return

        except socket.timeout:
            print("TIMEOUT: No se recibió un ACK")
            return

        except Exception as e:
            print(f"Error al recibir ACK: {e}")
            return
        self.recovery_protocol.send(file_data, ack_payload.mss)

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
        # TODO
        # RECEIVE
