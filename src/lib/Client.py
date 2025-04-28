from pathlib import Path
from socket import socket
from socket import timeout
from time import time
from threading import Thread
from queue import Queue
from .Flags import Flags
from .Header import Header
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
TIMEOUT_COEFFICIENT = 1.5
WINDOW_SIZE = 4


class Client:
    def __init__(
        self,
        recovery_protocol: RecoveryProtocol,
        filepath: str,
        filename: str,
        remote_addr: tuple[str, int],
        socket: socket
    ):
        self.endpoint = Endpoint(WINDOW_SIZE, MSS, socket, remote_addr)
        self.filepath = filepath
        self.filename = filename
        self.rp = recovery_protocol

    def handshake_upload(self, syn_payload):
        header = Header(
            len(syn_payload),
            self.endpoint.seq,
            self.endpoint.ack,
            Flags.SYN_UPLOAD,
        )

        datagram = Datagram(header, syn_payload).to_bytes()
        try:
            self.endpoint.send_message(datagram)
            print("Mande syn")
            data = self.endpoint.receive_message()
            print("Recibi mensaje")
            response = Datagram.from_bytes(data)
            print(f"flags: {response.header.flags}")
            if response.is_error():
                print(response.analyze().msg)
                return None
            if response.is_upload_ack():
                self.endpoint.set_timeout(None)
                return response
            print("No es un syn ack, handshake devuelta")
            return self.handshake_upload(syn_payload)
        except timeout:
            print("Timeout, handshake devuelta")
            return self.handshake_upload(syn_payload)

    def handshake_download(self, syn_payload):
        header = Header(
            len(syn_payload),
            self.endpoint.seq,
            self.endpoint.ack,
            Flags.SYN_DOWNLOAD,
        )

        datagram = Datagram(header, syn_payload).to_bytes()
        try:
            self.endpoint.send_message(datagram)
            print("Mande syn")
            data = self.endpoint.receive_message()
            print("Recibi mensaje")
            response = Datagram.from_bytes(data)
            print(f"flags: {response.header.flags}")
            if response.is_error():
                print(response.analyze().msg)
                return None
            if not response.is_download_ack():
                print("No es un syn ack, handshake devuelta")
                return self.handshake_download(syn_payload)
            self.endpoint.set_timeout(None)
            self.endpoint.increment_seq()
            self.endpoint.ack = response.get_sequence_number()
            self.handshake_download_2(datagram)
            return response
        except timeout:
            print("Timeout, handshake devuelta")
            return self.handshake_download(syn_payload)

    def handshake_download_2(self, datagram: Datagram):
        header = Header(
            0,
            self.endpoint.seq,
            self.endpoint.ack,
            Flags.ACK_DOWNLOAD,
        )

        datagram = Datagram(header, b"").to_bytes()
        self.endpoint.send_message(datagram)
        self.endpoint.update_last_msg(datagram)

    def start_upload(self):
        file_data = read_file(self.filepath)
        self.endpoint.set_timeout(INITIAL_RTT)

        syn_payload = UploadSYN(
            self.filename,
            len(file_data),
            MSS,
            self.rp.PROTOCOL_ID
        ).to_bytes()

        start = time()
        syn_ack = self.handshake_upload(syn_payload)
        if syn_ack is None:
            return
        rtt = time() - start

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
            self.endpoint,
            file_data,
            queue,
            ack_payload.mss,
            Flags.UPLOAD,
            rtt * TIMEOUT_COEFFICIENT
        )

    def start_download(self):
        self.endpoint.set_timeout(INITIAL_RTT)
        payload = DownloadSYN(
            self.filename,
            MSS,
            self.rp.PROTOCOL_ID
        ).to_bytes()
        syn_ack = self.handshake_download(payload)
        print("Handhsake finalizado")
        if syn_ack is None:
            return
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
            data = self.endpoint.receive_message()
            queue.put(data)
