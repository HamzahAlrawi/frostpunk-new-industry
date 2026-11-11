"""House insulation and additional research for industrial cities."""
from last_autumn import AUTUMN_TABS


EDGE_ADDITIONS = {"HouseVestibules", "HouseInsulatedFloors", "CoalHandlingShelters"}


def add_industry_housing(add, floats, storage, tabs):
    warmth = "R 3_Gathering Insulation"
    depot = "R 2_ResourceDepotUpgrade"
    machine_work = "E 6_Automatons Medical 2"
    factory = ("E 3_Factory", "Factory")

    add("HouseVestibules", "House Draughtproof Vestibules", "Houses gain one insulation level.",
        3, 18, 60, 40, 10, warmth, [("F 4_House","House")], target_names=["House"], tab=tabs["food"])
    add("HouseInsulatedFloors", "House Insulated Floors", "Houses gain one additional insulation level.",
        4, 16, 95, 70, 14, warmth, ["HouseVestibules"], target_names=["House"], tab=tabs["food"])

    add("AutomatonSawmillServos", "Automaton Timber Servos",
        "Automatons gain a 30% workplace efficiency bonus in Sawmills and Steam Sawmills.",
        2, 14, 38, 20, 8, machine_work, [factory], target_names=["Sawmill","SteamSawmill"],
        transform=floats((1.20,1.30)), icon=(2,5), tab=tabs["resources"])
    add("AutomatonSteelworksServos", "Automaton Mill Governors",
        "Automatons gain a 35% workplace efficiency bonus in all three grades of Steelworks.",
        2, 8, 44, 24, 9, machine_work, [factory], target_names=["Iron Ore Mine","SteamIronOreMine","AdvancedOreMine"],
        transform=floats((1.20,1.35)), icon=(8,0), tab=tabs["resources"])
    add("AutomatonWallDrillServos", "Automaton Drill Actuators",
        "Automatons gain a 35% workplace efficiency bonus in all three grades of Wall Drill.",
        3, 20, 54, 30, 10, machine_work, [factory], target_names=["WallDrill","WallDrillSteam","WallDrillAdvanced"],
        transform=floats((1.20,1.35)), icon=(8,1), tab=tabs["resources"])

    add("EmergencyFoodBins", "Emergency Food Bins", "Both sizes of Resource Depot gain a 45% capacity bonus for raw food and food rations.",
        0, 2, 16, 5, 4, depot, [], transform=storage(1.45, ("Raw Food","Food Rations")))
    add("CoalHandlingShelters", "Coal Handling Shelters", "Both grades of Coal Thumper and Charcoal Kilns gain one insulation level.",
        1, 4, 24, 10, 6, warmth, [("R 1_CoalThumper","Coal Thumper")],
        target_names=["CoalThumper","CoalThumperSteam","CharcoalKiln"])
    add("CoalStorageCompactors", "Coal Storage Compactors", "Both sizes of Resource Depot gain a 65% capacity bonus for coal.",
        2, 18, 38, 20, 8, depot, [("R 2_ResourceDepotUpgrade","Resource Depot Upgrade")],
        transform=storage(1.65, ("Coal",)))
    add("CareHouseLiners", "Care House Thermal Liners", "Care Houses and Houses of Healing gain one insulation level.",
        1, 10, 26, 10, 6, warmth, [], target_names=["CareHouse","HospitalOfMercy"])

    add("AutumnMachineGuards", "Machine Shop Safety Screens", "Machine Shops and Foundries gain one safety level.",
        1, 8, 27, 12, 6, "[Builders] GG 3_Steam Mill safety improve", [("[Builders] GG 1_SteamMill","Machine Shop")],
        target_names=["[Builders]PipeFoundry","[Builders]SteelPlateForge"], tab=AUTUMN_TABS["construction"])
    add("AutumnCoalCompactors", "Port Coal Compactors", "Both sizes of Resource Depot gain a 65% capacity bonus for coal.",
        2, 14, 35, 17, 7, "[Builders] RG 1_ResourceDepotUpgrade", [("[Builders] RG 1_ResourceDepotUpgrade","Resource Depot Upgrade")],
        transform=storage(1.65, ("Coal",)), tab=AUTUMN_TABS["resources"])
    add("AutumnFuelWorkwear", "Fuel Crew Workwear", "Charcoal Kilns and Gathering Posts gain one insulation level.",
        1, 14, 22, 8, 5, warmth, [], target_names=["CharcoalKiln","GatheringPost"], tab=AUTUMN_TABS["heat"])
