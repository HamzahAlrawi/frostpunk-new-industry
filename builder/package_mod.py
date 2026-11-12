"""Convert a native local build to the public patch distribution."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT / "tools"))
import archive
from make_delta import make_delta
from patch_format import apply_patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, default=ROOT.parent / "build/native")
    parser.add_argument("--originals", type=Path, required=True)
    args = parser.parse_args()
    source = json.loads((args.native / "manifest.json").read_text())
    archive.GAME = args.originals.resolve()
    output = ROOT.parent / "mod"
    patches = output / "patches"
    patches.mkdir(parents=True, exist_ok=True)
    manifest = {"name": "Frostpunk New Industry", "version": source["version"], "format": "nind-copy-insert-v1",
                "game": "Frostpunk", "supported_build": "Windows Steam 1.6.2, exact original archive hashes required", "archives": {}}
    for group, settings in source["archives"].items():
        entries = {entry[1]: entry for entry in archive.entries(group)}
        exported = []
        with (archive.GAME / (group + ".dat")).open("rb") as stream:
            for entry in settings["entries"]:
                original = archive.read(stream, entries[entry["hash"]])
                revised = gzip.decompress((args.native / "payload" / entry["payload"]).read_bytes())
                if hashlib.sha256(original).hexdigest() != entry["original_sha256"]:
                    raise ValueError("Build original does not match the supplied game files")
                delta, _ = make_delta(original, revised)
                if apply_patch(original, delta) != revised:
                    raise ValueError("Delta reconstruction failed")
                name = f"{group}-{entry['hash']:08x}.nid"
                (patches / name).write_bytes(delta)
                exported.append({key: value for key, value in entry.items() if key != "payload"} |
                                {"patch": name, "patch_sha256": hashlib.sha256(delta).hexdigest()})
        manifest["archives"][group] = {"original_files": settings["original_files"], "entries": exported}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    active = {guid for values in source["scenario_additions"].values() for guid in values}
    catalog = {key: source[key] for key in ("name", "version", "technology_sets", "scenario_additions", "technologies", "recipes",
                                           "retired_technologies", "opening_stock_bonus", "base_research_multiplier",
                                           "removed_team_perks", "redesigned_technologies", "research_tabs")}
    catalog["active_research_definitions"] = len(active)
    catalog["suspended_technologies"] = [entry["id"] for entry in source["suspended_field_operations"]]
    (output / "catalog.json").write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    print(f"Packaged {source['version']} as copy/insert patches.")


if __name__ == "__main__":
    main()
