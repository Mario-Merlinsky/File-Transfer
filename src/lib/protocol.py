import socket
from lib.datagram import Datagram
from lib.flags import Flags
from upload import MSS, TIMEOUT


def handle_protocol(
    protocol: str,
    addr: tuple[str, int],
    sock: socket.socket,
    file_data: bytes,
    filename: str
):

    if protocol == "GBN":
        handle_go_back_n(
            addr=addr,
            sock=sock,
            file_data=file_data,
            filename=filename
        )
    else:  # Es S&W
        handle_stop_and_wait(
            addr=addr,
            sock=sock,
            file_data=file_data,
            filename=filename
        )


def handle_go_back_n(
    addr: tuple[str, int],
    sock: socket.socket,
    file_data: bytes,
    filename: str
):

    pass


def handle_stop_and_wait(
    addr: tuple[str, int],
    sock: socket.socket,
    file_data: bytes,
    filename: str
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

    for i in range(0, len(file_data), MSS):
        seq_num = 0
        ack_num = 0  # En el primer envio es 0 porque no tengo nada
        # acknowledgeado desde el cliente
        first_datagram = True
        segment = file_data[i:i + MSS]
        datagram = Datagram(
            flags=Flags.UPDATE,
            sequence_number=seq_num % 2,
            window_size=1,
            payload_size=len(segment),
            acknowledgment_number=ack_num % 2,
            data=segment
        )

        while True:
            try:
                sock.sendto(datagram.to_bytes(), addr)
                response_data, _ = sock.recvfrom(MSS)
                sock.settimeout(TIMEOUT)

                response_datagram = Datagram.from_bytes(response_data)

                if response_datagram.flags == Flags.ACK:
                    if first_datagram:
                        first_datagram = False
                    else:
                        ack_num = seq_num
                    seq_num += 1
                    print(f"ACK recibido: {ack_num}")
                    break
            except socket.timeout:
                print("Timeout: Reenviando segmento")
                continue
            except Exception as e:
                print(f"Error al recibir ACK: {e}")
