"""Small copy/insert patches applied to files from an owned Frostpunk installation."""
import struct
import zlib


MAGIC = b"NIDELTA1"
HEADER = struct.Struct("<8sQQ")


def apply_patch(original, compressed):
    data = zlib.decompress(compressed)
    if len(data) < HEADER.size:
        raise ValueError("Truncated patch header")
    magic, source_size, target_size = HEADER.unpack_from(data)
    if magic != MAGIC or source_size != len(original):
        raise ValueError("Patch format or original size does not match")
    result = bytearray()
    position = HEADER.size
    while position < len(data):
        operation = data[position]
        position += 1
        if operation == 0:
            offset, size = struct.unpack_from("<II", data, position)
            position += 8
            if not size or offset + size > len(original):
                raise ValueError("Patch copy exceeds original file")
            result.extend(original[offset:offset + size])
        elif operation == 1:
            size, = struct.unpack_from("<I", data, position)
            position += 4
            if not size or position + size > len(data):
                raise ValueError("Truncated patch insertion")
            result.extend(data[position:position + size])
            position += size
        else:
            raise ValueError("Unknown patch instruction")
        if len(result) > target_size:
            raise ValueError("Patch exceeds target size")
    if len(result) != target_size:
        raise ValueError("Patch target size does not match")
    return bytes(result)
