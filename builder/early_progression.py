"""Affordable research for the stock tabs in tiers 0 through III."""
import struct

def add_early_upgrades(add, floats, storage, replace_scalar, tabs):
    heating, exploration, resources, food = (tabs[name] for name in ("heating", "exploration", "resources", "food"))
    warmth = "R 3_Gathering Insulation"
    production = "R 2_Sawmill Upgrade"
    depots = "R 2_ResourceDepotUpgrade"
    scouts = "E 3_ScoutsSpeed"
    generator = "H 3_Generator Upgrade - less coal"
    thumpers = ["CoalThumper", "CoalThumperSteam"]
    sawmills = ["Sawmill", "SteamSawmill"]
    coal_mines = ["Coal Mine", "SteamCoalMine", "AdvancedCoalMine"]

    add("TentWindbreaks", "Canvas Windbreaks", "Tents gain one insulation level.",
        0, 18, 18, 0, 5, warmth, [], target_names=["Tent"], tab=food)
    add("ServiceLiners", "Essential Building Liners", "Medical Posts and Cookhouses gain one insulation level.",
        0, 14, 20, 5, 5, "F 3_Cantinee - warmer", [],
        target_names=["Medical Post", "Food Processing"], tab=heating)
    add("EarlyScoutSleds", "Scout Trail Sleds", "Scouts gain a 50% travel speed bonus.",
        0, 6, 20, 5, 5, scouts, [("E 1_Beacon", "Beacon")], tab=exploration)
    add("ThumperScreens", "Coal Thumper Screens",
        "Both grades of Coal Thumper pile up coal 25% faster. Gathering Posts collect the piles.",
        0, 8, 20, 8, 5, production, [("R 1_CoalThumper", "Coal Thumper")],
        target_names=thumpers, icon=(8, 3), tab=resources)
    add("DepotShelving", "Depot Shelving", "Both sizes of Resource Depot gain a 40% storage capacity bonus.",
        0, 12, 18, 6, 5, depots, [], transform=storage(1.40), tab=resources)
    add("SawmillWindwalls", "Sawmill Windwalls", "Both grades of Sawmill gain one insulation level.",
        0, 16, 20, 6, 5, warmth, [("R 1_Sawmill", "Sawmill")], target_names=sawmills, tab=heating)

    add("BunkhouseDraughtLocks", "Bunkhouse Draught Locks", "Bunkhouses gain one insulation level.",
        1, 18, 25, 8, 6, warmth, [("F 2_Bunkhouse", "Bunkhouse")], target_names=["Bunkhouse"], tab=food)
    add("GeneratorDraught", "Generator Draught Tuning", "The Generator gains a 20% reduction in coal use.",
        1, 8, 32, 15, 7, generator, [], transform=floats((0.9, 0.80)), tab=heating)
    add("SteelworksRolling", "Steelworks Rolling Jigs", "All three grades of Steelworks gain a 30% steel production bonus.",
        1, 20, 28, 12, 7, production, [("R 1_Steel Mine", "Steelworks")],
        target_names=["Iron Ore Mine", "SteamIronOreMine", "AdvancedOreMine"],
        transform=floats((1.25, 1.30)), icon=(8, 0), tab=resources)
    add("FoodReserveBins", "Food Reserve Bins",
        "Both sizes of Resource Depot gain a 60% capacity bonus when assigned to raw food or food rations.",
        1, 6, 25, 10, 6, depots, ["DepotShelving"], transform=storage(1.60, ("Raw Food", "Food Rations")), tab=resources)
    add("MineAirlocks", "Coal Mine Airlocks", "All three grades of Coal Mine gain one insulation level.",
        1, 18, 26, 12, 6, warmth, [("R 2_Coal Mine", "Coal Mining")], target_names=coal_mines, tab=heating)

    add("DrillGearboxes", "Wall Drill Gearboxes", "All three grades of Wall Drill gain a 30% wood production bonus.",
        2, 18, 38, 18, 8, production, [("R 2_WallDrill", "Wall Drill")],
        target_names=["WallDrill", "WallDrillSteam", "WallDrillAdvanced"], transform=floats((1.25, 1.30)), tab=resources)
    add("HubPipeLagging", "Steam Hub Pipe Lagging", "Steam Hubs gain a 15% reduction in coal use.",
        2, 10, 40, 20, 8, "H 5_Steamhub Upgrade - less coal", [("H 1_SteamHub", "Steam Hub")],
        transform=floats((0.666667, 0.85)), tab=heating)
    add("InfirmaryRounds", "Infirmary Rapid Rounds", "Infirmaries gain a 30% healing speed bonus.",
        2, 16, 38, 16, 8, "F 5_Infirmary Upgrade", [("F 3_Steam healthcare", "Infirmary")],
        transform=floats((1.15, 1.30)), tab=food)
    add("HangarCargoSlings", "Hangar Cargo Slings", "Hunters' Hangars bring home 10 extra raw food per hunt at full staffing.",
        2, 20, 38, 18, 8, "F 5_FlyingHuntersUpgrade", [("F 3_Flying Hunters", "Flying Hunters")],
        transform=lambda payload: replace_scalar(payload, struct.pack("<i", 15), struct.pack("<i", 10)), tab=food)
    add("OutpostDispatch", "Outpost Dispatch Sleds",
        "Outpost teams and resource transports gain a travel speed bonus of 30%, or 25% in Winterhome.",
        2, 6, 40, 18, 8, "E 5_ExpeditionUpgrade", [("E 3_ExpeditionCenter", "Outpost Depot")],
        transform=lambda payload: floats((1.5, 1.30) if struct.pack("<f", 1.5) in payload else (1.2, 1.25))(payload),
        tab=exploration)

    add("SawmillSurvey", "Sawmill Survey Crews", "Both grades of Sawmill gain a 25% cutting radius bonus.",
        3, 20, 42, 18, 9, "R 5_Sawmill Upgrade - range", [("R 1_Sawmill", "Sawmill")],
        transform=floats((1.5, 1.25)), tab=resources)
    add("ThumperWinterization", "Coal Thumper Winterization", "Both grades of Coal Thumper gain one insulation level.",
        3, 18, 40, 20, 8, warmth, [("R 3_SteamCoalThumper", "Steam Coal Thumper")],
        target_names=thumpers, tab=heating)
    add("CoalReserveBins", "District Coal Bunkers",
        "Both sizes of Resource Depot gain a 60% capacity bonus when assigned to coal.",
        3, 6, 45, 20, 9, depots, ["DepotShelving"], transform=storage(1.60, ("Coal",)), tab=resources)
