"""Steelworks research and the native scout expedition limit adjustment."""
import struct


def two_scout_teams(payload):
    offset = 177
    assert len(payload) == 238
    assert payload[offset-4:offset+8] == struct.pack("<fif", 1.0, 1, 1.0)
    return payload[:offset] + struct.pack("<i", 2) + payload[offset+4:]


def add_steel_logistics(add, floats, storage, tabs):
    steelworks = ["Iron Ore Mine", "SteamIronOreMine", "AdvancedOreMine"]
    unlock = ("R 1_Steel Mine", "Steelworks")
    depot = "R 2_ResourceDepotUpgrade"
    add("SteelworksRefractoryLining", "Steelworks Refractory Linings",
        "All three grades of Steelworks gain one insulation level.",
        1, 18, 27, 14, 6, "R 3_Gathering Insulation", [unlock], target_names=steelworks)
    add("SteelworksIngotRacks", "Ingot Storage Cradles",
        "Both sizes of Resource Depot gain an 80% capacity bonus for steel.",
        1, 20, 24, 10, 6, depot, [], transform=storage(1.80, ("Steel",)))
    add("SteelworksShiftTeams", "Steelworks Shift Teams",
        "Human crews and automatons gain a 40% workplace efficiency bonus at every grade of Steelworks.",
        3, 14, 58, 36, 10, "F 6_Plantation upgrade", [unlock], target_names=steelworks,
        transform=floats((1.15,1.40)), icon=(8,0), tab=tabs["exploration"])
    add("SteelworksContinuousCasting", "Continuous Casting",
        "All three grades of Steelworks gain a further 45% steel production bonus.",
        4, 12, 88, 65, 14, "R 2_Sawmill Upgrade", ["SteelworksShiftTeams"], target_names=steelworks,
        transform=floats((1.25,1.45)), icon=(8,0), tab=tabs["resources"])
