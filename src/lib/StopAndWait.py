from io import BufferedWriter
import socket
from queue import Queue
from .Header import Header
from .Flags import Flags
from .Datagram import Datagram
from .RecoveryProtocol import RecoveryProtocol
from .ProtocolID import ProtocolID
from .Endpoint import Endpoint

INITIAL_RTT = 1
TIMEOUT_COEFFICIENT = 1.5


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
            header = Header(
                len(segment),
                endpoint.window_size,
                endpoint.seq,
                endpoint.ack,
                Flags.UPLOAD
            )
            datagram = Datagram(header, data=segment)

            print(
                f"Enviando datagrama con: seq={endpoint.seq} "
                f"ack={endpoint.ack} wdw={endpoint.window_size}"
            )

            while True:
                try:
                    self.socket.sendto(datagram.to_bytes(), self.addr)
                    response_data, _ = self.socket.recvfrom(
                        endpoint.window_size)  # Me quede aca
                    response_datagram = Datagram.from_bytes(response_data)

                    print(
                        f"Recibiendo datagrama con: seq={
                            response_datagram.get_sequence_number()} "
                        f"ack={response_datagram.get_ack_number()} "
                    )

                    print(endpoint.seq)
                    print(endpoint.ack == response_datagram.get_ack_number())

                    if response_datagram.is_ack() and \
                            response_datagram.get_ack_number() == endpoint.seq:

                        print(f"ACK recibido: {endpoint.seq}")
                        endpoint.increment_seq()
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
        last_ack: Datagram
    ):
        bytes_written = 0

        while bytes_written < file_size:
            try:
                data = queue.get(timeout=INITIAL_RTT * TIMEOUT_COEFFICIENT * 2)
                datagram = Datagram.from_bytes(data)

                if datagram.is_fin():
                    break

                current_seq = datagram.get_sequence_number()

                print(current_seq)
                print(f"ack: {endpoint.ack}")

                if current_seq == endpoint.ack:
                    payload_size = datagram.get_payload_size()
                    file.write(datagram.data[:payload_size])
                    bytes_written += payload_size
                    endpoint.increment_seq()

                    ack_header = endpoint.create_ack_header()

                    last_ack = Datagram(ack_header, b'0')
                    self.socket.sendto(last_ack.to_bytes(), self.addr)
                else:
                    # Reenviar último ACK
                    self.socket.sendto(last_ack.to_bytes(), self.addr)

            except queue.Empty:
                print("Timeout esperando paquete")
                break
            except Exception as e:
                print(f"Error durante recepción: {e}")
                raise

        file.close()
