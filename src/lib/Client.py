from pathlib import Path
from socket import socket
from socket import timeout
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
        remote_addr: tuple[str, int],
        socket: socket
    ):
        self.endpoint = Endpoint(recovery_protocol, MSS, socket, remote_addr)
        self.filepath = filepath
        self.filename = filename
        self.rp = recovery_protocol

    def handshake(self, syn_payload, flag: Flags):
        header = Header(
            len(syn_payload),
            (MSS + HEADER_SIZE) * self.rp.PROTOCOL_ID,
            INITIAL_SEQ_NUMBER,
            INITIAL_ACK_NUMBER,
            flag,
        )

        datagram = Datagram(header, syn_payload).to_bytes()
        try:
            self.endpoint.send_message(datagram)
            data = self.endpoint.receive_message(MSS + HEADER_SIZE)
            response = Datagram.from_bytes(data)
            if response.is_error():
                print(response.analyze().msg)
                return
            if handshake_is_valid(response.analyze(), flag):
                return response
            self.handshake(syn_payload, flag)
        except timeout:
            self.handshake(syn_payload, flag)

    def start_upload(self):
        file_data = read_file(self.filepath)
        self.endpoint.set_timeout(INITIAL_RTT)

        syn_payload = UploadSYN(
            self.filename,
            len(file_data),
            MSS,
            self.rp.PROTOCOL_ID
        ).to_bytes()

        flag = Flags.SYN_UPLOAD
        start = time()
        syn_ack = self.handshake(syn_payload, flag)
        rtt = time() - start
        self.endpoint.set_timeout(rtt * TIMEOUT_COEFFICIENT)

        ack_payload = syn_ack.analyze()

        if not isinstance(ack_payload, UploadACK):
            print(ack_payload.msg)
            return
        queue = Queue(-1)
        thread = Thread(
            target=self.enqueue_incoming_packets,
            args=(queue,),
            daemon=True
        )
        thread.start()
        self.rp.send(
            self.endpoint, file_data, queue, ack_payload.mss, Flags.UPLOAD
        )

    def start_download(self):
        self.endpoint.set_timeout(INITIAL_RTT)
        payload = DownloadSYN(
            self.filename,
            MSS,
            self.rp.PROTOCOL_ID
        ).to_bytes()
        flag = Flags.SYN_DOWNLOAD
        start = time()
        syn_ack = self.handshake(payload, flag)
        rtt = time() - start
        self.endpoint.set_timeout(rtt * TIMEOUT_COEFFICIENT)
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
            self.rp.receive(
                self.endpoint, file, queue, ack_payload.filesize
            )

        print("Descarga finalizada con exito")

    def enqueue_incoming_packets(self, queue):
        while True:
            try:
                data = self.endpoint.receive_message(MSS + HEADER_SIZE)
            except timeout:
                header = Header(0, 0, 0, 0, Flags.ERROR)
                payload = b'0'
                data = Datagram(header, payload).to_bytes()
            queue.put(data)


def handshake_is_valid(response: Datagram, flag: Flags):
    if (isinstance(response, DownloadACK) and flag == Flags.SYN_DOWNLOAD):
        return True
    if (isinstance(response, UploadACK) and flag == Flags.SYN_UPLOAD):
        return True
    return False
