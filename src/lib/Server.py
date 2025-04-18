from queue import Queue
from threading import Thread
from .Datagram import Datagram
from .Flags import Flags
from .Util import read_file
from .Messages.UploadSYN import UploadSYN
from .Messages.UploadACK import UploadACK
from .Messages.DownloadSYN import DownloadSYN
from .Messages.DownloadACK import DownloadACK
from .Messages.Data import Data
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
        host: str,
        port: int,
        storage_path: str,
    ):
        self.rp = recovery_protocol
        self.host = host
        self.port = port
        self.storage_path = storage_path
        self.queues = {}  # {Cliente: Queue}
        self.endpoints = {}  # {Cliente: Endpoint}

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
        rp = self.rp.copy()
        rp.addr = client_addr
        self.endpoints[client_addr] = Endpoint(rp, MSS)
        thread.start()

    def start(self):
        socket = self.recovery_protocol.socket
        socket.bind((self.host, self.port))
        print("Servidor creado con exito, esperando mensajes de cliente")

        while True:
            data, client_addr = socket.recvfrom(BUFFER_SIZE)
            if client_addr not in self.queues:
                print("Nueva conexion recibida")
                self.setup_new_client(client_addr)
            self.queues[client_addr].put(data)

    def handle_client(self, client_addr: tuple[str, int]):
        queue = self.queues[client_addr]
        filename = None
        file_size = None
        rp = self.endpoints[client_addr].recovery_protocol
        while True:
            try:
                data = queue.get()
                datagram = Datagram.from_bytes(data)
                payload = datagram.analyze()

                match payload:
                    case UploadSYN():
                        filename, file_size = self.handle_upload_syn(
                            datagram, payload, rp)
                    case DownloadSYN():
                        self.handle_download_syn(
                            datagram, payload, client_addr, rp)
                    case Data():
                        self.handle_upload(filename, file_size, rp)

            except Exception as e:
                print(f"Error al manejar el cliente {client_addr}: {e}")
                break

    def handle_upload_syn(
        self,
        client_datagram: Datagram,
        client_payload: UploadSYN,
        rp: RecoveryProtocol
    ):
        ack = client_datagram.get_sequence_number()
        error = self.validate_upload_syn(client_payload)
        if error is not None:
            self.send_error_response(error, ack, rp)
            return

        ack_payload = UploadACK(MSS)
        payload_bytes = ack_payload.to_bytes()
        endp = self.endpoints[rp.addr]
        header = Header(
            payload_size=len(payload_bytes),
            window_size=endp.window_size,
            sequence_number=endp.seq,
            acknowledgment_number=ack,
            flags=Flags.ACK_UPLOAD
        )

        endp.last_ack = Datagram(
            header,
            payload_bytes
        )

        rp.socket.sendto(endp.last_ack.to_bytes(), rp.addr)
        return client_payload.filename, client_payload.file_size

    def handle_upload(
        self,
        filename: str,
        file_size: int,
        rp: RecoveryProtocol
    ):
        endp = self.endpoints[rp.addr]
        file_path = str(Path(self.storage_path) / filename)
        try:
            print("Enviando ACK de subida")
            with open(file_path, "wb") as file:
                rp.receive(
                    endp,
                    file,
                    self.queues[rp.addr],
                    file_size
                )
        except Exception as e:
            print(f"Error durante la recepción del archivo: {e}")
            Path(file_path).unlink(missing_ok=True)
        self.queues.pop(rp.addr)
        self.endpoints.pop(rp.addr)

    def validate_upload_syn(self, client_payload: UploadSYN):
        error = self.validate_syn(client_payload)

        if client_payload.file_size > MAX_FILE_SIZE:
            error = str.encode(
                "El archivo es demasiado para grande para ser subido"
            )

        return error

    def validate_download_syn(self, client_payload: DownloadSYN):
        error = self.validate_syn(client_payload)
        filepath = str(Path(self.storage_path) / client_payload.filename)

        if not filepath.exists():
            error = str.encode(
                "El archivo no existe en el servidor"
            )
        return error, filepath

    def validate_syn(self, client_payload):
        if self.recovery_protocol.PROTOCOL_ID != \
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
        client_addr: tuple[str, int],
        rp: RecoveryProtocol
    ):

        endp = self.endpoints[client_addr]
        ack = client_datagram.get_sequence_number()
        error, filepath = self.validate_download_syn(client_payload)

        if error is None:
            file_data, last_ack = self.send_download_ack(
                client_datagram.get_sequence_number(),
                filepath,
                endp
            )
            rp.send(
                endp, file_data, client_payload.mss, Flags.DOWNLOAD
            )
            return

        datagram = Datagram.make_error_datagram(
            endp.seq, ack, error
        ).to_bytes()
        rp.socket.sendto(datagram, client_addr)
        return

    def send_download_ack(
        self,
        ack_number: int,
        filepath: str,
        endpoint: Endpoint
    ):

        file_data = read_file(filepath)
        payload = DownloadACK(mss=MSS, filesize=len(file_data)).to_bytes()

        header = Header(
            sequence_number=endpoint.seq,
            ack_number=ack_number,
            flags=Flags.ACK_DOWNLOAD,
            payload_size=len(payload),
            window_size=endpoint.window_size
        )
        datagram = Datagram(
            header=header,
            payload=DownloadACK(MSS)
        )

        endpoint.recovery_protocol.socket.sendto(
            datagram.to_bytes(),
            endpoint.recovery_protocol.addr
            )

        return file_data, datagram
