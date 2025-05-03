from queue import Queue
from queue import Empty
from time import time
from socket import socket
from socket import timeout
from threading import Thread
from .Datagram import Datagram
from .Flags import Flags
from .Util import read_file
from .Messages.UploadSYN import UploadSYN
from .Messages.UploadACK import UploadACK
from .Messages.DownloadSYN import DownloadSYN
from .Messages.DownloadACK import DownloadACK
from .Header import Header, HEADER_SIZE
from .RecoveryProtocol import RecoveryProtocol
from .Endpoint import Endpoint
from pathlib import Path
import logging


# 25MB
MAX_FILE_SIZE = 26214400
MSS = 1024
INITIAL_RTT = 1
WINDOW_SIZE = 4
TIMEOUT_COEFFICIENT = 4


class Server:
    def __init__(
        self,
        recovery_protocol: RecoveryProtocol,
        address: tuple[str, int],
        storage_path: str,
        socket: socket
    ):
        self.rp = recovery_protocol
        self.address = address
        self.storage_path = storage_path
        self.socket = socket
        self.queues = {}  # {Cliente: Queue}
        self.endpoints = {}  # {Cliente: Endpoint}

        self.queues: dict[tuple[str, int], Queue] = {}
        self.endpoints: dict[tuple[str, int], Endpoint] = {}
    # Este metodo recibe los mensajes de clientes
    # Si el cliente es nuevo, se genera un thread para que maneje
    # sus mensajes entrantes
    # Cliente nuevo o no, el mensaje se encolará para luego ser manejado
    # por el thread correspondiente

    def setup_new_client(self, client_addr: tuple[str, int]):
        logging.info(f"Configurando nuevo cliente: {client_addr}")
        thread = Thread(
            target=self.handle_client,
            args=(client_addr,),
            daemon=True
        )
        self.queues[client_addr] = Queue(-1)
        self.endpoints[client_addr] = Endpoint(
            WINDOW_SIZE, MSS, self.socket, client_addr
        )
        thread.start()

    def start(self):
        logging.info(
            "Servidor iniciado con éxito, esperando mensajes de cliente")
        try:
            while True:
                data, client_addr = self.socket.recvfrom(MSS + HEADER_SIZE)
                if client_addr not in self.queues:
                    logging.info(f"Nueva conexión recibida: {client_addr}")
                    self.setup_new_client(client_addr)
                self.queues[client_addr].put(data)
        except KeyboardInterrupt:
            logging.info("Servidor detenido manualmente")

    def handle_client(self, client_addr: tuple[str, int]):
        logging.info(f"Cliente conectado: {client_addr}")
        queue = self.queues[client_addr]
        data = queue.get()
        datagram = Datagram.from_bytes(data)
        payload = datagram.analyze()

        match payload:
            case UploadSYN():
                self.handle_upload_syn(
                    datagram, payload, client_addr)
            case DownloadSYN():
                self.handle_download_syn(
                    datagram, payload, client_addr)

        self.cleanup(client_addr)

    def handle_upload_syn(
        self,
        client_datagram: Datagram,
        client_payload: UploadSYN,
        client_address: str
    ):
        logging.info(f"Recibido SYN para upload de {client_address}")
        ack = client_datagram.get_sequence_number()
        error = self.validate_upload_syn(client_payload)
        endp = self.endpoints[client_address]
        if error is not None:
            logging.error(f"Error en SYN de upload: {error.decode()}")
            send_error_response(error, ack, endp)
            self.cleanup(client_address)
            return

        payload = UploadACK(MSS).to_bytes()

        header = Header(
            payload_size=len(payload),
            sequence_number=endp.seq,
            acknowledgment_number=ack,
            flags=Flags.ACK_UPLOAD
        )
        ack = Datagram(
            header,
            payload
        ).to_bytes()
        endp.update_last_msg(ack)

        endp.send_message(ack)
        logging.info(f"ACK enviado para upload de {client_address}")

        self.handle_upload(
            client_payload.filename,
            client_payload.file_size,
            client_address
        )

    def handle_upload(
        self,
        filename: str,
        file_size: int,
        client_address: str
    ):
        logging.info(
            f"Iniciando recepción de archivo '{filename}' de {client_address}")
        endp = self.endpoints[client_address]
        file_path = str(Path(self.storage_path) / filename)
        try:
            with open(file_path, "wb") as file:
                self.rp.receive(
                    endp,
                    file,
                    self.queues[client_address],
                    file_size
                )
                logging.info(
                    f"Archivo '{filename}' recibido correctamente de "
                    f"{client_address}"
                )
        except Exception as e:
            logging.error(
                f"Error durante la recepción del archivo '{filename}': {e}")
            Path(file_path).unlink(missing_ok=True)

    def validate_upload_syn(self, client_payload: UploadSYN):
        error = self.validate_syn(client_payload)

        if client_payload.file_size > MAX_FILE_SIZE:
            error = str.encode(
                "El archivo es demasiado grande para ser subido"
            )

        return error

    def validate_download_syn(self, client_payload: DownloadSYN):
        error = self.validate_syn(client_payload)
        filepath = Path(self.storage_path) / client_payload.filename

        if not filepath.is_file():
            error = str.encode(
                "El archivo no existe en el servidor"
            )
        return error, str(filepath)

    def validate_syn(self, client_payload):
        if self.rp.PROTOCOL_ID != \
                client_payload.recovery_protocol:
            return str.encode(
                "El método de recuperación entre cliente y servidor "
                "no es consistente"
            )
        return None

    def handle_download_syn(
        self,
        client_datagram: Datagram,
        client_payload: DownloadSYN,
        client_addr: tuple[str, int]
    ):
        logging.info(f"Recibido SYN para download de {client_addr}")
        endp = self.endpoints[client_addr]
        ack = client_datagram.get_sequence_number()
        error, filepath = self.validate_download_syn(client_payload)

        if error is not None:
            logging.error(f"Error en SYN de download: {error.decode()}")
            send_error_response(error, ack, endp)
            self.cleanup(client_addr)
            return
        logging.info(f"SYN válido para download de {client_addr}")
        file_data, rtt = self.send_download_ack(
            client_datagram.get_sequence_number(),
            filepath,
            endp,
            client_addr
        )
        queue = self.queues[client_addr]
        self.rp.send(
            endp,
            file_data,
            queue,
            client_payload.mss,
            Flags.DOWNLOAD,
            rtt * TIMEOUT_COEFFICIENT
        )
        logging.info(f"Archivo enviado a {client_addr}")

    def send_download_ack(
        self,
        ack_number: int,
        filepath: str,
        endpoint: Endpoint,
        client_addr: tuple[str, int]
    ):
        logging.info(f"Enviando ACK de download a {client_addr}")
        file_data = read_file(filepath)
        payload = DownloadACK(len(file_data), MSS).to_bytes()

        header = Header(
            sequence_number=endpoint.seq,
            acknowledgment_number=ack_number,
            flags=Flags.ACK_DOWNLOAD,
            payload_size=len(payload),
        )
        datagram = Datagram(
            header,
            payload
        ).to_bytes()
        endpoint.update_last_msg(datagram)

        queue = self.queues[client_addr]
        rtt = 0
        start = time()
        endpoint.send_message(datagram)
        while True:
            try:
                data = queue.get(timeout=INITIAL_RTT)
                end = time()
                response = Datagram.from_bytes(data)
                if response.is_download_ack():
                    rtt = end - start
                    break
            except Empty:
                logging.debug(
                    f"Timeout esperando download ACK de {client_addr},"
                    f" reenviando")
                start = time()
                endpoint.send_message(datagram)
                continue
        logging.info(f"RTT inicial calculado: {rtt:.2f} segundos")
        return file_data, rtt

    def cleanup(self, client_addr: tuple[str, int]):
        self.queues.pop(client_addr)
        self.endpoints.pop(client_addr)
        logging.info(f"Cliente {client_addr} desconectado")


def send_error_response(payload: bytes, ack: int, endp: Endpoint):
    flag = Flags.ERROR
    header = Header(len(payload), endp.seq, ack, flag)
    datagram = Datagram(header, payload).to_bytes()
    endp.send_message(datagram)
    try:
        data = endp.receive_message()
        response = Datagram.from_bytes(data)
        if response.is_ack():
            return
    except timeout:
        logging.warning("Timeout esperando ACK de error, reenviando")
        return send_error_response(payload, ack, endp)
