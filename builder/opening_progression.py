"""Research available before Drawing Boards and supplies for new cities."""
import struct

from last_autumn import AUTUMN_TABS


OPENING_STOCK = {"Wood": 40, "Steel": 25, "Coal": 50, "Raw Food": 30}
OPENING_PROFILES = {
    "Default", "TechHaven", "Refugees", "Winterhome", "Builders", "Reconquest",
    "Custom_Endless", "Custom_Endless_Serenity",
}
EDGE_OPENING = {"StarterGatheringTeams", "StarterTimberTools", "StarterWardStoves"}
# 25% higher base Workshop research output than 3.9, preserving the native
# one-to-four-Workshop diminishing-return curve and both workforce roles.
RESEARCH_SPEED = 1.25 * 1.25
PERK_RESEARCH_DURATION = 0.5


def starting_supplies(data, resources):
    amounts = {resources[name]: extra for name, extra in OPENING_STOCK.items()}
    changes = {}
    revised = bytearray(data)
    # Only the top-level starting-resource profiles. Other vectors include
    # scout rewards, test presets and starting supplies in custom maps.
    pos = data.index(b"\1\1Default\0" + bytes.fromhex("abffde98fc17e8921d495b49e5928974"))
    count, = struct.unpack_from("<I", data, pos - 4)
    assert count == 17
    for _ in range(count):
        assert data[pos:pos + 2] == b"\1\1"
        end = data.index(0, pos + 2)
        name = data[pos + 2:end].decode("ascii")
        pos = end + 17  # Name terminator and profile GUID.
        count, = struct.unpack_from("<I", data, pos)
        pos += 4
        if name in OPENING_PROFILES:
            changes[name] = set()
            for entry in range(pos, pos + count * 20, 20):
                resource = data[entry:entry + 16]
                if resource in amounts:
                    value, = struct.unpack_from("<I", data, entry + 16)
                    struct.pack_into("<I", revised, entry + 16, value + amounts[resource])
                    changes[name].add(resource)
        pos += count * 20
        for _ in range(2):  # Optional display name and description.
            assert data[pos] in (0, 1)
            pos = data.index(0, pos + 1) + 1 if data[pos] else pos + 1
    assert changes.keys() == OPENING_PROFILES
    for name, changed in changes.items():
        assert changed == amounts.keys() - ({resources["Coal"]} if name == "Builders" else set()), name
    return bytes(revised)


def research_curve(data):
    # Four native knots give the total rate for one through four active Workshops.
    size = struct.calcsize("<I8f")
    assert struct.unpack_from("<I8f", data) == struct.unpack("<I8f", struct.pack(
        "<I8f", 4, 1, 1, 2, 1.3, 3, 1.5, 4, 1.6
    ))
    knots = (1, 1.3, 1.5, 1.6)
    revised = b"".join(struct.pack("<ff", workshops, rate * RESEARCH_SPEED)
                       for workshops, rate in enumerate(knots, start=1))
    return data[:4] + revised + data[size:]


def add_opening_upgrades(add, floats, replace_scalar, tabs):
    sawmills = ["Sawmill", "SteamSawmill"]
    steelworks = ["Iron Ore Mine", "SteamIronOreMine", "AdvancedOreMine"]
    gathering = "R 1_Gathering Upgrade"
    production = "R 2_Sawmill Upgrade"
    warmth = "R 3_Gathering Insulation"
    autumn = AUTUMN_TABS

    add("StarterGatheringTeams", "Salvage Sorting Stations", "Gathering Posts collect resources 75% faster.",
        0, 6, 12, 0, 4, gathering, [], transform=floats((1.10, 1.75)))
    add("StarterTimberTools", "Gang Saw Blades", "Both grades of Sawmill gain a 75% wood production bonus.",
        0, 12, 16, 4, 4, production, [], transform=floats((1.25, 1.75)))
    add("StarterSteelTooling", "Steelworks Charge Bins", "All three grades of Steelworks gain a 75% steel production bonus.",
        0, 16, 16, 6, 4, production, [], target_names=steelworks, transform=floats((1.25, 1.75)), icon=(8, 0))
    add("StarterGeneratorGrates", "Generator Draft Grates", "The Generator burns 20% less coal.",
        0, 10, 16, 6, 4, "H 3_Generator Upgrade - less coal", [],
        transform=floats((0.90, 0.80)), tab=tabs["heating"])
    add("StarterHubValves", "Steam Hub Flow Valves", "Steam Hubs burn 20% less coal.",
        0, 20, 14, 5, 4, "H 5_Steamhub Upgrade - less coal", [], transform=floats((0.666667, 0.80)))
    add("StarterHuntingKits", "Hunter Trail Caches", "Hunters' Huts bring home 4 extra raw food per hunt at full staffing.",
        0, 10, 12, 0, 4, "F 1_HuntersUpgrade", [],
        transform=lambda data: replace_scalar(data, struct.pack("<i", 5), struct.pack("<i", 4)), tab=tabs["food"])
    add("StarterWardStoves", "Insulated Sick Wards", "Medical Posts, Infirmaries, and Care Houses gain one insulation level.",
        0, 16, 14, 4, 4, warmth, [], target_names=["Medical Post", "Ambulatorium", "CareHouse"], tab=tabs["food"])

    add("AutumnStarterGathering", "Salvage Sorting Stations", "Gathering Posts collect resources 75% faster.",
        0, 14, 12, 0, 4, gathering, [], transform=floats((1.10, 1.75)), tab=autumn["construction"])
    add("AutumnStarterTimber", "Gang Saw Blades", "Both grades of Sawmill gain a 75% wood production bonus.",
        0, 16, 16, 4, 4, production, [], target_names=sawmills,
        transform=floats((1.25, 1.75)), tab=autumn["construction"])
    add("AutumnStarterFishing", "Harbour Tidal Charts", "Both grades of Fishing Harbour gain a 75% fishing efficiency bonus.",
        0, 20, 16, 4, 4, "[Builders] FH 2_Fishing Harbor_efficiencyBoost", [],
        transform=floats((1.10, 1.75)), tab=autumn["food"])
    add("AutumnStarterSafety", "Fabrication Safety Walkways", "Profiles Manufacture buildings, Machine Shops, and Foundries gain one safety level.",
        0, 18, 14, 4, 4, "[Builders] GS 3_Manufacture safety improve", [],
        target_names=["[Builders]ScaffoldingManufacture", "[Builders]PipeFoundry", "[Builders]SteelPlateForge"],
        tab=autumn["construction"])
