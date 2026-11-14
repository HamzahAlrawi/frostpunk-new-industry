"""Check configurable native payloads against the owned pristine input records."""
import gzip
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from configuration import (DEFAULT, DIFFICULTY, NATIVE_LEVELS, PRESETS, SCENARIOS, TECHNOLOGIES,
                           configure_entry, difficulty_categories, resolve, starting_profiles)


def main():
    manifest = json.loads((ROOT / "build/native/manifest.json").read_text())
    metadata = manifest["configuration"]
    source = ROOT / "builder/cache/extracted/common"
    original = {name: (source / name).read_bytes() for name in (SCENARIOS, DIFFICULTY, TECHNOLOGIES)}
    revised = {e["name"]: gzip.decompress((ROOT / "build/native/payload" / e["payload"]).read_bytes())
               for e in manifest["archives"]["common"]["entries"] if e["name"] in original}
    profiles = starting_profiles(original[SCENARIOS])
    categories = difficulty_categories(original[DIFFICULTY])
    assert revised[DIFFICULTY] == original[DIFFICULTY]
    for preset in PRESETS:
        settings = resolve(DEFAULT | {"preset": preset})
        output = {name: configure_entry(name, original[name], revised[name], metadata, settings) for name in original}
        rows = starting_profiles(output[SCENARIOS])
        assert len(rows) == 17
        assert original[SCENARIOS][:profiles[0]["start"]] == output[SCENARIOS][:rows[0]["start"]]
        assert original[SCENARIOS][profiles[-1]["end"]:] == output[SCENARIOS][rows[-1]["end"]:]
        extras = {bytes.fromhex(metadata["resource_ids"][name]): amount
                  for name, amount in settings["starting_resources_bonus"].items()}
        for before, after in zip(profiles, rows):
            assert before["name"] == after["name"]
            assert original[SCENARIOS][before["start"]:before["header_end"]] == output[SCENARIOS][after["start"]:after["header_end"]]
            assert original[SCENARIOS][before["vector_end"]:before["end"]] == output[SCENARIOS][after["vector_end"]:after["end"]]
            old = dict(before["items"])
            expected = {guid: amount + extras.get(guid, 0) for guid, amount in old.items()}
            expected.update({guid: amount for guid, amount in extras.items() if guid not in old})
            assert dict(after["items"]) == expected, (preset, before["name"])
        for before, after in zip(categories, difficulty_categories(output[DIFFICULTY])):
            assert before["header"] == after["header"] and before["footer"] == after["footer"]
            native = settings["native_difficulty"]
            for old, new in zip(before["records"], after["records"]):
                selected = old if native == "menu" else before["records"][list(NATIVE_LEVELS.values()).index(NATIVE_LEVELS[native])]
                assert old["header"] == new["header"] and old["body"][:1] == new["body"][:1]
                assert new["body"][1:] == selected["body"][1:]
        if preset == "standard":
            assert all(output[name] == revised[name] for name in original), "Default config must match published patch hashes"
    # Probe custom pacing at the serialized offsets, preserving every other byte.
    settings = resolve(DEFAULT | {"workshop_output_multiplier": 2, "perk_research_duration_multiplier": 0.25})
    changed = configure_entry(TECHNOLOGIES, original[TECHNOLOGIES], revised[TECHNOLOGIES], metadata, settings)
    restored = bytearray(changed)
    for offset, authored in metadata["research_durations"]:
        assert struct.unpack_from("<f", changed, offset)[0] == authored * 0.25
        restored[offset:offset + 4] = revised[TECHNOLOGIES][offset:offset + 4]
    offset = metadata["workshop_curve_offset"]
    assert struct.unpack_from("<I8f", changed, offset) == struct.unpack("<I8f", struct.pack("<I8f", 4, 1, 2, 2, 2.6, 3, 3, 4, 3.2))
    restored[offset:offset + 36] = revised[TECHNOLOGIES][offset:offset + 36]
    assert bytes(restored) == revised[TECHNOLOGIES], "Custom pacing modified unrelated bytes"
    print(f"Verified all five presets: all 17 supply profiles, 13 native difficulty categories / 52 level records, {len(metadata['research_durations'])} research offsets, unchanged scenario tails and baseline hashes.")


if __name__ == "__main__":
    main()
