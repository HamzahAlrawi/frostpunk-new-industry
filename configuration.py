"""Validated installer settings and bounded edits of native configuration vectors."""
import hashlib
import json
import math
import re
import struct


RESOURCES = ("Wood", "Steel", "Coal", "Raw Food", "Food Rations", "Steam Cores")
CATEGORIES = (
    "Health", "Nutrition", "Economy_Coal", "Economy_Others", "Technology",
    "Economy_Food", "Economy_StartingResources", "Hope", "Weather", "Discontent",
    "Frostland_Resources", "Generator", "Telegraph Station",
)
LEVELS = ("Easy", "Medium", "Hard", "Frostbite")
NATIVE_LEVELS = {"easy": "Easy", "medium": "Medium", "hard": "Hard", "extreme": "Frostbite"}
PRESETS = {
    "easiest": ("easy", (200, 150, 400, 150, 100, 5)),
    "easy": ("easy", (150, 100, 300, 100, 75, 3)),
    "standard": ("menu", (100, 75, 200, 80, 50, 2)),
    "hard": ("hard", (80, 50, 150, 60, 30, 1)),
    "extreme": ("extreme", (60, 40, 100, 45, 20, 1)),
}
BALANCE_KEYS = ("perk_research_duration_multiplier", "workshop_output_multiplier",
                "production_rate_multiplier", "upgrade_power_multiplier", "law_power_multiplier")
PRESET_BALANCE = {
    "easiest": (0.35, 1.85, 1.15, 1.25, 1.30),
    "easy": (0.425, 1.70, 1.075, 1.125, 1.15),
    "standard": (0.50, 1.5625, 1.00, 1.00, 1.00),
    "hard": (0.65, 1.30, 0.90, 0.80, 0.75),
    "extreme": (0.80, 1.10, 0.80, 0.65, 0.55),
}
BALANCE_LIMITS = ((0.1, 4), (0.25, 5), (0.6, 1.5), (0.5, 1.5), (0.5, 1.5))
SCENARIOS = "configs/frostpunkscenariosconfig.bin"
DIFFICULTY = "configs/frostpunkdifficultyconfig.bin"
TECHNOLOGIES = "configs/frostpunktechnologiesconfig.bin"
MODIFIERS = "configs/frostpunkmodifiersconfig.bin"
EFFECTS = "configs/frostpunkeffectsconfig.bin"
ECONOMY = ("Economy_Coal", "Economy_Others", "Economy_Food")
DIFFICULTY_EFFECT = re.compile(rb"\x01Frostpunk([A-Za-z]+)DifficultyModification\0")
DEFAULT = {"schema_version": 1, "preset": "standard"}
PROFILE_ANCHOR = b"\1\1Default\0" + bytes.fromhex("abffde98fc17e8921d495b49e5928974")


def resolve(document):
    if not isinstance(document, dict):
        raise ValueError("Configuration must be a JSON object")
    allowed = {"schema_version", "preset", "native_difficulty", "difficulty_categories",
               "starting_resources_bonus", *BALANCE_KEYS}
    if document.keys() - allowed:
        raise ValueError(f"Unknown configuration keys: {sorted(document.keys() - allowed)}")
    if type(document.get("schema_version")) is not int or document["schema_version"] != 1:
        raise ValueError("Configuration schema_version must be 1")
    preset = document.get("preset", "standard")
    if not isinstance(preset, str) or preset not in PRESETS:
        raise ValueError(f"preset must be one of: {', '.join(PRESETS)}")
    native, stock = PRESETS[preset]
    native = document.get("native_difficulty", native)
    if not isinstance(native, str) or native not in ("menu", *NATIVE_LEVELS):
        raise ValueError("native_difficulty must be menu, easy, medium, hard, or extreme")
    categories = document.get("difficulty_categories", {})
    if not isinstance(categories, dict) or categories.keys() - set(CATEGORIES):
        raise ValueError("Unknown difficulty category; see docs/configuration.md")
    if any(not isinstance(v, str) or v not in ("menu", *NATIVE_LEVELS) for v in categories.values()):
        raise ValueError("Each difficulty category must be menu, easy, medium, hard, or extreme")
    overrides = document.get("starting_resources_bonus", {})
    if not isinstance(overrides, dict) or overrides.keys() - set(RESOURCES):
        raise ValueError(f"starting_resources_bonus accepts: {', '.join(RESOURCES)}")
    if any(type(v) is not int or not 0 <= v <= 50000 for v in overrides.values()):
        raise ValueError("Starting resource bonuses must be integers from 0 to 50000")
    settings = dict(preset=preset, native_difficulty=native, difficulty_categories=dict(categories),
                    starting_resources_bonus=dict(zip(RESOURCES, stock)) | overrides)
    for key, default, (lower, upper) in zip(BALANCE_KEYS, PRESET_BALANCE[preset], BALANCE_LIMITS):
        value = document.get(key, default)
        if type(value) not in (int, float) or not math.isfinite(value) or not lower <= value <= upper:
            raise ValueError(f"{key} must be a finite number from {lower} to {upper}")
        settings[key] = float(value)
    return settings


def fingerprint(settings):
    return hashlib.sha256(json.dumps(settings, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def starting_profiles(data):
    """Return exact profile spans without interpreting any later scenario vectors."""
    pos = data.index(PROFILE_ANCHOR)
    count, = struct.unpack_from("<I", data, pos - 4)
    if count != 17:
        raise ValueError("Unsupported starting-resource profile table")
    rows = []
    for _ in range(count):
        start = pos
        if data[pos:pos + 2] != b"\1\1":
            raise ValueError("Invalid starting profile header")
        end = data.index(0, pos + 2)
        name = data[pos + 2:end].decode("ascii")
        pos = end + 17
        header_end = pos
        size, = struct.unpack_from("<I", data, pos)
        pos += 4
        items = [(data[p:p + 16], struct.unpack_from("<I", data, p + 16)[0])
                 for p in range(pos, pos + size * 20, 20)]
        pos += size * 20
        vector_end = pos
        for _ in range(2):
            if data[pos] not in (0, 1):
                raise ValueError("Invalid optional profile string")
            pos = data.index(0, pos + 1) + 1 if data[pos] else pos + 1
        rows.append(dict(name=name, start=start, header_end=header_end,
                         vector_end=vector_end, end=pos, items=items))
    return rows


def starting_supplies(data, resource_ids, bonuses, base_data=None):
    rows = starting_profiles(data)
    baseline = starting_profiles(base_data) if base_data is not None else rows
    if [row['name'] for row in rows] != [row['name'] for row in baseline]:
        raise ValueError('Starting-profile identities differ from the native baseline')
    extras = {bytes.fromhex(resource_ids[name]): amount for name, amount in bonuses.items() if amount}
    chunks = [data[:rows[0]["start"]]]
    for row, base in zip(rows, baseline):
        items = base["items"]
        if len(dict(items)) != len(items):
            raise ValueError("Duplicate resource in starting profile")
        revised = [(guid, value + extras.get(guid, 0)) for guid, value in items]
        revised += [(guid, amount) for guid, amount in extras.items() if guid not in dict(items)]
        chunks += [data[row["start"]:row["header_end"]], struct.pack("<I", len(revised)),
                   b"".join(guid + struct.pack("<I", value) for guid, value in revised),
                   data[row["vector_end"]:row["end"]]]
    return b"".join(chunks) + data[rows[-1]["end"]:]


def difficulty_categories(data):
    count, = struct.unpack_from("<I", data)
    markers = list(re.finditer(rb"\x01\x01([ -~]+)\0(.{16})\x04\x00\x00\x00", data, re.S))
    if count != 13 or len(markers) != count or markers[0].start() != 4:
        raise ValueError("Unsupported native difficulty category table")
    result = []
    for i, marker in enumerate(markers):
        name = marker[1].decode("ascii")
        limit = markers[i + 1].start() if i + 1 < count else len(data)
        footer = b"\1" + name.encode() + b"\0" if i + 1 < count else b"\0"
        if not data[marker.end():limit].endswith(footer):
            raise ValueError("Invalid native difficulty category footer")
        levels = list(re.finditer(rb"\x01\x01(Easy|Medium|Hard|Frostbite)\0(.{16})", data[marker.end():limit], re.S))
        if [m[1].decode() for m in levels] != list(LEVELS) or levels[0].start() != 0:
            raise ValueError("Invalid native difficulty levels")
        records = []
        for j, level in enumerate(levels):
            start = marker.end() + level.start()
            body_start = marker.end() + level.end()
            end = marker.end() + levels[j + 1].start() if j < 3 else limit - len(footer)
            body = data[body_start:end]
            if len(body) < 5 or body[0] not in (0, 1):
                raise ValueError("Invalid native difficulty effect vector")
            records.append(dict(level=LEVELS[j], header=data[start:body_start], body=body))
        result.append(dict(name=name, header=data[marker.start():marker.end()], records=records, footer=footer))
    if tuple(c["name"] for c in result) != CATEGORIES:
        raise ValueError("Unknown native difficulty categories")
    return result


def economy_rates(body, donor, rate, recipes):
    """Scale native gathering/extraction speed and production-cycle duration."""
    # Medium carries an empty vector. Its target list is taken from Easy but
    # every scalar on that list starts at the neutral rate.
    neutral = body == bytes(4)
    selected = donor if neutral else body
    matches = list(DIFFICULTY_EFFECT.finditer(selected, 4))
    if len(matches) != struct.unpack_from("<I", selected)[0] or matches[0].start() != 4:
        raise ValueError("Unsupported native economy effect vector")
    records = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(selected)
        payload = bytearray(selected[match.end():end])
        kind = match[1]
        if payload[:36] != bytes(36):
            raise ValueError("Unsupported native economy effect condition")
        if kind == b"ExtractionBlueprint" and len(payload) == 64:
            offsets = (60,)
        elif kind == b"ResourceGathering" and len(payload) in (84,112):
            count = struct.unpack_from("<I", payload, 52)[0]
            if count not in (1,2) or len(payload) != 56 + count * 28:
                raise ValueError("Invalid gathering resource vector")
            offsets = range(80, len(payload), 28)
        elif kind == b"ProductionBlueprint" and len(payload) == 72:
            if any(payload[j:j+4] != bytes(4) for j in (52,60,64)):
                raise ValueError("Unsupported production difficulty flags")
            if neutral:
                struct.pack_into("<f", payload, 56, 1.0)
            length = 1.0 if neutral else struct.unpack_from("<f", payload, 68)[0]
            struct.pack_into("<f", payload, 68, length / rate)
            offsets = ()
        elif kind == b"HuntSending" and len(payload) == 60:
            if neutral:
                continue
            offsets = ()
        else:
            raise ValueError("Unsupported economy rate record")
        for offset in offsets:
            if struct.unpack_from("<II", payload, offset - 8) != (0,2):
                raise ValueError("Expected a multiplicative gathering or extraction rate")
            base = 1.0 if neutral else struct.unpack_from("<f", payload, offset)[0]
            struct.pack_into("<f", payload, offset, base * rate)
        records.append(match[0] + payload)
    production = b"\1FrostpunkProductionBlueprintDifficultyModification\0" + bytes(36)
    for uid in recipes:
        target = bytes.fromhex(uid)
        if len(target) != 16:
            raise ValueError("Invalid mod recipe ID")
        records.append(production + target + struct.pack("<IfIIf",0,1.0,0,0,1 / rate))
    return struct.pack("<I", len(records)) + b"".join(records)


def difficulty_settings(data, settings, recipes=()):
    chunks = [data[:4]]
    for category in difficulty_categories(data):
        selected = settings["difficulty_categories"].get(category["name"], settings["native_difficulty"])
        bodies = {r["level"]: r["body"] for r in category["records"]}
        chunks.append(category["header"])
        for record in category["records"]:
            # Keep every native name, object GUID, and default-selection flag.
            # Only the counted vector of native effect objects is substituted.
            effects = record["body"][1:] if selected == "menu" else bodies[NATIVE_LEVELS[selected]][1:]
            rate = settings.get("production_rate_multiplier", 1.0)
            if rate != 1 and category["name"] in ECONOMY:
                additions = recipes if category["name"] == "Economy_Others" else ()
                effects = economy_rates(effects, bodies["Easy"][1:], rate, additions)
            chunks.append(record["header"] + record["body"][:1] + effects)
        chunks.append(category["footer"])
    return b"".join(chunks)


def scaled_values(data, rules, settings):
    """Apply each factor to the distance from the authored neutral value."""
    output = bytearray(data)
    for offset, code, group, neutral, lower, upper in rules:
        if not 0 <= offset <= len(output) - 4 or code not in ("f", "i"):
            raise ValueError("Invalid balance field")
        factor = settings[group + "_power_multiplier"]
        if factor == 1:
            continue
        before = struct.unpack_from("<" + code, data, offset)[0]
        value = neutral + (before - neutral) * factor
        if code == "i":
            value = math.floor(value + 0.5)
        struct.pack_into("<" + code, output, offset, max(lower, min(upper, value)))
    return bytes(output)


def balance_labels(data, keys, settings):
    groups = {group:settings[group + "_power_multiplier"] for group in keys}
    suffixes = {
        key.encode(): f"\n\nStandard values shown. This preset applies ×{groups[group]:g} to scalable {group} bonuses."
                      .encode("utf-16-le")
        for group, names in keys.items() if groups[group] != 1 for key in names
    }
    if not suffixes:
        return data
    result = [data[4:8]]
    position = 8
    for _ in range(struct.unpack_from("<I", data, 4)[0]):
        size = struct.unpack_from("<H", data, position)[0]
        middle = position + 2 + size
        key = data[position + 2:middle]
        length = struct.unpack_from("<H", data, middle)[0] * 2
        end = middle + 2 + length
        if key in suffixes:
            value = data[middle + 2:end] + suffixes[key]
            result += [data[position:middle], struct.pack("<H", len(value)//2), value]
        else:
            result.append(data[position:end])
        position = end
    if position != len(data):
        raise ValueError("Invalid localization table")
    packed = b"".join(result)
    return struct.pack("<I", len(packed)) + packed


def configure_entry(name, original, revised, metadata, settings):
    if name == SCENARIOS:
        return starting_supplies(revised, metadata["resource_ids"], settings["starting_resources_bonus"], original)
    if name == DIFFICULTY:
        return difficulty_settings(original, settings, metadata.get("production_recipes", ()))
    if name == MODIFIERS or name == EFFECTS:
        return scaled_values(revised, metadata.get("balance_fields", {}).get(name, ()), settings)
    if name.endswith(".lang"):
        return balance_labels(revised, metadata.get("balance_text", {}), settings)
    if name == TECHNOLOGIES:
        output = bytearray(revised)
        for offset, authored in metadata["research_durations"]:
            if offset < 0 or offset + 4 > len(output):
                raise ValueError("Research duration offset outside configuration")
            struct.pack_into("<f", output, offset, authored * settings["perk_research_duration_multiplier"])
        offset = metadata["workshop_curve_offset"]
        if struct.unpack_from("<I", output, offset)[0] != 4:
            raise ValueError("Invalid Workshop scaling vector")
        for i, rate in enumerate((1, 1.3, 1.5, 1.6)):
            struct.pack_into("<ff", output, offset + 4 + i * 8, i + 1, rate * settings["workshop_output_multiplier"])
        return bytes(output)
    return revised
