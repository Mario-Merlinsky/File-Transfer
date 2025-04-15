from queue import Queue
from threading import Thread
from .Datagram import Datagram
from .Header import Header, HEADER_SIZE
from .Flags import Flags
from .Messages.UploadSYN import UploadSYN
from .Messages.DownloadACK import DownloadACK
from .Messages.DownloadSYN import DownloadSYN
from .Messages.UploadACK import UploadACK
from .RecoveryProtocol import RecoveryProtocol
from .util import read_file
from pathlib import Path

# 25MB
MAX_FILE_SIZE = 26214400
MSS = 1024
INITIAL_RTT = 1
INITIAL_SEQ_NUMBER = 0
BUFFER_SIZE = 1300


class Server:
    def __init__(
        self,
        recovery_protocol: RecoveryProtocol,
        host: str,
        port: int,
        storage_path: str,
    ):
        self.recovery_protocol = recovery_protocol
        self.host = host
        self.port = port
        self.storage_path = storage_path
        self.clients = set()
        self.queues = {}

    # Este metodo recibe los mensajes de clientes
    # Si el cliente es nuevo, se genera un thread para que maneje
    # sus mensajes entrantes
    # Cliente nuevo o no, el mensaje se encolará para luego ser manejado
    # por el thread correspondiente
    def start(self):
        self.recovery_protocol.seq = INITIAL_SEQ_NUMBER
        self.recovery_protocol.window_size = (
            (MSS + HEADER_SIZE) * self.recovery_protocol.PROTOCOL_ID
        )
        socket = self.recovery_protocol.socket
        socket.bind((self.host, self.port))
        print("Servidor creado con exito, esperando mensajes de cliente")
        while True:
            data, client_addr = socket.recvfrom(BUFFER_SIZE)
            if client_addr not in self.clients:
                thread = Thread(
                    target=self.handle_client,
                    args=(client_addr,),
                    daemon=True
                )
                self.clients.add(client_addr)
                self.queues[client_addr] = Queue(-1)
                thread.start()
            self.queues[client_addr].put(data)

    def handle_client(self, client_addr: tuple[str, int]):
        rp = self.recovery_protocol.copy()
        rp.addr = client_addr
        queue = self.queues[client_addr]
        data = queue.get()
        datagram = Datagram.from_bytes(data)
        payload = datagram.analyze()
        match payload:
            case UploadSYN():
                self.handle_upload_syn(
                    datagram, payload, client_addr, rp
                )
            case DownloadSYN():
                self.handle_download_syn(
                    datagram, payload, client_addr, rp
                )

    def handle_upload_syn(
        self,
        client_datagram: Datagram,
        client_payload: UploadSYN,
        client_adr: tuple[str, int],
        rp: RecoveryProtocol
    ):
        payload = None
        if client_payload.file_size > MAX_FILE_SIZE:
            payload = str.encode(
                "El archivo es demasiado para grande para ser subido"
            )
        if self.recovery_protocol.PROTOCOL_ID != \
                client_payload.recovery_protocol:
            payload = str.encode(
                "El metodo de recuperacion entre cliente y servidor "
                "no es consistente"
            )
        ack = client_datagram.get_sequence_number()
        if payload is None:
            file_path = str(Path(self.storage_path) / client_payload.filename)
            last_ack = self.send_upload_ack(ack, rp)
            file = open(file_path, "wb")
            rp.receive(
                file,
                self.queues[client_adr],
                client_payload.file_size,
                last_ack
            )
            return

        datagram = Datagram.make_error_datagram(
            INITIAL_SEQ_NUMBER, ack, payload
        ).to_bytes()
        rp.socket.sendto(datagram, client_adr)

    def send_upload_ack(
        self,
        seq_number: int,
        rp: RecoveryProtocol,
    ):
        payload = UploadACK(MSS).to_bytes()
        header = Header(
            sequence_number=INITIAL_SEQ_NUMBER,
            acknowledgment_number=seq_number,
            flags=Flags.ACK_UPLOAD,
            payload_size=len(payload),
            window_size=(MSS + HEADER_SIZE) * rp.PROTOCOL_ID
        )
        datagram = Datagram(
            header=header,
            data=payload
        )
        rp.socket.sendto(datagram.to_bytes(), rp.addr)
        rp.seq = header.sequence_number + 1
        rp.ack = seq_number + 1
        return datagram

    def handle_download_syn(
        self,
        client_datagram: Datagram,
        client_payload: DownloadSYN,
        client_addr: tuple[str, int],
        rp: RecoveryProtocol
    ):
        ack = client_datagram.get_sequence_number()
        payload = None
        print(self.recovery_protocol.PROTOCOL_ID)
        print(client_payload.recovery_protocol)
        if self.recovery_protocol.PROTOCOL_ID != \
                client_payload.recovery_protocol:
            payload = "El metodo de recuperacion entre cliente y servidor no \
                es consistente"
        if payload is None:
            filepath = str(Path(self.storage_path) / client_payload.filename)
            self.send_download_ack(INITIAL_RTT + 1, filepath)
            rp.send()
            return
        datagram = Datagram.make_error_datagram(
            INITIAL_SEQ_NUMBER, ack, payload
        ).to_bytes()
        rp.socket.sendto(datagram, client_addr)
        return

    def send_download_ack(
        self,
        seq_number: int,
        filepath: str,
    ):
        rp = self.recovery_protocol.copy()

        file_data = read_file(filepath)
        payload = DownloadACK(mss=MSS, filesize=file_data).to_bytes()

        header = Header(
            sequence_number=INITIAL_SEQ_NUMBER,
            ack_number=seq_number,
            flags=Flags.ACK_DOWNLOAD,
            payload_size=len(payload),
            window_size=(MSS + HEADER_SIZE) * rp.PROTOCOL_ID
        )
        datagram = Datagram(
            header=header,
            payload=DownloadACK(MSS)
        )

        rp.socket.sendto(datagram.to_bytes(), rp.addr)

        return
