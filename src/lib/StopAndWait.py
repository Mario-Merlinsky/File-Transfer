from io import BufferedWriter
from time import time
from queue import Empty
from queue import Queue
from .Header import Header
from .Flags import Flags
from .Datagram import Datagram
from .RecoveryProtocol import RecoveryProtocol
from .Endpoint import Endpoint
from .ProtocolID import ProtocolID
import logging

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

        logging.info("Iniciando envío de archivo con Stop-and-Wait")
        for i in range(0, len(file_data), receiver_mss):
            data = file_data[i:i + receiver_mss]
            endpoint.increment_seq()

            header = Header(
                len(data),
                endpoint.seq,
                endpoint.ack,
                flag
            )

            datagram = Datagram(header, data).to_bytes()

            while True:
                try:
                    start = time()
                    endpoint.send_message(datagram)
                    logging.debug(
                        f"Paquete enviado: Seq={header.sequence_number}")
                    response_data = queue.get(timeout=rtt)
                    rtt = (rtt + (time() - start)) / 2
                    logging.debug(f"RTT actualizado: {rtt:.2f} segundos")
                    response_datagram = Datagram.from_bytes(response_data)

                    logging.debug(
                        f"Flags recibidos: {response_datagram.header.flags}")

                    if response_datagram.is_ack():
                        if response_datagram.get_ack_number() == endpoint.seq:
                            logging.debug(f"ACK recibido: {endpoint.seq}")
                            endpoint.increment_ack()
                            endpoint.update_last_msg(datagram)
                            break
                        if response_datagram.get_ack_number() < endpoint.seq:
                            ack_number = response_datagram.get_ack_number()
                            logging.debug(
                                f"ACK duplicado recibido: {ack_number}")
                            continue
                    else:
                        logging.warning(
                            "ACK inválido, retransmitiendo último mensaje")
                        endpoint.send_last_message()
                        continue

                except Empty:
                    logging.debug("Timeout esperando ACK, retransmitiendo")
                    rtt = rtt * 2
                    continue

                except Exception as e:
                    logging.error(f"Error al recibir ACK: {e}")
                    raise

    def receive(
        self,
        endpoint: Endpoint,
        file: BufferedWriter,
        queue: Queue,
        file_size: int,
    ):
        logging.info("Iniciando recepción de archivo con Stop-and-Wait")
        bytes_written = 0
        while bytes_written < file_size:
            try:
                data = queue.get()
                datagram = Datagram.from_bytes(data)
                logging.debug(
                    f"Paquete recibido: Seq={datagram.get_sequence_number()},"
                    f" Esperado={endpoint.ack + 1}")
                logging.debug(f"Flags recibidos: {datagram.header.flags}")
                received_payload = datagram.data

                if datagram.get_sequence_number() - 1 == endpoint.ack:
                    endpoint.increment_seq()
                    endpoint.increment_ack()

                    file.write(received_payload)
                    bytes_written += len(received_payload)
                    endpoint.ack = datagram.get_sequence_number()

                    ack_header = Header(
                        payload_size=0,
                        sequence_number=datagram.get_sequence_number(),
                        acknowledgment_number=endpoint.ack,
                        flags=Flags.ACK
                    )
                    ack = Datagram(ack_header, b'').to_bytes()
                    endpoint.last_msg = ack
                    endpoint.send_message(ack)
                    logging.debug(f"ACK enviado: {endpoint.ack}")
                else:
                    seq_number = datagram.get_sequence_number()
                    logging.debug(
                        f"Paquete duplicado recibido: Seq={seq_number}")
                    endpoint.send_last_message()
            except Exception as e:
                logging.error(f"Error en recepción: {e}")
                raise
        file.close()
        logging.info(f"Archivo recibido correctamente: {bytes_written} bytes")
        while True:
            try:
                data = queue.get(timeout=CONNECTION_TIMEOUT)
                endpoint.send_last_message()
                continue
            except Empty:
                logging.info("Conexión cerrada correctamente")
                return
