"""Research for the Last Autumn campaign's four native tabs."""
import struct

AUTUMN_TABS = {
    "construction": bytes.fromhex("40546df3d421bf903d466d9850b96c47"),
    "resources": bytes.fromhex("72e12c50867298b2da4b33f6d0a22f0f"),
    "heat": bytes.fromhex("caff9f2e906b55b31846d04b90384c99"),
    "food": bytes.fromhex("e38b8613cf4527a636465dc055ad4590"),
}


def construction_cost_transform(places, resources, buildings, savings):
    def cost_vector(names, amounts):
        deltas = b"".join(resources[name] + struct.pack("<i", -amount) for name, amount in amounts.items())
        return struct.pack("<I", len(names)) + b"".join(
            places[name] + struct.pack("<I", len(amounts)) + deltas for name in names
        )

    original = cost_vector(["House", "[Builders] House"], {"Wood": 10, "Steel": 10})
    revised = cost_vector(buildings, savings)

    def transform(payload):
        assert payload.count(original) == 1
        return payload.replace(original, revised)

    return transform


def add_autumn_upgrades(add, floats, storage, places, resource_ids):
    construction = AUTUMN_TABS["construction"]
    resources = AUTUMN_TABS["resources"]
    heat = AUTUMN_TABS["heat"]
    food = AUTUMN_TABS["food"]
    warmth = "R 3_Gathering Insulation"
    workshop_efficiency = "F 6_Plantation upgrade"
    dock_efficiency = "[Builders] RD 1_Docks faster reload"
    reloading_efficiency = "[Builders] RU 2_URS_Faster gathering"
    depot_capacity = "[Builders] RG 1_ResourceDepotUpgrade"
    fabrication_efficiency = "[Builders] GS 2_ManufactureCheaperMaterials"
    harbour_efficiency = "[Builders] FH 2_Fishing Harbor_efficiencyBoost"

    add("AutumnDockSignals", "Dock Signal Flags", "All three grades of Docks gain a 30% unloading efficiency bonus.",
        0, 6, 20, 5, 5, dock_efficiency, [("[Builders] RD 0_Docksv1", "Docks")],
        transform=floats((1.10, 1.30)), tab=resources)
    add("AutumnGatheringRotas", "Gathering Crew Rotas", "Gathering Posts collect resources 25% faster.",
        0, 12, 15, 5, 5, "[Builders] RG 0_Gathering Upgrade", [],
        target_names=["GatheringPost"], transform=floats((1.10, 1.25)), tab=resources)
    add("AutumnLogRacks", "Sawmill Log Racks", "Both grades of Sawmill gain a 30% wood production bonus.",
        0, 18, 20, 8, 6, "[Builders] RW 1_Sawmill Upgrade", [("[Builders] RW 0_Sawmill", "Sawmill")],
        transform=floats((1.25, 1.30)), tab=resources)
    add("AutumnReloadingGantries", "Reloading Gantries", "All three grades of Reloading Station gain a 30% gathering efficiency bonus.",
        1, 8, 26, 12, 6, reloading_efficiency, [("[Builders] RU 1_URS", "Reloading Station")],
        transform=floats((1.10, 1.30)), tab=resources)
    add("AutumnPortWarehouses", "Port Warehouse Shelving", "Both sizes of Resource Depot gain a 50% storage capacity bonus.",
        1, 10, 25, 10, 6, depot_capacity, [(depot_capacity, "Resource Depot Upgrade")],
        transform=storage(1.50), tab=resources)
    add("AutumnDockRosters", "Dock Crew Rosters", "All three grades of Docks gain a further 35% unloading efficiency bonus.",
        2, 6, 34, 15, 8, dock_efficiency, ["AutumnDockSignals", ("[Builders] RD 2_Docksv2", "Upgraded Docks")],
        transform=floats((1.10, 1.35)), tab=resources)
    add("AutumnCraneRigging", "Crane Rigging", "All three grades of Reloading Station gain a further 30% gathering efficiency bonus.",
        3, 8, 40, 20, 9, reloading_efficiency, ["AutumnReloadingGantries", ("[Builders] RU 3_URS_Steam", "Steam Reloading Station")],
        transform=floats((1.10, 1.30)), tab=resources)
    add("AutumnBulkStockyards", "Bulk Cargo Stockyards",
        "Both sizes of Resource Depot gain a 60% capacity bonus when assigned to wood, steel, or coal.",
        3, 12, 35, 15, 8, depot_capacity, ["AutumnPortWarehouses"],
        transform=storage(1.60, ("Wood", "Steel", "Coal")), tab=resources)

    add("AutumnForagerSleds", "Forager Trail Kits", "Foragers gain a 25% travel speed bonus.",
        0, 6, 20, 5, 5, "[Builders] FF 1_ForagersSpeedUpgrade", [("[Builders] FF 0_Foragers", "Foragers Quarters")],
        transform=floats((1.50, 1.25)), tab=food)
    add("AutumnFieldDressings", "Field Dressings", "Medical Posts gain a 20% healing speed bonus.",
        0, 14, 12, 4, 4, "[Builders] FM 1_MedPost Upgrade", [],
        transform=floats((1.10, 1.20)), tab=food)
    add("AutumnNetCrews", "Fishing Net Crews", "Both grades of Fishing Harbour gain a 30% fishing efficiency bonus.",
        1, 12, 24, 10, 6, harbour_efficiency, [("[Builders] FH 1_Fishing Harbor", "Fishing Harbour")],
        transform=floats((1.10, 1.30)), tab=food)
    add("AutumnColdwaterNets", "Coldwater Nets", "Both grades of Fishing Harbour gain a further 35% fishing efficiency bonus.",
        2, 12, 34, 15, 8, harbour_efficiency, ["AutumnNetCrews", (harbour_efficiency, "Finer mesh")],
        transform=floats((1.10, 1.35)), tab=food)
    add("AutumnRapidRounds", "Infirmary Rapid Rounds", "Infirmaries gain a 30% healing speed bonus.",
        3, 16, 38, 16, 8, "[Builders] FM 4_Infirmary Upgrade", [("[Builders] FM 3_Steam healthcare", "Infirmary")],
        transform=floats((1.15, 1.30)), tab=food)

    add("AutumnShelterLiners", "Site Shelter Liners", "Tents gain one insulation level.",
        0, 6, 18, 0, 5, warmth, [], target_names=["[Builders] Tent"], tab=heat)
    add("AutumnWorkshopSeals", "Workshop Draught Seals", "Workshops gain one insulation level.",
        0, 4, 16, 5, 5, warmth, [], target_names=["Engineers Lab"], tab=heat)
    add("AutumnWorkshopSpeed1", "Workshop Drafting Stations",
        "Workshops gain a 30% efficiency bonus. Citywide research speed still uses the normal Workshop scaling.",
        0, 8, 15, 5, 4, workshop_efficiency, [], target_names=["Engineers Lab"],
        transform=floats((1.15, 1.30)), icon=(0, 2), tab=heat)
    add("AutumnWorkshopSpeed2", "Workshop Reference Library", "Workshops gain a further 30% efficiency bonus.",
        0, 10, 25, 10, 6, workshop_efficiency, ["AutumnWorkshopSpeed1"], target_names=["Engineers Lab"],
        transform=floats((1.15, 1.30)), icon=(0, 2), tab=heat)
    add("AutumnServiceLiners", "Essential Building Liners", "Medical Posts and Cookhouses gain one insulation level.",
        0, 14, 20, 5, 5, "F 3_Cantinee - warmer", [], target_names=["Medical Post", "Food Processing"], tab=heat)
    add("AutumnWorkshopSpeed3", "Workshop Test Rigs", "Workshops gain a further 40% efficiency bonus.",
        1, 10, 40, 20, 9, workshop_efficiency, ["AutumnWorkshopSpeed2"], target_names=["Engineers Lab"],
        transform=floats((1.15, 1.40)), icon=(0, 2), tab=heat)
    add("AutumnWinterLining", "Winter Shelter Lining", "Tents and Bunkhouses gain one insulation level.",
        2, 6, 28, 10, 7, warmth, ["AutumnShelterLiners"], target_names=["[Builders] Tent", "[Builders] Bunkhouse"], tab=heat)

    add("AutumnProfileJigs", "Structural Profile Jigs", "Profiles Manufactures gain a 25% workplace efficiency bonus.",
        0, 4, 18, 8, 5, fabrication_efficiency, [("[Builders] GS 0_ScaffoldingManufacture", "Profiles Manufacture")],
        transform=floats((1.10, 1.25)), tab=construction)
    add("AutumnExchangerTemplates", "Steam Exchanger Templates", "Machine Shops gain a 30% workplace efficiency bonus.",
        1, 12, 26, 12, 6, fabrication_efficiency, [("[Builders] GG 1_SteamMill", "Machine Shop")],
        target_names=["[Builders]PipeFoundry"], transform=floats((1.10, 1.30)), icon=(10, 2), tab=construction)
    add("AutumnCompositeJigs", "Steel Composite Jigs", "Foundries gain a 30% workplace efficiency bonus.",
        2, 8, 30, 15, 7, "[Builders] GM 3_ForgeCheaperMaterials", [("[Builders] GM 2_SteelPlateForge", "Foundry")],
        transform=floats((1.10, 1.30)), tab=construction)
    add("AutumnFabricationSafety", "Fabrication Safety Drills", "Profiles Manufactures, Machine Shops, and Foundries gain one safety level.",
        2, 16, 38, 20, 8, "[Builders] GS 3_Manufacture safety improve", [],
        target_names=["[Builders]ScaffoldingManufacture", "[Builders]PipeFoundry", "[Builders]SteelPlateForge"],
        tab=construction)

    # House Redesign uses signed resource deltas keyed by the building's config ID.
    cost_source = "F 5_House Upgrade - cheaper"

    def cheaper(buildings, savings):
        return construction_cost_transform(places, resource_ids, buildings, savings)

    fabrication = ["[Builders]ScaffoldingManufacture", "[Builders]PipeFoundry", "[Builders]SteelPlateForge"]
    docks = ["[Builders]Dock_LVL1", "[Builders]Dock_LVL2", "[Builders]Dock_LVL3"]
    reloading = ["[Builders]ReloadingPostUniversal", "[Builders]ReloadingPostUniversal2", "[Builders]ReloadingPostUniversal3"]
    fishing = ["[Builders]DockFishing_LVL1", "[Builders]DockFishing_LVL2"]

    add("AutumnProfileGuardrails", "Profile Shop Guardrails", "Profiles Manufacture buildings gain one safety level.",
        0, 6, 16, 6, 5, "[Builders] GS 3_Manufacture safety improve", ["AutumnProfileJigs"], tab=construction)
    add("AutumnFabricationKits", "Fabrication Building Kits",
        "Profiles Manufacture, Machine Shop, and Foundry buildings each cost 8 less wood and 5 less steel to build.",
        0, 10, 18, 5, 5, cost_source, [], transform=cheaper(fabrication, {"Wood": 8, "Steel": 5}),
        icon=(3, 6), tab=construction)
    add("AutumnVentilationKits", "Ventilation Building Kits", "Ventilation Plants cost 5 less wood and 15 less steel to build.",
        1, 16, 15, 5, 5, cost_source, [("[Builders] GF 1_Air Scrubbers1", "Ventilation Plant")],
        transform=cheaper(["[Builders] Air Scrubbers"], {"Wood": 5, "Steel": 15}), icon=(9, 0), tab=construction)

    add("AutumnDockTimber", "Dock Timber Patterns", "All three grades of Docks cost 8 less wood to build.",
        0, 2, 14, 0, 4, cost_source, [("[Builders] RD 0_Docksv1", "Docks")],
        transform=cheaper(docks, {"Wood": 8}), icon=(10, 7), tab=resources)
    add("AutumnTimberMaps", "Timber Survey Maps", "Both grades of Sawmill gain a 35% cutting radius bonus.",
        0, 20, 18, 6, 5, "[Builders] RW 3_Sawmill Upgrade - range", ["AutumnLogRacks"],
        transform=floats((1.50, 1.35)), tab=resources)
    add("AutumnDepotPallets", "Depot Pallet Racks",
        "Both sizes of Resource Depot gain a 40% capacity bonus when assigned to wood or steel.",
        0, 14, 15, 5, 4, depot_capacity, [], transform=storage(1.40, ("Wood", "Steel")), tab=resources)
    add("AutumnReclaimedReloading", "Reclaimed Reloading Parts", "All three grades of Reloading Station cost one fewer Steam Core to build.",
        1, 18, 24, 10, 6, cost_source, [], transform=cheaper(reloading, {"Steam Cores": 1}),
        icon=(10, 6), tab=resources)

    add("AutumnExtraForagers", "Extra Forager Crew", "Allows one additional Foragers' Quarters and forager team.",
        0, 8, 25, 10, 6, "[Builders] FF 1_Foragers_+1", ["AutumnForagerSleds"], tab=food)
    add("AutumnKitchenKits", "Camp Service Building Kits", "Cookhouses and Medical Posts each cost 8 less wood to build.",
        0, 16, 12, 0, 4, cost_source, [], transform=cheaper(["Food Processing", "Medical Post"], {"Wood": 8}),
        icon=(4, 9), tab=food)
    add("AutumnHarbourKits", "Fishing Harbour Kits", "Both grades of Fishing Harbour cost 10 less wood and 4 less steel to build.",
        0, 10, 15, 4, 5, cost_source, [], transform=cheaper(fishing, {"Wood": 10, "Steel": 4}), icon=(4, 4), tab=food)
    add("AutumnMedicalRotas", "Medical Relief Rotas", "Medical Posts and Infirmaries gain a 25% healing speed bonus.",
        1, 16, 22, 8, 6, "[Builders] FM 1_MedPost Upgrade", ["AutumnFieldDressings"],
        target_names=["Medical Post", "Ambulatorium"], transform=floats((1.10, 1.25)), tab=food)
    add("AutumnProvisionLockers", "Provision Lockers",
        "Both sizes of Resource Depot gain a 60% capacity bonus when assigned to raw food or food rations.",
        1, 20, 20, 7, 5, depot_capacity, [], transform=storage(1.60, ("Raw Food", "Food Rations")), tab=food)

    add("AutumnCanvasPatterns", "Canvas Cutting Patterns", "Tents cost 4 less wood to build.",
        0, 16, 12, 0, 4, cost_source, [], transform=cheaper(["[Builders] Tent"], {"Wood": 4}), icon=(5, 9), tab=heat)
    add("AutumnWindproofWorksites", "Windproof Worksites", "Gathering Posts, Sawmills, Docks, and Reloading Stations gain one insulation level.",
        1, 16, 26, 10, 6, warmth, [], target_names=["GatheringPost", "Sawmill", "SteamSawmill"] + docks + reloading, tab=heat)

    add("AutumnFabricationShifts", "Fabrication Shift Boards",
        "Profiles Manufacture, Machine Shop, and Foundry buildings gain a 25% workplace efficiency bonus.",
        0, 12, 20, 8, 5, fabrication_efficiency, [], target_names=fabrication,
        transform=floats((1.10, 1.25)), tab=construction)
    add("AutumnRelayMarkers", "Forager Relay Markers", "Foragers gain another 30% travel speed bonus.",
        1, 8, 25, 10, 6, "[Builders] FF 1_ForagersSpeedUpgrade", ["AutumnExtraForagers"],
        transform=floats((1.50, 1.30)), tab=food)
    add("AutumnPortClearing", "Port Clearing Crews", "All three grades of Docks gain a further 30% unloading efficiency bonus.",
        0, 8, 22, 8, 5, dock_efficiency, ["AutumnDockSignals"], transform=floats((1.10, 1.30)), tab=resources)
    add("AutumnHeavyCargo", "Heavy Cargo Handling", "All three grades of Reloading Station gain a 40% gathering efficiency bonus.",
        1, 20, 28, 12, 7, reloading_efficiency, [], transform=floats((1.10, 1.40)), tab=resources)
    add("AutumnKitchenRotas", "Camp Kitchen Rotas", "Cookhouses gain a 40% workplace efficiency bonus.",
        0, 18, 15, 5, 4, workshop_efficiency, [], target_names=["Food Processing"],
        transform=floats((1.15, 1.40)), icon=(5, 9), tab=food)
    add("AutumnSeasonalFishing", "Seasonal Fishing Crews", "Both grades of Fishing Harbour gain a 30% fishing efficiency bonus.",
        0, 12, 20, 8, 5, harbour_efficiency, [], transform=floats((1.10, 1.30)), tab=food)
    add("AutumnCampReserves", "Camp Supply Reserves",
        "Both sizes of Resource Depot gain a 50% capacity bonus when assigned to coal or food rations.",
        1, 16, 20, 8, 5, depot_capacity, [], transform=storage(1.50, ("Coal", "Food Rations")), tab=resources)


def add_autumn_expansion(add, floats):
    food = AUTUMN_TABS["food"]
    resources = AUTUMN_TABS["resources"]
    construction = AUTUMN_TABS["construction"]
    heat = AUTUMN_TABS["heat"]
    add("AutumnFoodLineInsulation", "Harbour Food Line Insulation",
        "Cookhouses and both grades of Fishing Harbour gain one insulation level.",
        1, 12, 25, 10, 6, "F 3_Cantinee - warmer", [("[Builders] FH 1_Fishing Harbor","Fishing Harbour")],
        target_names=["Food Processing","[Builders]DockFishing_LVL1","[Builders]DockFishing_LVL2"], tab=heat)
    add("AutumnKilnShifts", "Charcoal Kiln Stoking Crews", "Charcoal Kilns gain a 40% workplace efficiency bonus.",
        2, 20, 36, 16, 8, "F 6_Plantation upgrade", [("[Builders] RC 2_CharcoalKiln","Charcoal Kiln")],
        target_names=["CharcoalKiln"], transform=floats((1.15,1.40)), icon=(8,4), tab=resources)
    add("AutumnExchangerRigs", "Heavy Fabrication Rigs", "Machine Shops and Foundries gain a 35% workplace efficiency bonus.",
        2, 14, 38, 20, 9, "[Builders] GS 2_ManufactureCheaperMaterials", ["AutumnExchangerTemplates"],
        target_names=["[Builders]PipeFoundry","[Builders]SteelPlateForge"], transform=floats((1.10,1.35)),
        icon=(10,2), tab=construction)
    add("AutumnForagerRosters", "Forager Roster Office", "Allows one additional Foragers' Quarters and forager team.",
        2, 4, 45, 22, 9, "[Builders] FF 1_Foragers_+1", [("[Builders] FF 1_Foragers_+1","More Foragers")], tab=food)
    add("AutumnEmergencyWards", "Emergency Ward Stations", "Medical Posts and Infirmaries gain a further 30% healing speed bonus.",
        2, 16, 36, 18, 8, "[Builders] FM 1_MedPost Upgrade", ["AutumnMedicalRotas"],
        target_names=["Medical Post","Ambulatorium"], transform=floats((1.10,1.30)), tab=food)
    add("AutumnPortConsolidation", "Consolidated Port Handling", "Docks and Reloading Stations gain a further 30% workplace efficiency bonus.",
        3, 16, 50, 25, 10, "[Builders] RD 1_Docks faster reload", [],
        target_names=["[Builders]Dock_LVL1","[Builders]Dock_LVL2","[Builders]Dock_LVL3",
                      "[Builders]ReloadingPostUniversal","[Builders]ReloadingPostUniversal2","[Builders]ReloadingPostUniversal3"],
        transform=floats((1.10,1.30)), tab=resources)
