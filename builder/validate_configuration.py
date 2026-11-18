"""Check configurable native payloads against the owned pristine input records."""
import gzip
import json
import math
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from configuration import (DEFAULT, DIFFICULTY, DIFFICULTY_EFFECT, ECONOMY, EFFECTS, MODIFIERS, NATIVE_LEVELS,
                           PRESETS, SCENARIOS, TECHNOLOGIES,
                           configure_entry, difficulty_categories, resolve, starting_profiles)


def verify_rates(original, selected, configured, rate, recipe_ids):
    def records(data):
        tokens = list(DIFFICULTY_EFFECT.finditer(data,5))
        assert len(tokens)==struct.unpack_from("<I",data,1)[0]
        return [(match[1],data[match.end():tokens[i+1].start() if i+1<len(tokens) else len(data)])
                for i,match in enumerate(tokens)]

    before,after = records(selected),records(configured)
    neutral = not before
    if neutral:
        before = [(kind,raw) for kind,raw in records(original) if kind!=b"HuntSending"]
    assert len(after)==len(before)+len(recipe_ids)
    for (kind,raw),(actual,revised) in zip(before,after):
        assert kind==actual
        if kind==b"ProductionBlueprint":
            assert revised[:56]==raw[:56] and revised[60:68]==raw[60:68]
            assert struct.unpack_from("<f",revised,56)[0]==(1 if neutral else struct.unpack_from("<f",raw,56)[0])
            expected = (1 if neutral else struct.unpack_from("<f",raw,68)[0])/rate
            assert math.isclose(struct.unpack_from("<f",revised,68)[0],expected,rel_tol=1e-6)
        elif kind in (b"ExtractionBlueprint",b"ResourceGathering"):
            offsets = [60] if kind==b"ExtractionBlueprint" else list(range(80,len(raw),28))
            neutralized = bytearray(revised)
            for offset in offsets:
                expected = (1 if neutral else struct.unpack_from("<f",raw,offset)[0])*rate
                assert math.isclose(struct.unpack_from("<f",revised,offset)[0],expected,rel_tol=1e-6)
                neutralized[offset:offset+4]=raw[offset:offset+4]
            assert neutralized==raw
        else:
            assert revised==raw
    for (kind,raw),uid in zip(after[len(before):],recipe_ids):
        assert kind==b"ProductionBlueprint" and raw[36:52].hex()==uid
        assert raw[52:]==struct.pack("<IfIIf",0,1,0,0,1/rate)


def main():
    manifest = json.loads((ROOT / "build/native/manifest.json").read_text())
    metadata = manifest["configuration"]
    source = ROOT / "builder/cache/extracted/common"
    original = {name: (source / name).read_bytes() for name in (SCENARIOS, DIFFICULTY, TECHNOLOGIES,MODIFIERS,EFFECTS)}
    revised = {e["name"]: gzip.decompress((ROOT / "build/native/payload" / e["payload"]).read_bytes())
               for e in manifest["archives"]["common"]["entries"] if e["name"] in original}
    profiles = starting_profiles(original[SCENARIOS])
    baseline_profiles = starting_profiles(revised[SCENARIOS])
    categories = difficulty_categories(original[DIFFICULTY])
    assert revised[DIFFICULTY] == original[DIFFICULTY]
    for preset in PRESETS:
        settings = resolve(DEFAULT | {"preset": preset})
        output = {name: configure_entry(name, original[name], revised[name], metadata, settings) for name in original}
        rows = starting_profiles(output[SCENARIOS])
        assert len(rows) == 17
        assert revised[SCENARIOS][:baseline_profiles[0]["start"]] == output[SCENARIOS][:rows[0]["start"]]
        assert revised[SCENARIOS][baseline_profiles[-1]["end"]:] == output[SCENARIOS][rows[-1]["end"]:]
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
                rate = settings["production_rate_multiplier"]
                if before["name"] in ECONOMY and rate!=1:
                    recipes = metadata["production_recipes"] if before["name"]=="Economy_Others" else ()
                    verify_rates(before["records"][0]["body"],selected["body"],new["body"],rate,recipes)
                else:
                    assert new["body"][1:] == selected["body"][1:]
        technology=output[TECHNOLOGIES]
        for offset, authored in metadata["research_durations"]:
            assert technology[offset:offset+4]==struct.pack("<f",authored*settings["perk_research_duration_multiplier"])
        curve=metadata["workshop_curve_offset"]+4
        assert technology[curve:curve+32]==b"".join(
            struct.pack("<ff",i,rate*settings["workshop_output_multiplier"])
            for i,rate in enumerate((1,1.3,1.5,1.6),1))
        for name,rules in metadata["balance_fields"].items():
            restored = bytearray(output[name])
            for offset,code,group,neutral,low,high in rules:
                old = struct.unpack_from("<"+code,revised[name],offset)[0]
                gain = (old-neutral)*settings[group+"_power_multiplier"]+neutral
                if code=="i":
                    gain=int(gain+0.5)
                assert restored[offset:offset+4]==struct.pack("<"+code,min(high,max(low,gain)))
                restored[offset:offset+4]=revised[name][offset:offset+4]
            assert bytes(restored)==revised[name], (preset,name)
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
    settings=resolve(DEFAULT | {"production_rate_multiplier":1.2})
    custom=difficulty_categories(configure_entry(DIFFICULTY,original[DIFFICULTY],revised[DIFFICULTY],metadata,settings))
    for before,after in zip(categories,custom):
        if before["name"] in ECONOMY:
            recipes=metadata["production_recipes"] if before["name"]=="Economy_Others" else ()
            verify_rates(before["records"][0]["body"],before["records"][1]["body"],after["records"][1]["body"],1.2,recipes)
    from validate_tooltips import language_table
    settings=resolve(DEFAULT | {"preset":"easiest"})
    for entry in manifest["archives"]["localizations"]["entries"]:
        data=gzip.decompress((ROOT/"build/native/payload"/entry["payload"]).read_bytes())
        before=language_table(data)
        after=language_table(configure_entry(entry["name"],data,data,metadata,settings))
        assert before.keys()==after.keys()
        changed={key.encode():group for group,keys in metadata["balance_text"].items() for key in keys}
        assert changed.keys()<=after.keys()
        for key,value in after.items():
            if key in changed:
                factor=settings[changed[key]+"_power_multiplier"]
                assert value.startswith(before[key]) and f"×{factor:g}" in value[len(before[key]):].decode("utf-16-le")
            else:
                assert value==before[key]
        assert configure_entry(entry["name"],data,data,metadata,resolve(DEFAULT))==data
    print("Verified five presets and custom overrides across supplies, native difficulty, production, research, modifiers and law effects. Checked all 13 language tables. Standard reconstructs the baseline byte for byte.")


if __name__ == "__main__":
    main()
