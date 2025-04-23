from enum import IntEnum


class Flags(IntEnum):
    UPLOAD = 1
    DOWNLOAD = 2
    SYN = 4
    ACK = 8
    ERROR = 16
    SYN_UPLOAD = SYN | UPLOAD
    ACK_UPLOAD = ACK | UPLOAD
    SYN_DOWNLOAD = SYN | DOWNLOAD
    ACK_DOWNLOAD = ACK | DOWNLOAD
