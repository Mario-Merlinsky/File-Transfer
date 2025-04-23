from io import BufferedWriter
from time import time
from queue import Empty
from queue import Queue
from .Header import Header
from .Flags import Flags
from .Datagram import Datagram
from .RecoveryProtocol import RecoveryProtocol
from .ProtocolID import ProtocolID
from .Endpoint import Endpoint

CONNECTION_TIMEOUT = 5


class StopAndWait(RecoveryProtocol):
    PROTOCOL_ID = ProtocolID.STOP_AND_WAIT

    def send(
        self,
        endpoint: Endpoint,
        file_data: bytes,
        queue: Queue,
        receiver_mss: int,
        flag: Flags,
        rtt: float
    ):
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
            data = file_data[i:i + receiver_mss]
            endpoint.increment_seq()

            header = Header(
                len(data),
                endpoint.window_size,
                endpoint.seq,
                endpoint.ack,
                flag
            )

            datagram = Datagram(header, data).to_bytes()

            while True:
                try:
                    start = time()
                    endpoint.send_message(datagram)
                    print(f"mande paquete con seq = {header.sequence_number}")
                    response_data = queue.get(timeout=rtt)
                    rtt = (rtt + (time() - start)) / 2
                    print(f"rtt: {rtt}")
                    response_datagram = Datagram.from_bytes(response_data)

                    print(f"flag: {response_datagram.header.flags}")

                    if response_datagram.is_ack():
                        if response_datagram.get_ack_number() == endpoint.seq:
                            print(f"ACK recibido: {endpoint.seq}")
                            endpoint.increment_ack()
                            endpoint.update_last_msg(datagram)
                            break
                        if response_datagram.get_ack_number() < endpoint.seq:
                            continue
                    else:
                        print(f"{endpoint.last_msg}")
                        endpoint.send_message(endpoint.last_msg)
                        print("retransmit")
                        continue

                except Empty:
                    print("Timeout esperando ACK")
                    rtt = rtt * 2
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
                print(f"paquete con seq = {datagram.get_sequence_number()}")
                print(f"esperaba el {endpoint.ack + 1}")
                print(f"flags: {datagram.header.flags}")
                received_payload = datagram.data

                if datagram.get_sequence_number()-1 == endpoint.ack:
                    endpoint.increment_seq()
                    endpoint.increment_ack()

                    file.write(received_payload)
                    bytes_written += len(received_payload)
                    endpoint.ack = datagram.get_sequence_number()

                    ack_header = Header(
                        payload_size=0,
                        window_size=endpoint.window_size,
                        sequence_number=datagram.get_sequence_number(),
                        acknowledgment_number=endpoint.ack,
                        flags=Flags.ACK
                    )
                    ack = Datagram(ack_header, b'').to_bytes()
                    endpoint.last_msg = ack
                    endpoint.send_message(ack)
                else:
                    print(f"duplicado rec: {datagram.get_sequence_number()}")
                    endpoint.send_message(endpoint.last_msg)
            except Exception as e:
                print(f"Error en recepción: {e}")
                raise
        # se perdio el ultimo ack
        file.close()
        while True:
            try:
                data = queue.get(timeout=CONNECTION_TIMEOUT)
                endpoint.send_message(endpoint.last_msg)
                continue
            except Empty:
                return
