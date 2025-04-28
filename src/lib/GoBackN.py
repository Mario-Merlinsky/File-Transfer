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

CONNECTION_TIMEOUT = 5


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
        print(f"[INFO] Tamaño del archivo: {len(file_data)} bytes")
        print(f"[INFO] MSS: {receiver_mss} bytes")
        print(f"[INFO] Tamaño de la ventana: {endpoint.window_size} paquetes")
        print(
            f"[INFO] Número total de paquetes: "
            f"{ceil(len(file_data) / receiver_mss)}")
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
                endpoint.send_message(datagram)
                print(
                    f"[SEND] Paquete enviado: Seq={next_seq + 1}, "
                    f"Tamaño={len(segment)} bytes")
                if next_seq == 0:
                    start_timer()
                next_seq += 1
            try:
                response_data = queue.get()
                rtt = (rtt + (time() - start)) / 2
                response_datagram = Datagram.from_bytes(response_data)

                if response_datagram.is_ack():

                    ack_number = response_datagram.get_ack_number() - 1
                    print(f"ACK recibido: {ack_number + 1}")
                    if ack_number > base:
                        base = ack_number
                        if base == next_seq:
                            stop_timer(timer_event, timer_thread)
                        else:
                            start_timer(timer_event, timer_thread)
                        for seq in list(buffer.keys()):
                            if seq <= ack_number:
                                del buffer[seq]

            except Empty:
                print(f"Timeout actual: {rtt} segundos")
                print("Timeout esperando ACK, reenviando ventana")
                rtt = rtt * 2
                print(f"[SEND] Reenviando ventana desde Seq={base + 1}")
                print(f"[SEND] hasta Seq={next_seq + 1}")
                for seq in range(base, next_seq):
                    if seq in buffer:
                        endpoint.send_message(buffer[seq])
                        print(f"Reenviado paquete: {seq + 1}")

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
            print(f"bytes_written: {bytes_written}")
            print(f"file_size: {file_size}")
            try:
                data = queue.get()
                datagram = Datagram.from_bytes(data)
                print(f"[RECEIVE] Numero de seq esperado: {endpoint.ack}")

                if datagram.get_sequence_number() == endpoint.ack:
                    print(
                        "[RECEIVE] Paquete recibido antes del if: "
                        f"Seq={datagram.get_sequence_number()}")
                    endpoint.increment_ack()
                    file.write(datagram.data)
                    bytes_written += len(datagram.data)
                    print(f"ack: {endpoint.ack}")
                    ack_header = Header(
                        payload_size=0,
                        sequence_number=endpoint.seq,
                        acknowledgment_number=endpoint.ack,
                        flags=Flags.ACK
                    )
                    ack_datagram = Datagram(ack_header, b'').to_bytes()
                    endpoint.send_message(ack_datagram)
                    endpoint.update_last_msg(ack_datagram)
                    print(
                        f"[SEND] ACK enviado acumulativo: {endpoint.ack}")
                else:
                    print(
                        f"[RECEIVE] Paquete fuera de orden: "
                        f"Seq={datagram.get_sequence_number()}")
                    endpoint.send_last_message()

            except Empty:
                print("Timeout esperando paquete, terminando recepción")
                break
            except Exception as e:
                print(f"Error en recepción: {e}")
                raise

        file.close()
        print(
            f"[SERVER] Archivo recibido correctamente: {bytes_written} bytes")
        # se perdio el ultimo ack
        while True:
            try:
                data = queue.get(timeout=CONNECTION_TIMEOUT)
                endpoint.send_last_message()
                continue
            except Empty:
                return


def start_timer(timer_event: Event, timer_thread: Thread, rtt: int):
    stop_timer(timer_event, timer_thread)
    timer_event.clear()
    thread = Thread(target=timer, args=(timer_event, timer_thread, rtt))
    thread.start()


def stop_timer(timer_event, timer_thread: Thread):
    timer_event.set()
    if timer_thread is not None:
        timer_thread.join()
        timer_thread = None
    pass


def timer(timer_event: Event, timer_thread: Thread, rtt: int):
    if not timer_event.wait(rtt):
        pass
    pass
