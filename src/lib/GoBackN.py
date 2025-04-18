from io import BufferedWriter
import socket
from queue import Queue, Empty
from .Header import Header
from .Flags import Flags
from .Datagram import Datagram
from .RecoveryProtocol import RecoveryProtocol
from .ProtocolID import ProtocolID
from .Endpoint import Endpoint
from math import ceil


class GoBackN(RecoveryProtocol):
    PROTOCOL_ID = ProtocolID.GO_BACK_N

    def copy(self) -> 'GoBackN':
        return GoBackN(self.socket, self.addr)

    def send(
        self,
        endpoint: Endpoint,
        file_data: bytes,
        queue: Queue,
        receiver_mss: int,
        flag: Flags
    ):
        base = endpoint.seq
        next_seq = base
        buffer = {}
        print(f"[INFO] Tamaño del archivo: {len(file_data)} bytes")
        print(f"[INFO] MSS: {receiver_mss} bytes")
        print(f"[INFO] Tamaño de la ventana: {endpoint.window_size} paquetes")
        print(f"[INFO] Número total de paquetes: {ceil(len(file_data) / receiver_mss)}")

        while base * receiver_mss < len(file_data):
            while next_seq < base + endpoint.window_size and next_seq * receiver_mss < len(file_data):
                segment_start = next_seq * receiver_mss
                segment_end = segment_start + receiver_mss
                segment = file_data[segment_start:segment_end]

                header = Header(
                    payload_size=len(segment),
                    window_size=endpoint.window_size,
                    sequence_number=next_seq,
                    acknowledgment_number=endpoint.ack,
                    flags=Flags.UPLOAD
                )
                datagram = Datagram(header, segment).to_bytes()
                buffer[next_seq] = datagram

                endpoint.send_message(datagram)
                print(f"[SEND] Paquete enviado: Seq={next_seq}, Tamaño={len(segment)} bytes")
                next_seq += 1

            try:
                response_data = queue.get()

                response_datagram = Datagram.from_bytes(response_data)

                if response_datagram.is_ack():
                    ack_number = response_datagram.get_ack_number()
                    print(f"ACK recibido: {ack_number}")

                    if ack_number >= base:
                        base = ack_number
                        for seq in list(buffer.keys()):
                            if seq <= ack_number:
                                del buffer[seq]

            except socket.timeout:
                print(f"Timeout actual: {self.socket.gettimeout()} segundos")
                print("Timeout esperando ACK, reenviando ventana")
                for seq in range(base, next_seq):
                    if seq in buffer:
                        endpoint.send_message(buffer[seq])
                        print(f"Reenviado paquete: {seq}")

    def receive(
        self,
        endpoint: Endpoint,
        file: BufferedWriter,
        queue: Queue,
        file_size: int,
    ):
        bytes_written = 0

        while bytes_written < file_size:
            try:
                data = queue.get()
                datagram = Datagram.from_bytes(data)
                print(f"[RECEIVE] Paquete recibido antes del if: Seq={datagram.get_sequence_number()}")
                print(f"[RECEIVE] ACK esperado: {endpoint.ack}")

                if datagram.get_sequence_number() == endpoint.ack:
                    print(f"[RECEIVE] Paquete recibido: Seq={datagram.get_sequence_number()}")
                    endpoint.increment_ack()
                    file.write(datagram.data)
                    bytes_written += len(datagram.data)

                    if endpoint.ack % endpoint.window_size == 0 or bytes_written >= file_size:
                        ack_header = Header(
                            payload_size=0,
                            window_size=endpoint.window_size,
                            sequence_number=endpoint.seq,
                            acknowledgment_number=endpoint.ack,
                            flags=Flags.ACK
                        )
                        ack_datagram = Datagram(ack_header, b'')
                        endpoint.send_message(ack_datagram.to_bytes())
                        print(f"[SEND] ACK enviado acumulativo: {endpoint.ack}")
                else:
                    print(f"[RECEIVE] Paquete fuera de orden: Seq={datagram.get_sequence_number()}")

            except Empty:
                print("Timeout esperando paquete, terminando recepción")
                break
            except Exception as e:
                print(f"Error en recepción: {e}")
                raise

        file.close()
        print(f"[SERVER] Archivo recibido correctamente: {bytes_written} bytes")
    
    def send_error_response(self, message: str, ack_number: int):
        error_datagram = Datagram.make_error_datagram(
                self.seq,
                ack_number,
                message.encode()
            )
        self.socket.sendto(error_datagram.to_bytes(), self.addr)
