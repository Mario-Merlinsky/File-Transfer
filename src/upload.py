import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Subir archivo al servidor')

    parser.add_argument('-v', '--verbose', action='store_true', help='increase output verbosity')
    parser.add_argument('-q', '--quiet', action='store_true', help='decrease output verbosity')
    parser.add_argument('-H', '--host', type=str, help='server IP address')
    parser.add_argument('-p', '--port', type=int, help='server port')
    parser.add_argument('-s', '--src', type=str, help='source file path')
    parser.add_argument('-n', '--name', type=str, help='file name')
    parser.add_argument('-r', '--protocol', type=str, help='error recovery protocol')

    args = parser.parse_args()

# setear log con modo verbose o quiet
# Llamar cliente con argumentos