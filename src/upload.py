import argparse
import socket
from lib.Upload import UploadSYN, UploadACK
from lib.datagram import Datagram
from lib.flags import Flags
from lib.protocol import handle_protocol

MSS = 1024
MEMORY = 1024 ** 3


def client_upload_message(
    addr: tuple[str, int],
    sock: socket.socket,
    filepath: str,
    filename: str,
    protocol: str
):

    try:
        with open(filepath, "rb") as file:
            file_data = file.read()
    except FileNotFoundError:
        print(f"No se pudo abrir el archivo: {filepath}")
        return

    syn_payload = UploadSYN(filename=filename, filesize=len(file_data))
    syn_datagram = Datagram(
        flags=Flags.SYN | Flags.UPDATE,
        seq=0,
        payload=syn_payload)
    sock.sendto(syn_datagram.to_bytes(), addr)

    try:
        data, _ = sock.recvfrom(MSS)  # Dudas: que poner el MSS es correcto,
        # si esta haciendo algun tipo de await hasta que le caiga algo.
        # si no lo esta haciendo habria que poner un timeout

        ack_datagram = Datagram.from_bytes(data)
        ack_payload = ack_datagram.analyze()

        if ack_payload is not UploadACK:
            print("No se recibió un ACK válido")
            return

    except Exception as e:
        print(f"Error al recibir ACK: {e}")
        return

    handle_protocol(
        protocol=protocol,
        addr=addr,
        sock=sock,
        file_data=file_data,
        filename=filename
        # quizas habria que agregar un Type que sea 1 o 0 si es de envio o
        # recibo
    )

    return


def main():
    parser = argparse.ArgumentParser(description='< command description >')

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='increase output verbosity'
    )
    group.add_argument(
        '-q', '--quiet', action='store_true', help='decrease output verbosity'
    )
    parser.add_argument('-H', '--host', type=str, help='server IP address')
    parser.add_argument('-p', '--port', type=int, help='server port')
    parser.add_argument('-s', '--src', type=str, help='source file path')
    parser.add_argument('-n', '--name', type=str, help='file name')
    parser.add_argument(
        '-r', '--protocol',
        type=str,
        help='error recovery protocol',
        required=True,
        choices=['GBN', 'S&W'],
        default='GBN'
    )

    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((args.host, args.port))

    client_upload_message(
        addr=(args.host, args.port),
        sock=sock,
        filepath=args.src,
        filename=args.name,
        protocol=args.protocol
    )


# setear log con modo verbose o quiet
# Llamar cliente con argumentos

if __name__ == '__main__':
    main()
