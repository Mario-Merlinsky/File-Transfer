from io import BufferedWriter
import socket
from queue import Queue
from .Header import Header
from .Flags import Flags
from .Datagram import Datagram
from .RecoveryProtocol import RecoveryProtocol
from .ProtocolID import ProtocolID


class StopAndWait(RecoveryProtocol):
    PROTOCOL_ID = ProtocolID.STOP_AND_WAIT

    def copy(self) -> 'StopAndWait':
        return StopAndWait(self.socket, self.addr)

    def send(self, file_data: bytes, receiver_mss: int):

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
            first_datagram = True
            segment = file_data[i:i + receiver_mss]
            print(len(segment))
            header = Header(
                len(segment),
                self.window_size,
                self.seq,
                self.ack,
                Flags.UPLOAD
            )
            datagram = Datagram(
                header,
                data=segment
            )
            # chequear que el ack del paquete recibido concuerde con
            # el del ultimo enviado
            while True:
                try:
                    print(f"envio datagrama con seq = {self.seq}")
                    self.socket.sendto(datagram.to_bytes(), self.addr)
                    response_data, _ = self.socket.recvfrom(self.window_size)
                    response_datagram = Datagram.from_bytes(response_data)
                    if response_datagram.is_ack():
                        if first_datagram:
                            first_datagram = False
                        else:
                            self.ack = self.seq
                        self.seq += 1
                        print(f"ACK recibido: {self.ack}")
                        break
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Error al recibir ACK: {e}")
        header = Header(0, self.window_size, self.seq, self.ack, Flags.FIN)
        data = b'0'
        datagram = Datagram(header, data)
        self.socket.sendto(datagram.to_bytes(), self.addr)

    def receive(
        self,
        file: BufferedWriter,
        queue: Queue,
        file_size: int,
        last_ack: Datagram
    ):
        bytes_written = 0
        while True:
            data = queue.get()
            datagram = Datagram.from_bytes(data)
            if datagram.is_fin():
                break
            if datagram.get_sequence_number() != self.ack:
                # Me llego un paquete ya recibido
                self.socket.sendto(last_ack.to_bytes(), self.addr)
                continue

            index = datagram.get_payload_size()
            bytes_written += file.write(datagram.data[:index])
            header = Header(0, self.window_size, self.seq, self.ack, Flags.ACK)
            ack = Datagram(header, b'0')
            self.socket.sendto(ack.to_bytes(), self.addr)
            last_ack = ack
            self.seq += 1
            self.ack += 1

        if file_size == bytes_written:
            print("Escribi la cantidad correcta de bytes")
            file.close()
