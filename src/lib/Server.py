from queue import Queue
from socket import socket
from threading import Thread
from .Datagram import Datagram
from .Flags import Flags
from .Util import read_file
from .Messages.UploadSYN import UploadSYN
from .Messages.UploadACK import UploadACK
from .Messages.DownloadSYN import DownloadSYN
from .Messages.DownloadACK import DownloadACK
from .Header import Header
from .RecoveryProtocol import RecoveryProtocol
from .Endpoint import Endpoint
from pathlib import Path


# 25MB
MAX_FILE_SIZE = 26214400
MSS = 1024
INITIAL_RTT = 1
BUFFER_SIZE = 1300


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
        thread = Thread(
            target=self.handle_client,
            args=(client_addr,),
            daemon=True
        )
        self.queues[client_addr] = Queue(-1)
        self.endpoints[client_addr] = Endpoint(
            self.rp, MSS, self.socket, client_addr
        )
        thread.start()

    def start(self):
        print("Servidor creado con exito, esperando mensajes de cliente")

        while True:
            data, client_addr = self.socket.recvfrom(BUFFER_SIZE)
            if client_addr not in self.queues:
                print("Nueva conexion recibida")
                self.setup_new_client(client_addr)
            self.queues[client_addr].put(data)

    def handle_client(self, client_addr: tuple[str, int]):
        queue = self.queues[client_addr]
        filename = None
        file_size = None
        while True:
            try:
                data = queue.get()
                datagram = Datagram.from_bytes(data)
                payload = datagram.analyze()

                match payload:
                    case UploadSYN():
                        filename, file_size = self.handle_upload_syn(
                            datagram, payload, client_addr)
                        self.handle_upload(filename, file_size, client_addr)
                    case DownloadSYN():
                        self.handle_download_syn(
                            datagram, payload, client_addr)

            except Exception as e:
                print(f"Error al manejar el cliente {client_addr}: {e}")
                break

    def handle_upload_syn(
        self,
        client_datagram: Datagram,
        client_payload: UploadSYN,
        client_address: str
    ):
        ack = client_datagram.get_sequence_number()
        error = self.validate_upload_syn(client_payload)
        endp = self.endpoints[client_address]
        if error is not None:
            self.send_error_response(error, ack, endp)
            return

        payload = UploadACK(MSS).to_bytes()

        header = Header(
            payload_size=len(payload),
            window_size=endp.window_size,
            sequence_number=endp.seq,
            acknowledgment_number=ack,
            flags=Flags.ACK_UPLOAD
        )
        ack = Datagram(
            header,
            payload
        )
        endp.last_ack = ack

        endp.send_message(ack.to_bytes())
        return client_payload.filename, client_payload.file_size

    def handle_upload(
        self,
        filename: str,
        file_size: int,
        client_address: str
    ):
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
        except Exception as e:
            print(f"Error durante la recepción del archivo: {e}")
            Path(file_path).unlink(missing_ok=True)
        # TODO
        # cambiar al fin
        self.queues.pop(client_address)
        self.endpoints.pop(client_address)

    def validate_upload_syn(self, client_payload: UploadSYN):
        error = self.validate_syn(client_payload)

        if client_payload.file_size > MAX_FILE_SIZE:
            error = str.encode(
                "El archivo es demasiado para grande para ser subido"
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
                "El metodo de recuperacion entre cliente y servidor "
                "no es consistente"
            )
        return None

    def handle_download_syn(
        self,
        client_datagram: Datagram,
        client_payload: DownloadSYN,
        client_addr: tuple[str, int]
    ):

        endp = self.endpoints[client_addr]
        ack = client_datagram.get_sequence_number()
        error, filepath = self.validate_download_syn(client_payload)

        if error is None:
            file_data = self.send_download_ack(
                client_datagram.get_sequence_number(),
                filepath,
                endp
            )
            queue = self.queues[client_addr]
            self.rp.send(
                endp, file_data, queue, client_payload.mss, Flags.DOWNLOAD
            )
            return

        datagram = Datagram.make_error_datagram(
            endp.seq, ack, error
        ).to_bytes()
        endp.send_message(datagram)
        return

    def send_download_ack(
        self,
        ack_number: int,
        filepath: str,
        endpoint: Endpoint
    ):

        file_data = read_file(filepath)
        payload = DownloadACK(len(file_data), MSS).to_bytes()

        header = Header(
            sequence_number=endpoint.seq,
            acknowledgment_number=ack_number,
            flags=Flags.ACK_DOWNLOAD,
            payload_size=len(payload),
            window_size=endpoint.window_size
        )
        datagram = Datagram(
            header,
            payload
        ).to_bytes()

        endpoint.send_message(datagram)

        return file_data

    def send_error_response(self, payload: bytes, ack: int, endp: Endpoint):
        flag = Flags.ERROR
        header = Header(len(payload), endp.window_size, endp.seq, ack, flag)
        datagram = Datagram(header, payload).to_bytes()
        endp.send_message(datagram)
