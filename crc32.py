import zlib
#import base64


class crc32_adapter():
    block_size = 32

    def __init__(self):
        self.accumulated = b''

    def update(self, data):
        if self.accumulated == b'':
            self.accumulated = zlib.adler32(data)
        else:
            self.accumulated = zlib.adler32(data, self.accumulated)

    def hexdigest(self):
        return str(self.accumulated)
