"""Native place upgrades for the New Industry archive builder."""
from automaton_efficiency import ROLE_WORKPLACE_BONUSES, raise_workplace_research, split_workplace_efficiency

def make_upgrades(add_tech, techinfo, mod_data, buildings, guid, loc, pack32):
    import re
    import struct

    tech = {row["name"]: row for row in techinfo}
    records = list(re.finditer(rb"\x01Frostpunk[A-Za-z]+Modifier\x00", mod_data))
    place_class = b"\x01FrostpunkPlaceModifier\x00"
    by_guid = {
        mod_data[record.end():record.end()+16]: (record, records[i+1].start())
        for i, record in enumerate(records[:-1]) if record.group() == place_class
    }
    upgrades = []
    all_bindings = []
    prices = {
        "GatheringSort": (25, 8, 6),
        "GatheringLogistics": (65, 35, 12),
        "SawmillOutput2": (45, 25, 10),
        "CoalMineOutput3": (95, 55, 16),
        "MedicalEfficiency2": (35, 15, 8),
        "FieldDressings": (12, 4, 4),
        "WardProtocols": (75, 40, 13),
        "CropRotation": (25, 8, 6),
        "SeedSelection2": (80, 45, 14),
        "HubReturnLines": (100, 65, 18),
    }

    def places(names):
        ids = []
        for name in names:
            marker = b"\x01" + name.encode() + b"\0"
            assert buildings.count(marker) == 1, name
            pos = buildings.index(marker) + len(marker)
            category = "9a9fdded110faa98de4746580f6e204c" if name == "Engineers Lab" else "6e48307d0c1898b8914b3d1bfd67c30f"
            assert buildings[pos:pos+16].hex() == category, name
            ids.append(buildings[pos+16:pos+32])
        return ids

    added_tech = {}

    def add(key, title, desc, stage, col, parent, source, targets=None, *, output=None, replace_value=None):
        row = tech[source]
        tail = bytes.fromhex(row["rest"])
        assert tail[:8] == struct.pack("<2I", 2, 0)
        count = struct.unpack_from("<I", tail, 8)[0]
        assert 1 <= count <= 5 and len(tail) == 41 + count * 32
        pairs = [(tail[p:p+16], tail[p+16:p+32]) for p in range(12, 12+32*count, 32)]
        if targets:
            pairs = [(place, pairs[0][1]) for place in places(targets)]
        mapping = {}
        descriptions = set()
        for _, source_id in pairs:
            if source_id in mapping:
                continue
            record, end = by_guid[source_id]
            body = mod_data[record.end()+16:end]
            assert body[0] == 1
            name_end = body.index(0, 1)
            old_name = body[1:name_end]
            original_tail = body[name_end+1:]
            replacement = original_tail
            if output is not None:
                assert source == "R 2_Sawmill Upgrade"
                # Sawmill's vanilla 1.25 output multiplier is the only 1.25 in this record.
                previous = struct.pack("<f", 1.25)
                assert original_tail.count(previous) == 1
                replacement = original_tail.replace(previous, struct.pack("<f", output))
            if replace_value is not None:
                kind, before, after = replace_value
                old_value = struct.pack("<"+kind, before)
                assert replacement.count(old_value) == 1, (key, old_name, before)
                replacement = replacement.replace(old_value, struct.pack("<"+kind, after))
            if key in ROLE_WORKPLACE_BONUSES:
                replacement = split_workplace_efficiency(replacement)
            replacement, description = raise_workplace_research(replacement, desc)
            descriptions.add(description)
            token = rb"\x01@Generated/ModifiersConfig/Modifiers/[^\x00]+/Display name\x00"
            replacement = re.sub(token, lambda _: loc("Modifier/"+key, title), replacement)
            new_id = guid("place/" + key + "/" + source_id.hex())
            mapping[source_id] = new_id
            upgrades.append(place_class + new_id + b"\x01NI " + key.encode() + b"/" + old_name + b"\0" + replacement)
        bindings = [(place, mapping[source_id]) for place, source_id in pairs]
        all_bindings.extend(bindings)
        rest = tail[:8] + pack32(len(bindings)) + b"".join(place+effect for place,effect in bindings) + tail[12+32*count:]
        require = []
        if parent:
            require.append(added_tech[parent] if parent in added_tech else bytes.fromhex(tech[parent]["guid"]))
        category = bytes.fromhex(row["category"])
        if key in {"WorkshopHeat", "IndustrialHeat", "DrillHeat", "KilnHeat", "MedicalHeat4", "HothouseHeat4"}:
            category = bytes.fromhex("3be2ab21909e45aee64283f2019439d3")
        wood, steel, hours = prices.get(key, ([20,35,55,75,105,140][stage],
                                             [8,15,30,45,70,100][stage], [6,8,12,16,20,24][stage]))
        description, = descriptions
        added_tech[key] = add_tech(key, title, description, stage, col, require, {"Wood":wood,"Steel":steel}, hours,
                                  tuple(row["layout"][:2]), category, rest=rest, effects=bindings)

    gathering_heat = "R 3_Gathering Insulation"
    saw_output = "R 2_Sawmill Upgrade"
    add("GatheringWorkwear", "Insulated Gathering Gear", "Gathering Posts gain +1 heat level.", 0, 4, None, gathering_heat)
    add("GatheringSort", "Gathering Post Sorting", "Gathering Posts collect resources 25% faster.", 1, 2, "R 1_Gathering Upgrade", "R 1_Gathering Upgrade", replace_value=("f",1.10,1.25))
    add("GatheringHeat3", "Gathering Post Insulation III", "Gathering Posts gain another +1 heat level.", 5, 2, "R 5_Gathering Insulation 2", gathering_heat)
    add("GatheringLogistics", "Gathering Post Logistics", "Gathering Posts gain another 30% gathering speed bonus.", 4, 6, "R 4_Gathering upgrade 2", "R 4_Gathering upgrade 2", replace_value=("f",1.10,1.30))
    add("SawmillOutput2", "Precision Sawmills", "Sawmills and Steam Sawmills gain a 25% production bonus.", 3, 16, saw_output, saw_output, output=1.25)
    add("CoalMineOutput3", "Coal Mine Rationalisation", "All three grades of Coal Mine gain a further 30% production bonus.", 5, 10, "R 5_Coal Mine upgrade 2", "R 5_Coal Mine upgrade 2", replace_value=("f",1.10,1.30))
    add("ThumperOutput2", "High-Flow Coal Thumpers", "Coal Thumpers and Steam Coal Thumpers pile up coal 20% faster. Staff Gathering Posts to collect it.", 4, 4, "R 3_SteamCoalThumper", saw_output, ["CoalThumper","CoalThumperSteam"], output=1.20)
    add("DrillOutput", "Precision Drill Heads", "All three Wall Drill grades gain a 20% wood production bonus.", 4, 16, "R 2_WallDrill", saw_output, ["WallDrill","WallDrillSteam","WallDrillAdvanced"], output=1.20)
    add("SteelOutput", "Steelworks Hot Blast", "All three Steelworks grades gain a 20% steel production bonus.", 4, 12, "R 1_Steel Mine", saw_output, ["Iron Ore Mine","SteamIronOreMine","AdvancedOreMine"], output=1.20)
    add("WorkshopHeat", "Workshop Draught Seals", "Workshops gain +1 heat level.", 0, 2, None, gathering_heat, ["Engineers Lab"])
    add("KilnHeat", "Kiln Insulation", "Charcoal Kilns gain +1 heat level.", 2, 14, "R 2_CharcoalKiln", gathering_heat, ["CharcoalKiln"])
    add("DrillHeat", "Wall Drill Insulation", "All three Wall Drill grades gain +1 heat level.", 3, 14, "R 2_WallDrill", gathering_heat, ["WallDrill","WallDrillSteam","WallDrillAdvanced"])
    add("IndustrialHeat", "Steelworks Insulation", "All three Steelworks grades gain +1 heat level.", 4, 16, "R 1_Steel Mine", gathering_heat, ["Iron Ore Mine","SteamIronOreMine","AdvancedOreMine"])
    add("CoalMineHeat", "Coal Mine Insulation", "All three Coal Mine grades gain +1 heat level.", 3, 16, "R 2_Coal Mine", gathering_heat, ["Coal Mine","SteamCoalMine","AdvancedCoalMine"])
    add("MedicalHeat3", "Healthcare Insulation III", "Medical Posts, Infirmaries and other buildings covered by Healthcare Insulation II gain another +1 heat level.", 5, 12, "F 6_Healthcare Buildings - warmer", "F 6_Healthcare Buildings - warmer")
    add("HouseHeat2", "House Insulation II", "Houses gain another +1 heat level.", 5, 18, "F 6_House Insulation", "F 6_House Insulation")
    add("CookhouseHeat2", "Cookhouse Insulation II", "Cookhouses gain another +1 heat level.", 4, 20, "F 3_Cantinee - warmer", "F 3_Cantinee - warmer")
    add("HothouseHeat3", "Hothouse Insulation III", "Both Hothouse grades gain another +1 heat level.", 5, 4, "F 5_Plantation Insulation", "F 5_Plantation Insulation")
    add("MedicalEfficiency2", "Medical Post Triage", "Medical Posts gain a further 25% healing speed bonus.", 2, 14, "F 2_MedPost Upgrade", "F 2_MedPost Upgrade", replace_value=("f",1.10,1.25))

    add("FieldDressings", "Field Dressings", "Medical Posts gain a 20% healing speed bonus.", 0, 12, None, "F 2_MedPost Upgrade", replace_value=("f",1.10,1.20))
    add("WardProtocols", "Infirmary Ward Protocols", "Infirmaries gain a further 30% healing speed bonus, reducing the time patients occupy beds.", 5, 14,
        "F 5_Infirmary Upgrade", "F 5_Infirmary Upgrade", replace_value=("f",1.15,1.30))
    add("CropRotation", "Hothouse Crop Rotation", "Both Hothouse grades gain a 35% workplace efficiency bonus. This is available as soon as you research Hothouse.", 1, 4,
        "F 2_Plantation", "F 6_Plantation upgrade", replace_value=("f",1.15,1.35))
    add("SeedSelection2", "Hothouse Selection II", "Both Hothouse grades gain another 35% efficiency bonus.", 5, 6,
        "F 6_Plantation upgrade", "F 6_Plantation upgrade", replace_value=("f",1.15,1.35))
    add("HuntingTrails", "Marked Hunting Trails", "Hunters' Huts bring home 3 extra raw food per hunt at full staffing.", 0, 10,
        "F 1_HuntersUpgrade", "F 1_HuntersUpgrade", replace_value=("i",5,3))
    add("HuntingSleds", "Insulated Game Sleds", "Hunters' Huts bring home another 4 raw food per hunt at full staffing.", 3, 6,
        "HuntingTrails", "F 1_HuntersUpgrade", replace_value=("i",5,4))
    add("FlightRigs", "Cold-Weather Flight Rigs", "Hunters' Hangars bring home 8 extra raw food per hunt at full staffing.", 5, 8,
        "F 5_FlyingHuntersUpgrade", "F 5_FlyingHuntersUpgrade", replace_value=("i",15,8))
    add("MedicalHeat4", "Healthcare Insulation IV", "The healthcare buildings covered by tier III gain another +1 heat level.", 5, 12,
        "MedicalHeat3", "F 6_Healthcare Buildings - warmer")
    add("HothouseHeat4", "Hothouse Insulation IV", "Both Hothouse grades gain another +1 heat level.", 5, 14,
        "HothouseHeat3", "F 5_Plantation Insulation")
    add("HubReturnLines", "Steam Hub Return Lines", "Steam Hubs use 15% less coal on top of the existing hub efficiency upgrade, with the same heat coverage.", 5, 4,
        "H 5_Steamhub Upgrade - less coal", "H 5_Steamhub Upgrade - less coal", replace_value=("f",0.666667,0.85))

    assert mod_data[4:4+len(place_class)] == place_class
    assert len({effect for _,effect in all_bindings}) == len(upgrades)
    total = struct.unpack_from("<I",mod_data)[0]
    return pack32(total + len(upgrades)) + b"".join(upgrades) + mod_data[4:]
