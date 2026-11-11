"""Low- and mid-tier branches for City Mastery and the native research tabs."""
from steel_logistics import two_scout_teams

EDGE_COMPATIBLE = {
    "MasteryCargoRacks", "MasteryClinicSteam", "MasteryFactoryLines", "MasteryFuelDistrict",
    "WorksiteWarmBreaks", "SteamThumperFeed", "InfirmaryRecoveryWards", "CookhouseSteamShell",
}


def add_expansion(add, floats, storage, tabs):
    production = "R 2_Sawmill Upgrade"
    workplace = "F 6_Plantation upgrade"
    warmth = "R 3_Gathering Insulation"
    depot = "R 2_ResourceDepotUpgrade"
    medical = "F 2_MedPost Upgrade"
    infirmary = ("F 3_Steam healthcare", "Infirmary")
    factory = ("E 3_Factory", "Factory")
    kiln = ("R 2_CharcoalKiln", "Charcoal Kiln")
    sawmill = ("R 1_Sawmill", "Sawmill")
    steelworks = ["Iron Ore Mine", "SteamIronOreMine", "AdvancedOreMine"]
    coal_mines = ["Coal Mine", "SteamCoalMine", "AdvancedCoalMine"]
    hothouses = ["Plantation", "Steam Plantation"]
    clinics = ["Medical Post", "Ambulatorium"]
    safety = "H 6_Generator Upgrade - less stress"
    automaton_efficiency = "E 4_Automaton Efficiency"

    add("MasteryPrepBenches", "Cookhouse Prep Benches", "Cookhouses gain a 40% workplace efficiency bonus.",
        0, 4, 15, 4, 4, workplace, [], target_names=["Food Processing"], transform=floats((1.15,1.40)), icon=(5,9))
    add("MasteryCargoRacks", "Bulk Cargo Racks", "Both sizes of Resource Depot gain a 40% capacity bonus for wood and steel.",
        0, 14, 18, 6, 5, depot, [], transform=storage(1.40, ("Wood","Steel")))
    add("MasteryTimberSurvey", "Timber Survey Stakes", "Both grades of Sawmill gain a 30% cutting radius bonus.",
        0, 8, 18, 6, 5, "R 5_Sawmill Upgrade - range", [sawmill], transform=floats((1.50,1.30)))
    add("MasteryScoutDispatch", "Scout Dispatch Shift", "The Beacon can dispatch two additional scout teams.",
        0, 18, 28, 12, 6, "E 2_ScoutsLimit", [("E 1_Beacon","Beacon")], transform=two_scout_teams)

    add("MasteryKilnRotas", "Kiln Stoking Crews", "Charcoal Kilns gain a 35% workplace efficiency bonus.",
        1, 14, 23, 10, 6, workplace, [kiln], target_names=["CharcoalKiln"], transform=floats((1.15,1.35)), icon=(8,4))
    add("MasteryHubDraught", "Steam Hub Draught Controls", "Steam Hubs gain a 10% reduction in coal use.",
        1, 2, 27, 12, 6, "H 5_Steamhub Upgrade - less coal", [("H 1_SteamHub","Steam Hub")],
        transform=floats((0.666667,0.90)))
    add("MasteryIrrigation", "Hothouse Irrigation Lines", "Both grades of Hothouse gain a 30% workplace efficiency bonus.",
        1, 8, 28, 12, 7, workplace, [("F 2_Plantation","Hothouse")], transform=floats((1.15,1.30)))
    add("MasteryClinicRotas", "Clinic Supply Rotas", "Medical Posts and Infirmaries gain a 25% healing speed bonus.",
        1, 12, 24, 10, 6, medical, [(medical,"Medical Post Upgrade")], target_names=clinics, transform=floats((1.10,1.25)))

    add("MasteryAutomatonCalibration", "Automaton Calibration", "Automaton efficiency increases by 25 percentage points.",
        2, 20, 48, 30, 9, automaton_efficiency, [factory], transform=floats((0.10,0.25)), tab=tabs["exploration"])
    add("MasteryOverdriveValves", "Overdrive Pressure Valves",
        "Generator stress builds 15% more slowly and recovers 15% faster.",
        2, 16, 54, 35, 10, safety, [("H 3_Generator Overdrive 1","Overdrive Couplings")],
        transform=floats((0.75,0.85),(1.25,1.15)))
    add("MasteryClinicSteam", "Clinic Steam Lines", "Medical Posts and Infirmaries gain one insulation level.",
        2, 12, 38, 18, 8, warmth, [infirmary], target_names=clinics)
    add("MasterySteelFeeders", "Powered Steelworks Feeders", "All three grades of Steelworks gain a 30% steel production bonus.",
        2, 14, 45, 24, 8, production, [("R 1_Steel Mine","Steelworks")], target_names=steelworks,
        transform=floats((1.25,1.30)), icon=(8,0))
    add("MasteryProvisionLines", "Provision Processing Lines", "Hothouses and Cookhouses gain another 30% workplace efficiency bonus.",
        2, 8, 46, 24, 9, workplace, ["MasteryIrrigation"], target_names=hothouses+["Food Processing"],
        transform=floats((1.15,1.30)))

    add("MasteryFactoryLines", "Modular Factory Lines", "Factories gain a 50% workplace efficiency bonus.",
        3, 20, 62, 38, 11, workplace, [factory], target_names=["Factory"],
        transform=floats((1.15,1.50)), icon=(0,2))
    add("MasteryOverdriveRecovery", "Stress Recovery Governors", "The Generator gains a further 20% stress recovery speed bonus.",
        3, 16, 68, 45, 12, safety, ["MasteryOverdriveValves"], transform=floats((0.75,1.0),(1.25,1.20)))
    add("MasteryFuelDistrict", "District Fuel Processing", "Coal Mines and Charcoal Kilns gain a 35% workplace efficiency bonus.",
        3, 14, 66, 36, 11, workplace, [kiln], target_names=coal_mines+["CharcoalKiln"],
        transform=floats((1.15,1.35)), icon=(8,4))

    add("MasteryMedicalAutomata", "Medical Automaton Gauges", "Automatons in Medical Posts and Infirmaries gain a 50% efficiency bonus.",
        4, 12, 85, 55, 14, "E 6_Automatons Medical 2", [("E 5_Automaton Medical","Medical Automatons")],
        transform=floats((1.20,1.50)))
    add("MasteryWorksNetwork", "Municipal Works Network",
        "Sawmills, Steelworks, Coal Mines, and Wall Drills gain a 35% production bonus across all grades.",
        5, 8, 160, 115, 20, production, ["MineLifts"],
        target_names=["Sawmill","SteamSawmill","WallDrill","WallDrillSteam","WallDrillAdvanced"]+steelworks+coal_mines,
        transform=floats((1.25,1.35)), icon=(8,0))

    add("HuntersFieldKits", "Hunters' Field Kits", "Hunters' Huts bring home 5 extra raw food per hunt at full staffing.",
        0, 2, 18, 5, 5, "F 1_HuntersUpgrade", [("F 1_HuntersUpgrade","Hunters' Gear")], tab=tabs["food"])
    add("CookhouseSteamShell", "Cookhouse Steam Shells", "Cookhouses gain one insulation level.",
        1, 20, 25, 9, 6, "F 3_Cantinee - warmer", [], tab=tabs["food"])
    add("WorksiteWarmBreaks", "Heated Break Shelters", "Gathering Posts and both grades of Sawmill gain one insulation level.",
        1, 18, 25, 10, 6, warmth, [], target_names=["GatheringPost","Sawmill","SteamSawmill"], tab=tabs["heating"])
    add("SteamThumperFeed", "Thumper Feed Regulators", "Both grades of Coal Thumper pile up coal 35% faster.",
        2, 20, 41, 22, 8, production, [("R 3_SteamCoalThumper","Steam Coal Thumper")],
        target_names=["CoalThumper","CoalThumperSteam"], transform=floats((1.25,1.35)), icon=(8,3))
    add("ClockworkSynchronisers", "Clockwork Synchronisers", "Automaton efficiency increases by another 20 percentage points.",
        3, 20, 62, 42, 12, automaton_efficiency, ["MasteryAutomatonCalibration"],
        transform=floats((0.10,0.20)), tab=tabs["exploration"])
    add("InfirmaryRecoveryWards", "Infirmary Recovery Wards", "Infirmaries and Houses of Healing gain a 35% healing speed bonus.",
        3, 10, 49, 28, 9, "F 5_Infirmary Upgrade", [infirmary],
        target_names=["Ambulatorium","HospitalOfMercy"], transform=floats((1.15,1.35)), tab=tabs["food"])
