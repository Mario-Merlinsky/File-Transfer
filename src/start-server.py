import argparse
import socket
from threading import Thread
from lib.datagram import Datagram
from lib.Upload import UploadACK, UploadSYN
from lib.Download import DownloadACK, DownloadSYN


def handle_upload_syn(
    addr: tuple[str, int],
    sock: socket.socket,
    datagram: Datagram,
    payload: UploadSYN
):
    return


def handle_upload_ack(
    addr: tuple[str, int],
    sock: socket.socket,
    datagram: Datagram,
    payload: UploadACK
):

    return


def handle_download_syn(
    addr: tuple[str, int],
    sock: socket.socket,
    datagram: Datagram,
    payload: DownloadSYN
):
    return


def handle_download_ack(
    addr: tuple[str, int],
    sock: socket.socket,
    datagram: Datagram,
    payload: DownloadACK
):
    return


def handle_message(addr: tuple[str, int], sock: socket.socket, data: bytes):
    datagram = Datagram.from_bytes(data)
    payload = datagram.analyze()

    match payload:
        case UploadSYN():
            handle_upload_syn(addr, sock, datagram, payload)
        case UploadACK():
            handle_upload_ack(addr, sock, datagram, payload)
        case DownloadSYN():
            handle_download_syn(addr, sock, datagram, payload)
        case DownloadACK():
            handle_download_ack(addr, sock, datagram, payload)

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
    parser.add_argument(
        '-H', '--host', type=str, help='service IP address', required=True
    )
    parser.add_argument(
        '-p', '--port', type=int, help='service port', required=True
    )
    parser.add_argument(
        '-s', '--storage',
        type=str,
        help='storage file path',
        required=True
    )
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
    while True:
        data, addr = sock.recvfrom(1300)
        thread = Thread(
            target=handle_message,
            args=(addr, sock, data),
            daemon=True
        )
        thread.start()
# setear log con modo verbose o quiet
# Llamar server con argumentos


if __name__ == '__main__':
    main()
