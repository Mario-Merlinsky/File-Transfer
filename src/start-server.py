import argparse
import socket
import logging
from lib.logger import setup_logger
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
    setup_logger(args.verbose, args.quiet)
    logging.debug('Iniciando servidor con argumentos: %s', args)
    recovery_protocol = None
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    address = (args.host, args.port)
    sock.bind(address)
    match args.protocol:
        case 'GBN':
            recovery_protocol = GoBackN()
        case 'SW':
            recovery_protocol = StopAndWait()
    logging.debug('Protocolo de recuperacion: %s', recovery_protocol)
    serv = Server(recovery_protocol, address, args.storage, sock)
    logging.info('Servidor creado con protocolo %s', args.protocol)
    serv.start()


if __name__ == '__main__':
    main()
