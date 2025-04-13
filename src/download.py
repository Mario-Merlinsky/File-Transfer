import argparse

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
    parser.add_argument('-H', '--host', type=str, help='server IP address')
    parser.add_argument('-p', '--port', type=int, help='server port')
    parser.add_argument('-d', '--dst', type=str, help='destination file path')
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

    if args.verbose and args.quiet:
        parser.error('Cannot use both -v/--verbose and -q/--quiet')

# setear log con modo verbose o quiet
# Llamar cliente con argumentos
