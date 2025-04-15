import argparse
import socket
from lib.Client import Client
from lib.StopAndWait import StopAndWait
from lib.GoBackN import GoBackN


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
    parser.add_argument('-d', '--dst', type=str, help='destination file path')
    parser.add_argument('-n', '--name', type=str, help='file name')
    parser.add_argument(
        '-r', '--protocol',
        type=str,
        help='error recovery protocol',
        required=True,
        choices=['GBN', 'SW'],
        default='GBN'
    )

    args = parser.parse_args()
    recovery_protocol = None
    addr = (args.host, args.port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    match args.protocol:
        case 'GBN':
            recovery_protocol = GoBackN(sock, addr)
        case 'SW':
            recovery_protocol = StopAndWait(sock, addr)
    client = Client(
        recovery_protocol,
        args.dst,
        args.name
    )
    client.start_download()


if __name__ == '__main__':
    main()
