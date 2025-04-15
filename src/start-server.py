import argparse
import socket
from lib.Server import Server
from lib.GoBackN import GoBackN
from lib.StopAndWait import StopAndWait


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
        choices=['GBN', 'SW'],
        default='GBN'
    )

    args = parser.parse_args()
    recovery_protocol = None
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    match args.protocol:
        case 'GBN':
            recovery_protocol = GoBackN(sock)
        case 'SW':
            recovery_protocol = StopAndWait(sock)
    serv = Server(recovery_protocol, args.host, args.port, args.storage)
    serv.start()
# setear log con modo verbose o quiet


if __name__ == '__main__':
    main()
