import struct


class Protocol:
    def __init__(self):
        self.payload_size = 0
        self.window_size = 0
        self.sequence_number = 0
        self.acknowledgment_number = 0
        self.flags = 0
        self.data = b''

    def to_bytes(self):
        return struct.pack(
            "!HHIIB",
            self.payload_size,
            self.window_size,
            self.sequence_number,
            self.acknowledgment_number,
            self.flags
        ) + self.data

    def get_bytes(self, datagram):
        header_size = struct.calcsize("!HHIIB")
        header = struct.unpack("!HHIIB", datagram[:header_size])
        self.payload_size, self.window_size, self.sequence_number,
        self.acknowledgment_number, self.flags = header
        self.data = datagram[header_size:header_size+self.payload_size]
