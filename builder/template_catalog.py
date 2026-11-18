"""The native GUID-to-prefab directory in templates.dat."""
from collections import defaultdict
from pathlib import PurePosixPath

from tools.native_binary import Cursor, SchemaError, Span, replace_spans, u32


CATALOG_KEY = 0xfdf27723
CATALOG_ASSET = "templateinfo.bin"
MAGIC = bytes.fromhex("ef ee de c0")


def guid_order(uid):
    return int.from_bytes(uid, "little")


def read_catalog(data):
    """Return GUID records and the file tree with its editable folder vectors."""
    c = Cursor(data)
    if c.take(4) != MAGIC:
        raise SchemaError("Unsupported native template catalog")
    count = c.count()
    templates = {}
    for _ in range(count):
        end = data.index(b"\0", c.position)
        name = c.take(end + 1 - c.position)[:-1].decode()
        uid = c.take(16)
        templates[uid] = (name, c.take(4))
    if len(templates) != count or list(templates) != sorted(templates, key=guid_order):
        raise SchemaError("Template GUID catalog must be sorted and unique")

    tree_start = c.position
    folders = {}
    paths = {}

    def visit(parent):
        label = c.take(c.count(256))
        if not label.endswith(b"\0") or b"\0" in label[:-1] or b"/" in label:
            raise SchemaError("Unsupported template catalog folder name")
        folder = parent / label[:-1].decode().lower()
        if folder in folders:
            raise SchemaError(f"Duplicate template folder {folder}")
        start = c.position
        members = [c.take(16) for _ in range(c.count(1000))]
        folders[folder] = (Span(start, c.position), members)
        for uid in members:
            if uid in paths or uid not in templates:
                raise SchemaError(f"Missing or duplicate template GUID {uid.hex()}")
            paths[uid] = folder / (templates[uid][0].lower() + ".binarytemplate")
        for _ in range(c.count(256)):
            visit(folder)

    visit(PurePosixPath())
    if c.position != len(data) or paths.keys() != templates.keys() or len(set(paths.values())) != count:
        raise SchemaError("Template folder tree does not resolve every GUID uniquely")
    return tree_start, templates, folders, paths


def register_buildings(native, buildings, payloads):
    tree_start, templates, folders, paths = read_catalog(native)
    stock_guids = {path: uid for uid, path in paths.items()}
    new_members = defaultdict(list)
    for building in buildings:
        uid = bytes.fromhex(building["guid"])
        path = PurePosixPath("templates") / building["path"]
        donor = PurePosixPath("templates") / building["donor"]
        if uid in templates or path in stock_guids or path.parent not in folders:
            raise SchemaError(f"Conflicting template registration for {path}")
        _, flags = templates[stock_guids[donor]]
        if not payloads[building["path"]][1].startswith(uid + flags):
            raise SchemaError(f"Template header differs from catalog record for {path}")
        templates[uid] = (path.stem, flags)
        stock_guids[path] = uid
        new_members[path.parent].append(uid)

    # The first table is GUID-sorted. The tree also needs the GUID in its
    # folder so the engine can turn the record's basename into an archive key.
    records = b"".join(name.encode() + b"\0" + uid + flags
                       for uid, (name, flags) in sorted(templates.items(), key=lambda row: guid_order(row[0])))
    patches = [(Span(4, tree_start), u32(len(templates)) + records)]
    for folder, added in new_members.items():
        span, members = folders[folder]
        patches.append((span, u32(len(members) + len(added)) + b"".join(members + added)))
    return replace_spans(native, patches)
