import socket


def handle_protocol(
    protocol: str,
    addr: tuple[str, int],
    sock: socket.socket,
    file_data: bytes,
    filename: str
):

    if protocol == "GBN":
        pass
    else:  # Es S&W
        pass




