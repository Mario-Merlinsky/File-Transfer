from pathlib import Path
from time import time
from threading import Thread
from queue import Queue
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


class Client:
    def __init__(
        self,
        recovery_protocol: RecoveryProtocol,
        filepath: str,
        filename: str,
    ):
        self.endpoint = Endpoint(recovery_protocol, MSS)
        self.filepath = filepath
        self.filename = filename

    def handshake(self, syn_payload, flags: Flags):
        header = Header(
            len(syn_payload),
            (MSS + HEADER_SIZE) * self.endpoint.recovery_protocol.PROTOCOL_ID,
            INITIAL_SEQ_NUMBER,
            INITIAL_ACK_NUMBER,
            flags,
        )

        datagram = Datagram(header, syn_payload).to_bytes()
        try:
            self.endpoint.recovery_protocol.socket.sendto(
                datagram,
                self.endpoint.recovery_protocol.addr
            )
            data, _ = self.endpoint.recovery_protocol.socket.recvfrom(
                MSS + HEADER_SIZE
            )

        except TimeoutError:
            self.handshake(syn_payload, flags)

        return Datagram.from_bytes(data)

    def start_upload(self):
        file_data = read_file(self.filepath)
        self.endpoint.recovery_protocol.socket.settimeout(INITIAL_RTT)

        syn_payload = UploadSYN(
            self.filename,
            len(file_data),
            MSS,
            self.endpoint.recovery_protocol.PROTOCOL_ID
        ).to_bytes()

        flag = Flags.SYN_UPLOAD
        start = time()
        syn_ack = self.handshake(syn_payload, flag)
        rtt = time() - start
        self.endpoint.recovery_protocol.socket.settimeout(
            rtt * TIMEOUT_COEFFICIENT
        )

        ack_payload = syn_ack.analyze()

        if not isinstance(ack_payload, UploadACK):
            print(ack_payload.msg)
            return

        self.endpoint.recovery_protocol.send(
            self, file_data, ack_payload.mss, Flags.UPLOAD
        )

    def start_download(self):
        self.endpoint.recovery_protocol.socket.settimeout(INITIAL_RTT)
        payload = DownloadSYN(
            self.filename,
            MSS,
            self.endpoint.recovery_protocol.PROTOCOL_ID
        ).to_bytes()
        flag = Flags.SYN_DOWNLOAD
        start = time()
        syn_ack = self.handshake(payload, flag)
        rtt = time() - start
        self.endpoint.recovery_protocol.socket.settimeout(
            rtt * TIMEOUT_COEFFICIENT
        )
        ack_payload = syn_ack.analyze()

        if not isinstance(ack_payload, DownloadACK):
            print(ack_payload.msg)
            return
        filepath = str(Path(self.filepath) / self.filename)
        queue = Queue(-1)
        thread = Thread(
            target=self.enqueue_incoming_packets,
            args=(queue,),
            daemon=True
        )
        thread.start()
        with open(filepath, "wb") as file:
            self.endpoint.recovery_protocol.receive(
                self.endpoint, file, queue, ack_payload.filesize
            )

    def enqueue_incoming_packets(self, queue):
        while True:
            data, _ = self.endpoint.recovery_protocol.socket.recvfrom(
                MSS + HEADER_SIZE
            )
            queue.put(data)


def archivos_iguales(path1, path2):
    with open(path1, 'rb') as f1, open(path2, 'rb') as f2:
        while True:
            b1 = f1.read(4096)
            b2 = f2.read(4096)
            if b1 != b2:
                print("los archivos no son iguales")
                print(b1, b2)
                return
            if not b1:  # Ambos llegaron al final
                break
        print("los archivos son iguales")
        return
