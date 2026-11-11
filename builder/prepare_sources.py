"""Extract only the build inputs from a verified, owned copy of Frostpunk."""
import argparse
import json
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT / "tools"))
import archive
from installer import Installer


def analyze_technologies(data):
    starts = [match.start() for match in re.finditer(b"\1FrostpunkTechnologyEntry\0", data)]
    rows = []
    for index, start in enumerate(starts):
        position = start + len(b"\1FrostpunkTechnologyEntry\0")
        assert data[position] == 1
        name_end = data.index(0, position + 1)
        name = data[position + 1:name_end].decode()
        guid = data[name_end + 1:name_end + 17]
        limit = starts[index + 1] if index + 1 < len(starts) else len(data)
        display = re.search(rb"\x01@[^\x00]+\x00", data[name_end + 17:limit])
        assert display is not None
        tail = name_end + 17 + display.start()
        for _ in range(3):
            flag = data[tail]
            tail += 1
            assert flag in (0, 1)
            if flag:
                tail = data.index(0, tail) + 1
        layout = struct.unpack_from("<4i", data, tail)
        category = data[tail + 16:tail + 32]
        cost_count, = struct.unpack_from("<I", data, tail + 32)
        duration = tail + 36 + cost_count * 20
        hours, = struct.unpack_from("<f", data, duration)
        end = starts[index + 1] if index + 1 < len(starts) else duration + 4 + 41
        rows.append(dict(name=name, guid=guid.hex(), start=start, tail=tail, layout=layout,
                         category=category.hex(), costcount=cost_count, hours=hours, rest=data[duration + 4:end].hex()))
    assert len(rows) == 176
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", required=True, type=Path)
    args = parser.parse_args()
    archive.GAME = args.game.resolve()
    manifest = json.loads((ROOT.parent / "mod/manifest.json").read_text())
    Installer(archive.GAME, ROOT / "cache", manifest).verify(archive.GAME, {
        base + extension: digest for base, entry in manifest["archives"].items() for extension, digest in entry["original_files"].items()
    })
    for group in manifest["archives"]:
        with (archive.GAME / (group + ".dat")).open("rb") as stream:
            for entry in archive.entries(group):
                name = archive.NAMES.get(entry[1])
                if name is None or (group == "common" and not name.startswith("configs/")):
                    continue
                path = ROOT / "cache/extracted" / group / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.read(stream, entry))
    technologies = (ROOT / "cache/extracted/common/configs/frostpunktechnologiesconfig.bin").read_bytes()
    (ROOT / "cache/tech.json").write_text(json.dumps(analyze_technologies(technologies), indent=2) + "\n")
    (ROOT / "cache/source.json").write_text(json.dumps({"game": str(archive.GAME)}, indent=2) + "\n")
    print("Prepared local build inputs and native technology metadata.")


if __name__ == "__main__":
    main()
