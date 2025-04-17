from queue import Queue
from threading import Thread
from .Datagram import Datagram
from .Flags import Flags
from .Messages.UploadSYN import UploadSYN
# from .Messages.DownloadACK import DownloadACK
# from .Messages.DownloadSYN import DownloadSYN
from .Messages.UploadACK import UploadACK
from .RecoveryProtocol import RecoveryProtocol
from .Endpoint import Endpoint
# from .Util import read_file
from pathlib import Path


# 25MB
MAX_FILE_SIZE = 26214400
MSS = 1024
INITIAL_RTT = 1
BUFFER_SIZE = 1300


class Server(Endpoint):
    def __init__(
        self,
        recovery_protocol: RecoveryProtocol,
        host: str,
        port: int,
        storage_path: str,
    ):
        super().__init__(recovery_protocol, MSS)
        self.recovery_protocol = recovery_protocol
        self.host = host
        self.port = port
        self.storage_path = storage_path
        self.queues = {}  # {Cliente: Queue}

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
        thread.start()

    def start(self):
        socket = self.recovery_protocol.socket
        socket.bind((self.host, self.port))
        print("Servidor creado con exito, esperando mensajes de cliente")

        while True:
            data, client_addr = socket.recvfrom(BUFFER_SIZE)
            if client_addr not in self.queues:
                self.setup_new_client(client_addr)
            self.queues[client_addr].put(data)

    def handle_client(self, client_addr: tuple[str, int]):
        rp = self.recovery_protocol.copy()
        rp.addr = client_addr
        queue = self.queues[client_addr]

        while True:
            try:
                data = queue.get()
                datagram = Datagram.from_bytes(data)
                payload = datagram.analyze()

                match payload:
                    case UploadSYN():
                        self.handle_upload_syn(
                            datagram, payload, client_addr, rp)
                    # case DownloadSYN():
                    #     self.handle_download_syn(
                    #         datagram, payload, client_addr, rp)
            except Exception as e:
                print(f"Error al manejar el cliente {client_addr}: {e}")
                break

    def handle_upload_syn(
        self,
        client_datagram: Datagram,
        client_payload: UploadSYN,
        rp: RecoveryProtocol
    ):
        ack = client_datagram.get_sequence_number() + 1
        error = self.validate_upload_payload(client_payload)

        if error is not None:
            self.send_error_response(error, ack, rp)
            return

        file_path = str(Path(self.storage_path) / client_payload.filename)
        try:
            last_ack = self.send_upload_ack(rp)
            print("Enviando ACK de subida")
            with open(file_path, "wb") as file:
                rp.receive(
                    self,
                    file,
                    self.queues[rp.addr],
                    client_payload.file_size,
                    last_ack
                )
        except Exception as e:
            print(f"Error durante la recepción del archivo: {e}")
            Path(file_path).unlink(missing_ok=True)

    def send_upload_ack(
        self,
        rp: RecoveryProtocol,
    ) -> Datagram:
        payload = UploadACK(MSS).to_bytes()
        header = self.create_ack_header(Flags.ACK_UPLOAD)

        header.acknowledgment_number = self.ack
        header.payload_size = len(payload)

        datagram = Datagram(header=header, data=payload)
        rp.socket.sendto(datagram.to_bytes(), rp.addr)

        self.increment_seq()
        self.update_last_ack(datagram)

        return datagram

    def validate_upload_payload(self, client_payload: UploadSYN):
        if self.recovery_protocol.PROTOCOL_ID != \
                client_payload.recovery_protocol:
            return str.encode(
                "El metodo de recuperacion entre cliente y servidor "
                "no es consistente"
            )
        if client_payload.file_size > MAX_FILE_SIZE:
            return str.encode(
                "El archivo es demasiado para grande para ser subido"
            )

        return None

    # def handle_download_syn(
    #     self,
    #     client_datagram: Datagram,
    #     client_payload: DownloadSYN,
    #     client_addr: tuple[str, int],
    #     rp: RecoveryProtocol
    # ):
    #     ack = client_datagram.get_sequence_number()
    #     payload = None
    #     print(self.recovery_protocol.PROTOCOL_ID)
    #     print(client_payload.recovery_protocol)
    #     if self.recovery_protocol.PROTOCOL_ID != \
    #             client_payload.recovery_protocol:
    #        payload = "El metodo de recuperacion entre cliente y servidor no \
    #             es consistente"
    #     if payload is None:
    #         filepath = str(Path(self.storage_path) / client_payload.filename)
    #         self.send_download_ack(INITIAL_RTT + 1, filepath)
    #         rp.send()
    #         return
    #     datagram = Datagram.make_error_datagram(
    #         INITIAL_SEQ_NUMBER, ack, payload
    #     ).to_bytes()
    #     rp.socket.sendto(datagram, client_addr)
    #     return

    # def send_download_ack(
    #     self,
    #     seq_number: int,
    #     filepath: str,
    # ):
    #     rp = self.recovery_protocol.copy()

    #     file_data = read_file(filepath)
    #     payload = DownloadACK(mss=MSS, filesize=file_data).to_bytes()

    #     header = Header(
    #         sequence_number=INITIAL_SEQ_NUMBER,
    #         ack_number=seq_number,
    #         flags=Flags.ACK_DOWNLOAD,
    #         payload_size=len(payload),
    #         window_size=(MSS + HEADER_SIZE) * rp.PROTOCOL_ID
    #     )
    #     datagram = Datagram(
    #         header=header,
    #         payload=DownloadACK(MSS)
    #     )

    #     rp.socket.sendto(datagram.to_bytes(), rp.addr)

    #     return
