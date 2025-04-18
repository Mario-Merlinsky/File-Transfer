from io import BufferedWriter
import socket
from queue import Queue, Empty
from .Header import Header
from .Flags import Flags
from .Datagram import Datagram
from .RecoveryProtocol import RecoveryProtocol
from .ProtocolID import ProtocolID
from .Endpoint import Endpoint
from .Messages.Upload import Upload


class StopAndWait(RecoveryProtocol):
    PROTOCOL_ID = ProtocolID.STOP_AND_WAIT

    def copy(self) -> 'StopAndWait':
        return StopAndWait(self.socket, self.addr)

    def send(self, endpoint: Endpoint, file_data: bytes, receiver_mss: int):

        # Caso favorable: Manda un data segment, le llega un ACK de este data
        # segment

        # Casos desfavorables:
        # 1. Manda un data segment, pero el servidor no lo recibe
        # 2. Manda un data segment, pero no llega el ACK de este
        # 3. Manda un data segment, pero el servidor tarda en procesarlo y
        # cuando le llega el ACK al cliente, este ya habia enviado otra vez
        # el segmento por timeout, por lo que el servidor lo recibe y manda
        # un ACK pero ignora el duplicado. El cliente tambien ignora el
        # duplicado del ACK

        for i in range(0, len(file_data), receiver_mss):
            segment = file_data[i:i + receiver_mss]
            endpoint.increment_seq()

            data = Upload(endpoint.seq, segment).to_bytes()

            header = Header(
                len(data),
                endpoint.window_size,
                endpoint.seq,
                endpoint.ack,
                Flags.UPLOAD
            )

            datagram = Datagram(header, data)

            while True:
                try:
                    self.socket.sendto(datagram.to_bytes(), self.addr)
                    response_data, _ = self.socket.recvfrom(
                        endpoint.window_size)

                    response_datagram = Datagram.from_bytes(response_data)

                    if response_datagram.is_ack() and \
                            (response_datagram.get_ack_number()
                                == endpoint.seq):

                        print(f"ACK recibido: {endpoint.seq}")
                        endpoint.increment_ack()
                        break

                except socket.timeout:
                    print("Timeout esperando ACK")
                    continue

                except Exception as e:
                    print(f"Error al recibir ACK: {e}")
                    raise

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

                upload_payload = Upload.from_bytes(datagram.data)

                if datagram.get_sequence_number()-1 == endpoint.ack:
                    endpoint.increment_seq()
                    endpoint.increment_ack()

                    file.write(upload_payload.data)
                    bytes_written += len(upload_payload.data)
                    endpoint.ack = upload_payload.sequence_number

                    ack_header = Header(
                        payload_size=0,
                        window_size=endpoint.window_size,
                        sequence_number=datagram.get_sequence_number(),
                        acknowledgment_number=endpoint.ack,
                        flags=Flags.ACK
                    )
                    endpoint.last_ack = Datagram(ack_header, b'')
                    self.socket.sendto(endpoint.last_ack.to_bytes(), self.addr)
                else:
                    self.socket.sendto(endpoint.last_ack.to_bytes(), self.addr)

            except Empty:
                print("Timeout esperando paquete, terminando recepción")
                break
            except Exception as e:
                print(f"Error en recepción: {e}")
                raise

        file.close()

    def send_error_response(self, message: str, ack_number: int):
        error_datagram = Datagram.make_error_datagram(
                self.seq,
                ack_number,
                message.encode()
            )
        self.socket.sendto(error_datagram.to_bytes(), self.addr)
