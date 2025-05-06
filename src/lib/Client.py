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
import logging


MSS = 1024
INITIAL_RTT = 1
TIMEOUT_COEFFICIENT = 4
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
            logging.debug("SYN enviado para upload")
            data = self.endpoint.receive_message()
            logging.debug("Mensaje recibido durante handshake")
            response = Datagram.from_bytes(data)
            logging.debug(f"Flags recibidos: {response.header.flags}")
            if response.is_error():
                logging.error(response.analyze().msg)
                return None
            if response.is_upload_ack():
                self.endpoint.set_timeout(None)
                logging.info("Handshake de upload completado")
                return response
            logging.warning("No es un SYN ACK, reintentando handshake")
            return self.handshake_upload(syn_payload)
        except timeout:
            logging.warning("Timeout durante handshake, reintentando")
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
            logging.debug("SYN enviado para download")
            data = self.endpoint.receive_message()
            logging.debug("Mensaje recibido durante handshake")
            response = Datagram.from_bytes(data)
            logging.debug(f"Flags recibidos: {response.header.flags}")
            if response.is_error():
                logging.error(response.analyze().msg)
                return None
            if not response.is_download_ack():
                logging.warning("No es un SYN ACK, reintentando handshake")
                return self.handshake_download(syn_payload)
            self.endpoint.set_timeout(None)
            self.endpoint.increment_seq()
            self.endpoint.ack = response.get_sequence_number()
            self.handshake_download_2(datagram)
            return response
        except timeout:
            logging.warning("Timeout durante handshake, reintentando")
            return self.handshake_download(syn_payload)

    def handshake_download_2(self, datagram: Datagram):
        header = Header(
            0,
            self.endpoint.seq,
            self.endpoint.ack,
            Flags.ACK,
        )

        datagram = Datagram(header, b"").to_bytes()
        self.endpoint.send_message(datagram)
        self.endpoint.update_last_msg(datagram)
        logging.info("ACK enviado para completar handshake de download")

    def start_upload(self):
        file_data = read_file(self.filepath)
        self.endpoint.set_timeout(INITIAL_RTT)
        if file_data is None:
            return
        syn_payload = UploadSYN(
            self.filename,
            len(file_data),
            self.rp.PROTOCOL_ID
        ).to_bytes()

        start = time()
        syn_ack = self.handshake_upload(syn_payload)
        if syn_ack is None:
            logging.error("Handshake fallido durante upload")
            return
        rtt = time() - start

        ack_payload = syn_ack.analyze()

        if not isinstance(ack_payload, UploadACK):
            logging.error(f"Error durante upload: {ack_payload.msg}")
            return
        queue = Queue(-1)
        thread = Thread(
            target=self.enqueue_incoming_packets,
            args=(queue,),
            daemon=True
        )
        thread.start()
        logging.info("Iniciando envío de archivo")
        self.rp.send(
            self.endpoint,
            file_data,
            queue,
            ack_payload.mss,
            Flags.UPLOAD,
            rtt * TIMEOUT_COEFFICIENT
        )
        logging.info("Archivo enviado con éxito")

        end = time() - start
        logging.info(f"Tiempo de transferencia: {end:.2f} segundos")

    def start_download(self):
        self.endpoint.set_timeout(INITIAL_RTT)
        payload = DownloadSYN(
            self.filename,
            MSS,
            self.rp.PROTOCOL_ID
        ).to_bytes()
        start = time()
        syn_ack = self.handshake_download(payload)
        logging.info("Handshake finalizado para download")
        if syn_ack is None:
            logging.error("Handshake fallido durante download")
            return
        ack_payload = syn_ack.analyze()

        if not isinstance(ack_payload, DownloadACK):
            logging.error(f"Error durante download: {ack_payload.msg}")
            return
        filepath = str(Path(self.filepath) / self.filename)
        queue = Queue(-1)
        thread = Thread(
            target=self.enqueue_incoming_packets,
            args=(queue,),
            daemon=True
        )
        thread.start()
        logging.info(f"Iniciando descarga del archivo: {self.filename}")
        with open(filepath, "wb") as file:
            self.rp.receive(
                self.endpoint, file, queue, ack_payload.filesize
            )
        logging.info("Descarga finalizada con éxito")
        end = time() - start
        logging.info(f"Tiempo de transferencia: {end:.2f} segundos")

    def enqueue_incoming_packets(self, queue):
        while True:
            data = self.endpoint.receive_message()
            queue.put(data)
            logging.debug("Paquete recibido y encolado")
