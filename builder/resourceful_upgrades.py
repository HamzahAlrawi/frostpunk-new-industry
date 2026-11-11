"""Research that changes where buildings reach and how scarce cores are allocated."""
from last_autumn import AUTUMN_TABS, construction_cost_transform


EDGE_RESOURCEFUL = {"GatheringReach", "MiningCoreMounts"}


def add_resourceful_upgrades(add, places, resources, tabs):
    reach = "R 5_Sawmill Upgrade - range"
    cost = "F 5_House Upgrade - cheaper"
    add("GatheringReach", "Gathering Sled Networks",
        "Gathering Posts gain a 50% collection radius bonus, letting each post reach more resource piles.",
        1, 2, 24, 10, 6, reach, [], target_names=["GatheringPost"],
        icon=(3, 9), tab=tabs["resources"])
    add("AutumnGatheringReach", "Gathering Sled Networks",
        "Gathering Posts gain a 50% collection radius bonus, letting each post reach more resource piles.",
        1, 4, 24, 10, 6, reach, [], target_names=["GatheringPost"],
        icon=(3, 9), tab=AUTUMN_TABS["resources"])
    add("HothouseCoreMounts", "Modular Hothouse Core Mounts",
        "Both grades of Hothouse cost one fewer Steam Core to build. A standard Hothouse can be built without a core, and an Industrial Hothouse needs one core.",
        2, 6, 50, 30, 10, cost, [("F 2_Plantation", "Hothouse")],
        transform=construction_cost_transform(places, resources, ["Plantation", "Steam Plantation"], {"Steam Cores": 1}), icon=(0, 2))
    add("MiningCoreMounts", "Modular Extraction Cassettes",
        "All grades of Coal Mine and Wall Drill cost one fewer Steam Core to build. Basic Coal Mines and Wall Drills can be built without a core.",
        3, 2, 70, 50, 12, cost, [("R 2_Coal Mine", "Coal Mining")],
        transform=construction_cost_transform(places, resources,
            ["Coal Mine", "SteamCoalMine", "AdvancedCoalMine", "WallDrill", "WallDrillSteam", "WallDrillAdvanced"],
            {"Steam Cores": 1}), icon=(0, 2), tab=tabs["resources"])
    add("AutumnCraneBrakes", "Crane Arrestor Brakes",
        "All three grades of Reloading Station gain one safety level, offsetting the extra danger of upgraded machinery.",
        2, 8, 38, 20, 8, "[Builders] GS 3_Manufacture safety improve",
        [("[Builders] RU 1_URS", "Reloading Station")],
        target_names=["[Builders]ReloadingPostUniversal", "[Builders]ReloadingPostUniversal2", "[Builders]ReloadingPostUniversal3"],
        icon=(10, 1), tab=AUTUMN_TABS["resources"])
