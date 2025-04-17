from pathlib import Path
from time import time
import socket
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


class Client(Endpoint):
    def __init__(
        self,
        recovery_protocol: RecoveryProtocol,
        filepath: str,
        filename: str,
        dest_addr: tuple[str, int],
        dest_sock: socket.socket,
    ):
        super().__init__(recovery_protocol, MSS)
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
        try:
            self.destination_socket.sendto(datagram, self.destination_addr)
            data, _ = self.destination_socket.recvfrom(MSS + HEADER_SIZE)

        except TimeoutError:
            self.handshake(syn_payload, flags)

        return Datagram.from_bytes(data)

    def start_upload(self):
        file_data = read_file(self.filepath)
        self.destination_socket.settimeout(INITIAL_RTT)

        syn_payload = UploadSYN(
            self.filename,
            len(file_data),
            MSS,
            self.recovery_protocol.PROTOCOL_ID
        ).to_bytes()

        flag = Flags.SYN_UPLOAD
        start = time()
        syn_ack = self.handshake(syn_payload, flag)
        rtt = time() - start
        self.destination_socket.settimeout(rtt * TIMEOUT_COEFFICIENT)

        ack_payload = syn_ack.analyze()

        if not isinstance(ack_payload, UploadACK):
            print(ack_payload.msg)
            return

        self.recovery_protocol.send(self, file_data, ack_payload.mss)

    def start_download(self):
        self.destination_socket.settimeout(INITIAL_RTT)
        payload = DownloadSYN(
            self.filename,
            MSS,
            self.recovery_protocol.PROTOCOL_ID
        ).to_bytes()
        flag = Flags.SYN_DOWNLOAD
        start = time()
        syn_ack = self.handshake(payload, flag)
        rtt = time() - start
        self.destination_socket.settimeout(rtt)
        ack_payload = syn_ack.analyze()

        if not isinstance(ack_payload, DownloadACK):
            print(ack_payload.msg)
            return
        filepath = str(Path(self.filepath) / self.filename)
        queue = Queue(-1)
        thread = Thread(
            target=self.enqueue,
            args=(queue,),
            daemon=True
        )
        thread.start()
        with open(filepath, "rb") as file:
            self.recovery_protocol.receive(
                self, file, queue, ack_payload.filesize, None
            )

    def enqueue_incoming_packets(self, queue):
        while True:
            data, _ = self.self.destination_socket.recvfrom(MSS + HEADER_SIZE)
            queue.put(data)
