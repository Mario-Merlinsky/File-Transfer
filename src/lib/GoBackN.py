from io import BufferedWriter
from time import time
from queue import Queue, Empty
from threading import Event
from threading import Thread
from .Header import Header
from .Flags import Flags
from .Datagram import Datagram
from .RecoveryProtocol import RecoveryProtocol
from .Endpoint import Endpoint
from .ProtocolID import ProtocolID
from math import ceil
import logging
from .Server import CONNECTION_TIMEOUT


class GoBackN(RecoveryProtocol):
    PROTOCOL_ID = ProtocolID.GO_BACK_N

    def send(
        self,
        endpoint: Endpoint,
        file_data: bytes,
        queue: Queue,
        receiver_mss: int,
        flag: Flags,
        rtt: float
    ):
        timer_thread = None
        timer_event = Event()
        base = endpoint.seq
        next_seq = base
        endpoint.increment_seq()
        buffer = {}
        logging.info(f"Tamaño del archivo: {len(file_data)} bytes")
        logging.info(f"MSS: {receiver_mss} bytes")
        logging.info(f"Tamaño de la ventana: {endpoint.window_size} paquetes")
        logging.info(
            f"Número total de paquetes: {ceil(len(file_data) / receiver_mss)}")
        while base * receiver_mss < len(file_data):
            while next_seq < base + endpoint.window_size and next_seq * \
                    receiver_mss < len(file_data):
                segment_start = next_seq * receiver_mss
                segment_end = segment_start + receiver_mss
                segment = file_data[segment_start:segment_end]

                header = Header(
                    payload_size=len(segment),
                    sequence_number=next_seq + 1,
                    acknowledgment_number=endpoint.ack,
                    flags=flag
                )
                datagram = Datagram(header, segment).to_bytes()
                buffer[next_seq] = datagram
                start = time()
                if next_seq == 0:
                    start_timer(timer_event, timer_thread, rtt, queue)
                    logging.debug(f"Iniciando timer paquete: {base + 1}")
                endpoint.send_message(datagram)
                logging.debug(
                    f"Paquete enviado: Seq={next_seq + 1}, "
                    f"Tamaño={len(segment)} bytes")
                next_seq += 1
            try:
                response_data = queue.get()
                if isinstance(response_data, Exception):
                    raise response_data
                rtt = (rtt + (time() - start)) / 2
                response_datagram = Datagram.from_bytes(response_data)

                if response_datagram.is_ack():
                    ack_number = response_datagram.get_ack_number() - 1
                    logging.debug(f"ACK recibido: {ack_number + 1}")
                    if ack_number > base:
                        base = ack_number
                        stop_timer(timer_event, timer_thread)
                        start_timer(timer_event, timer_thread, rtt, queue)

            except TimeoutError:
                logging.debug(f"Timeout actual: {rtt} segundos")
                logging.debug("Timeout esperando ACK, reenviando ventana")
                rtt = rtt * 2
                logging.debug(f"Reenviando ventana desde Seq={base + 1}")
                logging.debug(f"Hasta Seq={next_seq + 1}")
                for seq in range(base, next_seq):
                    if seq in buffer:
                        endpoint.send_message(buffer[seq])
                        logging.debug(f"Reenviado paquete: {seq + 1}")
                start_timer(timer_event, timer_thread, rtt, queue)

    def receive(
        self,
        endpoint: Endpoint,
        file: BufferedWriter,
        queue: Queue,
        file_size: int,
    ):
        endpoint.increment_ack()
        bytes_written = 0
        while bytes_written < file_size:
            logging.debug(f"bytes_written: {bytes_written}")
            logging.debug(f"file_size: {file_size}")
            data = queue.get()
            datagram = Datagram.from_bytes(data)
            logging.debug(f"Numero de seq esperado: {endpoint.ack}")

            if datagram.get_sequence_number() == endpoint.ack:
                logging.debug(
                    f"Paquete recibido: Seq={datagram.get_sequence_number()}")
                endpoint.increment_ack()
                file.write(datagram.data)
                bytes_written += len(datagram.data)
                endpoint.increment_seq()
                logging.debug(f"ACK actualizado: {endpoint.ack}")
                ack_header = Header(
                    payload_size=0,
                    sequence_number=endpoint.seq,
                    acknowledgment_number=endpoint.ack,
                    flags=Flags.ACK
                )
                ack_datagram = Datagram(ack_header, b'').to_bytes()
                endpoint.send_message(ack_datagram)
                endpoint.update_last_msg(ack_datagram)
                logging.debug(f"ACK enviado: {endpoint.ack}")
            else:
                seq_num = datagram.get_sequence_number()
                logging.debug(f"Paquete fuera de orden: Seq={seq_num}")
                endpoint.send_last_message()
        file.close()
        logging.info(f"Archivo recibido correctamente: {bytes_written} bytes")
        while True:
            try:
                data = queue.get(timeout=CONNECTION_TIMEOUT)
                endpoint.send_last_message()
                continue
            except Empty:
                return


def start_timer(
    timer_event: Event, timer_thread: Thread, rtt: int, queue: Queue
):
    stop_timer(timer_event, timer_thread)
    timer_event.clear()
    thread = Thread(target=timer, args=(timer_event, timer_thread, rtt, queue))
    thread.start()


def stop_timer(timer_event, timer_thread: Thread):
    timer_event.set()
    if timer_thread is not None:
        timer_thread.join()
        timer_thread = None


def timer(timer_event: Event, timer_thread: Thread, rtt: int, queue: Queue):
    if not timer_event.wait(rtt):
        queue.put(TimeoutError())
