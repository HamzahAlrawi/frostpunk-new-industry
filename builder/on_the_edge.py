"""Research suited to On The Edge's warehouse, braziers, and local industry."""
from steel_logistics import two_scout_teams

EDGE_SHARED = {
    "Cores1", "Cores2", "Cores3", "GatheringWorkwear", "GatheringSort", "GatheringHeat3", "GatheringLogistics",
    "SawmillOutput2", "CoalMineOutput3", "ThumperOutput2", "WorkshopHeat", "KilnHeat", "CoalMineHeat",
    "MedicalHeat3", "CookhouseHeat2", "MedicalEfficiency2", "FieldDressings", "WardProtocols", "MedicalHeat4",
    "CitywideLagging", "CitywideLagging2", "CitywideLagging3", "StackedDepots", "ModularWarehouses", "DeepCoalBins",
    "ProvisionCells", "ScoutBearings", "ScoutOverhaul", "BeaconDispatch", "CoalCircuit", "WorkshopBench",
    "WorkshopSteam", "WorkshopSpeed1", "WorkshopSpeed2", "WorkshopSpeed3", "TentWindbreaks", "ServiceLiners",
    "EarlyScoutSleds", "ThumperScreens", "DepotShelving", "SawmillWindwalls", "BunkhouseDraughtLocks",
    "MineAirlocks", "InfirmaryRounds", "SawmillSurvey", "ThumperWinterization",
}


def add_edge_upgrades(add, floats, storage, tabs, mastery, buildings):
    heat = tabs["heating"]
    resources = tabs["resources"]
    food = tabs["food"]
    exploration = tabs["exploration"]
    vault_heat = "[Reconquest] R 4_VaultInsulation"
    vault = "8ba3f0878462afaac64fb87803841b4e"
    vault_efficiency = "7345b019c50cfd93904b2939d269628a"
    brazier = "7e8d2eef528353ac7a436beaa483d4e5"
    marker = b"\x01[Builders]Brazier\x00"
    offset = buildings.index(marker) + len(marker) + 16
    assert buildings[offset:offset+16].hex() == brazier
    brazier_tech = ("[Reconquest] HC 1_Brazier", "Braziers")
    depots = "R 2_ResourceDepotUpgrade"

    add("EdgeWarehouseSorting", "Warehouse Sorting Crews", "The Army Warehouse gains a 30% workplace efficiency bonus.",
        0, 10, 18, 5, 5, vault_heat, [], place_effect=(vault, vault_efficiency),
        transform=floats((1.20, 1.30)), icon=(0, 10), tab=resources)
    add("EdgeWarehouseBaffles", "Warehouse Draught Baffles", "The Army Warehouse gains one insulation level.",
        0, 18, 20, 5, 5, vault_heat, [], tab=heat)
    add("EdgeBrazierGrates", "Brazier Draught Grates", "Braziers gain a 25% reduction in coal use.",
        0, 2, 22, 6, 5, vault_heat, [brazier_tech],
        place_effect=(brazier, "06f8ad08e6435d8d2a4802290b3fad4e"), transform=floats((0.666667, 0.75)),
        icon=(10, 5), tab=heat)
    add("EdgeMealPrep", "Cookhouse Meal Prep", "Cookhouses gain a 40% workplace efficiency bonus.",
        0, 4, 15, 4, 4, "F 6_Plantation upgrade", [], target_names=["Food Processing"],
        transform=floats((1.15, 1.40)), icon=(5, 9), tab=food)
    add("EdgeTimberMaps", "Outpost Timber Maps", "Both grades of Sawmill gain a 30% cutting radius bonus.",
        0, 14, 20, 5, 5, "R 5_Sawmill Upgrade - range", [("R 1_Sawmill", "Sawmill")],
        transform=floats((1.50, 1.30)), tab=resources)
    add("EdgeRationReserve", "Ration Reserve Lockers",
        "Both sizes of Resource Depot gain a 60% capacity bonus when assigned to raw food or food rations.",
        0, 6, 15, 5, 4, depots, [], transform=storage(1.60, ("Raw Food", "Food Rations")), tab=food)
    add("EdgeFieldTeams", "Extra Reconnaissance Teams", "The Beacon can dispatch two additional scout teams.",
        0, 2, 25, 10, 6, "E 2_ScoutsLimit", [("E 1_Beacon", "Beacon")], transform=two_scout_teams, tab=exploration)
    add("EdgeSawmillCalibration", "Sawmill Blade Calibration", "Both grades of Sawmill gain a 30% wood production bonus.",
        0, 10, 20, 8, 5, "R 2_Sawmill Upgrade", [("R 1_Sawmill", "Sawmill")],
        transform=floats((1.25, 1.30)), tab=mastery)

    add("EdgeWarehouseWinches", "Warehouse Handling Winches", "The Army Warehouse gains a further 35% workplace efficiency bonus.",
        1, 20, 32, 14, 7, vault_heat, [("[Reconquest] R 1_VaultUpgrade1", "Handcarts")], place_effect=(vault, vault_efficiency),
        transform=floats((1.20, 1.35)), icon=(4, 11), tab=resources)
    add("EdgeBrazierRadius", "Brazier Heat Reflectors", "Braziers gain 4 terrain units of heating radius at the same coal use.",
        1, 2, 28, 12, 6, vault_heat, ["EdgeBrazierGrates"],
        place_effect=(brazier, "40e775fc05c6238f904da4e06ee724b6"), transform=floats((8.0, 4.0), (3.0, 0.0)),
        icon=(10, 3), tab=heat)
    add("EdgeClinicRotas", "Clinic Relief Rotas", "Medical Posts and Infirmaries gain a 25% healing speed bonus.",
        1, 14, 22, 8, 6, "F 2_MedPost Upgrade", [("F 2_MedPost Upgrade", "Medical Post Upgrade")],
        target_names=["Medical Post", "Ambulatorium"],
        transform=floats((1.10, 1.25)), tab=food)
    add("EdgeKilnCrews", "Kiln Crew Rotas", "Charcoal Kilns gain a 35% workplace efficiency bonus.",
        1, 14, 22, 10, 6, "F 6_Plantation upgrade", [("R 2_CharcoalKiln", "Charcoal Kiln")],
        target_names=["CharcoalKiln"], transform=floats((1.15, 1.35)), icon=(8, 4), tab=heat)
    add("EdgeCoalCrews", "Coal Mine Shift Crews", "All three grades of Coal Mine gain a 30% workplace efficiency bonus.",
        1, 20, 26, 12, 6, "R 3_Coal mine upgrade 1", [("R 2_Coal Mine", "Coal Mining")],
        transform=floats((1.10, 1.30)), tab=heat)
    add("EdgeDepotFuel", "Outpost Coal Bins", "Both sizes of Resource Depot gain a 60% capacity bonus when assigned to coal.",
        1, 16, 20, 8, 5, depots, [], transform=storage(1.60, ("Coal",)), tab=mastery)
