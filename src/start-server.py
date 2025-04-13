import argparse
import socket
from threading import Thread

if __name__ == '__main__':
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
# setear log con modo verbose o quiet
# Llamar server con argumentos
