"""Optional production recipes using each station's native product and queue format."""
import re
import struct

from last_autumn import AUTUMN_TABS


EDGE_RECIPES = {"RetortCharcoal", "RapidCoking"}
PRODUCTION = b"\1FrostpunkProductionComponentTemplate\0"


def uint(value):
    return struct.pack("<I", value)


def string(value):
    return b"\1" + value.encode() + b"\0"


def native_production_recipes(blueprints):
    entries = list(re.finditer(rb"\x01\x01([ -~]+)\x00(.{16})", blueprints, re.S))
    return {entry.group(1).decode(): blueprints[entry.end():entries[i + 1].start()]
            for i, entry in enumerate(entries[:-1])}


def encode_station_recipe(native, key, title, source, building, paths, output, amount,
                          inputs, hours, research, resources, guid, localize, costs,
                          requirement, *, exclusions=(), negate=None):
    """Use the source station's native product flags and typed recipe tail."""
    sample = native[source]
    atlas = string("UI\\Elements\\Resources_Icos.dds")
    if atlas not in sample:
        atlas = string("UI\\Elements\\Resources_Icons2.dds")
    icon_at = sample.index(atlas) + len(atlas)
    product = string("FrostpunkResourceProduct")
    resource_product = product in sample
    if not resource_product:
        product = string("FrostpunkFoodRationProduct")
    product_at = sample.index(product) + len(product)
    assert sample[icon_at + 16:icon_at + 22] in (b"\1\0\1\0\0\0", b"\1\1\1\0\0\0", b"\0\1\1\0\0\0")
    assert sample[product_at:product_at + 4] == uint(1)
    input_at = product_at + (28 if resource_product else 16)
    count, = struct.unpack_from("<I", sample, input_at)
    tail = sample[input_at + 4 + count * 20 + 4:]
    if source.startswith("[Reconquest]Vault_"):
        assert tail.startswith(uint(2) + bytes(6) + b"\1@")
        tail = uint(2) + bytes(7)
    assert tail in (uint(2) + bytes(7), uint(2) + uint(1) + b"\0\1\0")
    recipe_id = guid("recipe/" + key)
    items = ", ".join(f"{quantity} {name.lower()}" for name, quantity in inputs.items())
    output_name = {"Wooden Materials": "structural profiles", "Steam Tools": "steam exchangers", "Steel Plates": "steel composites"}.get(output, output.lower())
    description = f"Optional {building} recipe. Spend {items} to produce {amount} {output_name} in {hours:g} working hours at full efficiency. Select this recipe in the building panel."
    conditions = [requirement(research)]
    if exclusions:
        assert negate is not None
        conditions += [negate(value) for value in exclusions]
    data = b"\1" + string("NI " + key) + recipe_id + uint(len(conditions)) + b"".join(conditions)
    data += localize("Recipe/" + key + "/Name", title) + localize("Recipe/" + key + "/Description", description) + bytes(2)
    coordinates = sample[icon_at:icon_at + 16]
    output_data = string("FrostpunkResourceProduct") + uint(1) + resources[output] + uint(amount)
    display_atlas = string("UI\\Elements\\Resources_Icos.dds")
    if output == "Food Rations":
        display_atlas = string("UI\\Elements\\Resources_Icons2.dds")
        coordinates = struct.pack("<4i", 0, 1, 4, 4)
        output_data = string("FrostpunkFoodRationProduct") + uint(1) + uint(amount) + uint(3)
    data += display_atlas + coordinates + sample[icon_at + 16:icon_at + 17] + b"\1" + uint(1)
    data += output_data + uint(0) + costs(inputs) + struct.pack("<f", hours) + tail
    info = dict(id=key, title=title, output=output, amount=amount, inputs=inputs, hours=hours,
                building=building, source_blueprint=source, unlock=research.hex(), targets=paths)
    if exclusions:
        info['excludes'] = [value.hex() for value in exclusions]
    return recipe_id, data, info


def attach_recipes(template, recipes):
    offset = template.index(PRODUCTION) + len(PRODUCTION) + 16
    count, = struct.unpack_from("<I", template, offset)
    end = offset + 4 + count * 16
    assert 1 <= count <= 9 and template[end + 17:end + 27] == b"\1Frostpunk"
    assert len(recipes) == len(set(recipes))
    assert not any(recipe in template[offset + 4:end] for recipe in recipes)
    return template[:offset] + uint(count + len(recipes)) + template[offset + 4:end] + b"".join(recipes) + template[end:]


def build_station_recipes(technology, blueprints, vanilla, resources, guid, localize, costs, requirement, tabs):
    native = native_production_recipes(blueprints)
    recipes = []
    targets = {}
    tier_names = {0: [], 1: ["Drawing Boards (I)"], 2: ["Drafting Machines (II)"]}

    def unlock(key, title, description, tier, column, tab, materials, hours, parents, icon):
        prerequisites = tier_names[tier] + [display for _, display in parents]
        return technology(key, title, description + "\n\nRequires: " + (", ".join(prerequisites) or "No prior research") + ".",
                          tier, column, [vanilla[name] for name, _ in parents], materials, hours, icon, tab,
                          prerequisite_names=prerequisites)

    def recipe(key, title, source, building, paths, output, amount, inputs, hours, research):
        record = encode_station_recipe(native,key,title,source,building,paths,output,amount,inputs,
                                       hours,research,resources,guid,localize,costs,requirement)
        recipe_id = record[0]
        recipes.append(record)
        for path in paths:
            targets.setdefault("gameentities/buildings/" + path + ".binarytemplate", []).append(recipe_id)

    kiln_desc = "Unlocks Retort Kiln Batches. Spend 7 wood and 1 steel for 56 coal in 1 working hour at full efficiency. Steel maintains the sealed retorts, saving wood per unit of coal. Select the recipe at a Charcoal Kiln."
    kiln = unlock("RetortCharcoal", "Retort Kiln Batches", kiln_desc, 1, 12, tabs["heating"],
                  {"Wood": 24, "Steel": 10}, 6, [("R 2_CharcoalKiln", "Charcoal Kiln")], (8, 4))
    kiln_path = ["resourceprocessing/charcoalkiln"]
    recipe("RetortCharcoal", "Retort Kiln Batches", "CharcoalKiln_Coal", "Charcoal Kiln", kiln_path,
           "Coal", 56, {"Wood": 7, "Steel": 1}, 1, kiln)

    growing = unlock("CoalHeatedSeedbeds", "Coal-Heated Seedbeds",
                     "Unlocks optional Hothouse growing recipes. Spend 2 coal for 4 raw food in 40 working minutes, or 4 coal for 8 raw food in an Industrial Hothouse. Both run at roughly twice the normal base growing rate. Select the recipe at each Hothouse.",
                     1, 8, tabs["food"], {"Wood": 25, "Steel": 10}, 6, [("F 2_Plantation", "Hothouse")], (5, 9))
    for key, source, path, name, amount, coal in (
        ("CoalHeatedSeedbeds", "Plantation_Food", "resourceextraction/foodplantation", "Hothouse", 4, 2),
        ("IndustrialCoalSeedbeds", "SteamPlantation_Food", "resourceextraction/foodplantation_steam", "Industrial Hothouse", 8, 4),
    ):
        recipe(key, "Coal-Heated Seedbeds", source, name, [path], "Raw Food", amount, {"Coal": coal}, 2 / 3, growing)

    autumn = AUTUMN_TABS
    kiln_autumn = unlock("AutumnRetortCharcoal", "Retort Kiln Batches", kiln_desc, 2, 2, autumn["heat"],
                         {"Wood": 24, "Steel": 10}, 6, [("[Builders] RC 2_CharcoalKiln", "Charcoal Kiln")], (8, 4))
    recipe("AutumnRetortCharcoal", "Retort Kiln Batches", "CharcoalKiln_Coal", "Charcoal Kiln", kiln_path,
           "Coal", 56, {"Wood": 7, "Steel": 1}, 1, kiln_autumn)

    fishing = unlock("AutumnBaitedNets", "Baited Deep-Water Nets",
                     "Unlocks optional Fishing Harbour recipes. Spend 1 food ration and 1 coal for 5 raw food in 45 working minutes, or 8 raw food at an Advanced Fishing Harbour. Select the recipe at each harbour.",
                     1, 4, autumn["food"], {"Wood": 22, "Steel": 8}, 6,
                     [("[Builders] FH 1_Fishing Harbor", "Fishing Harbour")], (4, 4))
    for key, source, grade, amount in (("BaitedNets", "[Builders]FishingHarbor1", 1, 5),
                                      ("AdvancedBaitedNets", "[Builders]FishingHarbor2", 2, 8)):
        paths = [f"builders/dock_fishing{'v2' if grade == 2 else ''}", f"builders/docks/dockfishingproper_lvl{grade}"]
        recipe(key, "Baited Deep-Water Nets", source, "Fishing Harbour", paths, "Raw Food", amount,
               {"Food Rations": 1, "Coal": 1}, 0.75, fishing)

    for key, title, source, building, path, output, inputs, hours, tier, column, parent, icon in (
        ("AutumnSteamCuredProfiles", "Steam-Cured Profiles", "[Builders] Manufacture Scaffoldings", "Profiles Manufacture",
         "builders/constructionsite/scaffoldingsmanufacture", "Wooden Materials", {"Wood": 12, "Coal": 15}, 1.25,
         0, 8, ("[Builders] GS 0_ScaffoldingManufacture", "Profiles Manufacture"), (3, 6)),
        ("AutumnFuelTemperedExchangers", "Fuel-Tempered Exchangers", "[Builders] Factory Pipe", "Machine Shop",
         "builders/constructionsite/pipefoundry", "Steam Tools", {"Steel": 12, "Coal": 20}, 2,
         1, 18, ("[Builders] GG 1_SteamMill", "Machine Shop"), (10, 2)),
        ("AutumnCharcoalAlloy", "Charcoal-Alloy Composites", "[Builders] ManufactureSteelPlate", "Foundry",
         "builders/constructionsite/metalplateforge", "Steel Plates", {"Steel": 12, "Coal": 70}, 2.5,
         2, 18, ("[Builders] GM 2_SteelPlateForge", "Foundry"), (9, 10)),
    ):
        display = {"Wooden Materials": "structural profile", "Steam Tools": "steam exchanger", "Steel Plates": "steel composite"}[output]
        items = " and ".join(f"{quantity} {name.lower()}" for name, quantity in inputs.items())
        research = unlock(key, title, f"Unlocks an optional {building} recipe. Spend {items} for 1 {display} in {hours:g} working hours at full efficiency. Select it in the building panel.",
                          tier, column, autumn["construction"], {"Wood": 20 + tier * 5, "Steel": 8 + tier * 4},
                          5 + tier, [parent], icon)
        recipe(key, title, source, building, [path], output, 1, inputs, hours, research)

    warehouse = unlock("EdgeWarehouseSalvage", "Warehouse Cutting Torches",
                       "Unlocks an optional Army Warehouse recipe. Spend 10 wood and 20 coal to recover 48 steel in 3 working hours at full efficiency. Select it at the Army Warehouse.",
                       0, 14, tabs["exploration"], {"Wood": 20, "Steel": 6}, 5, [], (8, 0))
    recipe("WarehouseSalvage", "Warehouse Cutting Torches", "[Reconquest]Vault_Steel", "Army Warehouse", ["reconquest/vault"],
           "Steel", 48, {"Wood": 10, "Coal": 20}, 3, warehouse)

    for key, tab, column, parent in (
        ("RapidCoking", tabs["exploration"], 12, ("R 2_CharcoalKiln", "Charcoal Kiln")),
        ("AutumnRapidCoking", autumn["heat"], 8, ("[Builders] RC 2_CharcoalKiln", "Charcoal Kiln")),
    ):
        research = unlock(key, "Rapid Coking Beds",
                          "Unlocks an optional Charcoal Kiln recipe. Spend 14 wood for 56 coal in 30 working minutes at full efficiency. This burns through wood faster to deliver coal quickly when reserves are low.",
                          2, column, tab, {"Wood": 38, "Steel": 20}, 8, [parent], (8, 3))
        recipe(key, "Rapid Coking Beds", "CharcoalKiln_Coal", "Charcoal Kiln", kiln_path,
               "Coal", 56, {"Wood": 14}, 0.5, research)

    fermentation = unlock("FermentationBeds", "Fermentation Beds",
                          "Unlocks ration-fed Hothouse recipes. A Hothouse spends 1 food ration and 1 coal for 5 raw food in 1 working hour. An Industrial Hothouse spends 2 rations and 2 coal for 10 raw food. These conserve coal compared with Coal-Heated Seedbeds and return rations to the growing cycle as a starter.",
                          2, 20, tabs["food"], {"Wood": 36, "Steel": 18}, 8,
                          [("F 2_Plantation", "Hothouse")], (8, 6))
    for key, source, path, building, amount, ration in (
        ("FermentationBeds", "Plantation_Food", "resourceextraction/foodplantation", "Hothouse", 5, 1),
        ("IndustrialFermentationBeds", "SteamPlantation_Food", "resourceextraction/foodplantation_steam", "Industrial Hothouse", 10, 2),
    ):
        recipe(key, "Fermentation Beds", source, building, [path], "Raw Food", amount,
               {"Food Rations": ration, "Coal": ration}, 1, fermentation)

    smokehouses = unlock("AutumnDocksideSmokehouses", "Dockside Smokehouses",
                         "Unlocks direct ration production at Fishing Harbours. Spend 1 wood and 2 coal for 8 standard food rations per working hour, or 12 rations at an Advanced Fishing Harbour. The catch is prepared at the harbour, freeing the Cookhouse crew for other work.",
                         1, 18, autumn["food"], {"Wood": 28, "Steel": 12}, 7,
                         [("[Builders] FH 1_Fishing Harbor", "Fishing Harbour")], (5, 9))
    for key, source, grade, amount in (("DocksideSmokehouses", "[Builders]FishingHarbor1", 1, 8),
                                      ("AdvancedDocksideSmokehouses", "[Builders]FishingHarbor2", 2, 12)):
        paths = [f"builders/dock_fishing{'v2' if grade == 2 else ''}", f"builders/docks/dockfishingproper_lvl{grade}"]
        recipe(key, "Dockside Smokehouses", source, "Fishing Harbour", paths, "Food Rations", amount,
               {"Wood": 1, "Coal": 2}, 1, smokehouses)

    return recipes, targets
