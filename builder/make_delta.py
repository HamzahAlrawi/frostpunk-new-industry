"""Build copy/insert patches without including the original game files."""
import struct
import zlib

from patch_format import HEADER, MAGIC


def matching_prefix(original, revised, source, target):
    size = 16
    limit = min(len(original) - source, len(revised) - target)
    while size + 4096 <= limit and original[source + size:source + size + 4096] == revised[target + size:target + size + 4096]:
        size += 4096
    for step in (2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1):
        if size + step <= limit and original[source + size:source + size + step] == revised[target + size:target + size + step]:
            size += step
    return size


def make_delta(original, revised):
    anchors = {}
    for position in range(0, len(original) - 15, 16):
        key = original[position:position + 16]
        first, _ = anchors.get(key, (position, position))
        anchors[key] = (first, position)
    data = bytearray(HEADER.pack(MAGIC, len(original), len(revised)))
    position = 0
    literal = 0
    copied = 0
    while position + 16 <= len(revised):
        candidates = anchors.get(revised[position:position + 16])
        if candidates is None:
            position += 1
            continue
        source = max(candidates, key=lambda value: matching_prefix(original, revised, value, position))
        size = matching_prefix(original, revised, source, position)
        if position > literal:
            data.extend(b"\1" + struct.pack("<I", position - literal) + revised[literal:position])
        data.extend(b"\0" + struct.pack("<II", source, size))
        copied += size
        position += size
        literal = position
    if literal < len(revised):
        data.extend(b"\1" + struct.pack("<I", len(revised) - literal) + revised[literal:])
    return zlib.compress(data, 9), copied
