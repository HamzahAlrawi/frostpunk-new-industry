"""Late research using the same typed effect vectors as the source technologies."""
import re
import struct
from automaton_efficiency import ROLE_WORKPLACE_BONUSES, raise_workplace_research, split_workplace_efficiency
from steel_logistics import add_steel_logistics, two_scout_teams


def building_ids(buildings):
    name_records = list(re.finditer(rb"\x01\x01([ -~]+)\x00", buildings))
    category_count = struct.unpack_from("<I", buildings)[0]
    categories = {buildings[m.end():m.end()+16] for m in name_records[:category_count]}
    assert category_count == len(categories) == 11
    places = {m.group(1).decode(): buildings[m.end()+16:m.end()+32]
              for m in name_records[category_count:] if buildings[m.end():m.end()+16] in categories}
    assert len(places) == len(set(places.values())) == 112
    assert places["House"].hex() == "a7377de655c61d9b3745e66c0f2ec651"
    assert places["FaithKeepers"].hex() == "665c8c59b5fddbae3b4621e7b304b8a4"
    return places


def make_mastery(technology, techinfo, original, modified, buildings, resources, category, tabs, guid, loc, u32):
    vanilla = {t["name"]: t for t in techinfo}
    markers = list(re.finditer(rb"\x01Frostpunk[A-Za-z]+Modifier\x00", original))
    assert len(markers) == struct.unpack_from("<I", original)[0]
    by_id = {original[m.end():m.end()+16]: (m, markers[i+1].start() if i+1<len(markers) else len(original))
             for i,m in enumerate(markers)}
    places = building_ids(buildings)
    late_records = []
    unlocks = {}
    titles = {}
    tier_names = {1:"Drawing Boards (I)",2:"Drafting Machines (II)",3:"Mechanical Calculators (III)",
                  4:"Difference Engine (IV)",5:"Automatic Prototyping (V)"}

    def replace_scalar(payload, old, new, *, count=1):
        assert payload.count(old) == count, (old.hex(), count)
        return payload.replace(old, new)

    def floats(*changes):
        def update(payload):
            for old,new in changes:
                payload = replace_scalar(payload, struct.pack("<f",old), struct.pack("<f",new))
            return payload
        return update

    def storage(factor, only=()):
        def update(payload):
            marker = u32(8) + resources["Augmentation parts"]
            assert payload.count(marker) == 1
            start = payload.index(marker)+4
            records = [payload[i:i+24] for i in range(start,start+192,24)]
            assert all(r[16:] == u32(0)+struct.pack("<f",1.5) for r in records)
            ids = {resources[name] for name in only}
            assert ids <= {r[:16] for r in records}
            revised = b"".join(r[:20]+struct.pack("<f",factor if not ids or r[:16] in ids else 1.0) for r in records)
            return payload[:start]+revised+payload[start+192:]
        return update

    def add(key, title, effect, tier, column, wood, steel, hours, source, parents,
            *, target_names=None, place_effect=None, transform=None, icon=None, cores=0, tab=None):
        row = vanilla[source]
        tail = bytes.fromhex(row["rest"])
        assert tail[:4] == u32(2)
        pos = 4

        def read_vector(width):
            nonlocal pos
            count = struct.unpack_from("<I", tail, pos)[0]
            pos += 4
            end = pos + count * width
            assert end <= len(tail)
            values = [tail[i:i+width] for i in range(pos,end,width)]
            pos = end
            return values

        global_ids = read_vector(16)
        site_pairs = read_vector(32)
        extra_pairs = read_vector(32)
        assert len(tail[pos:]) == 25 and tail[pos+4:pos+16] == b"\x01TECH_ENTRY\x00"
        if target_names is not None:
            assert len({pair[16:] for pair in site_pairs})==1 and not global_ids and not extra_pairs
            site_pairs = [places[name] + site_pairs[0][16:] for name in target_names]
        if place_effect is not None:
            assert target_names is None and not global_ids and not extra_pairs
            target,modifier = map(bytes.fromhex, place_effect)
            assert len(target)==16 and by_id[modifier][0].group()==b"\x01FrostpunkPlaceModifier\x00"
            site_pairs = [target+modifier]
        assert global_ids or site_pairs or extra_pairs
        new_ids = {}
        descriptions = set()
        for old_id in dict.fromkeys(global_ids+[p[16:] for p in site_pairs+extra_pairs]):
            marker,end = by_id[old_id]
            start = marker.end()+16
            assert original[start] == 1
            name_end = original.index(0,start+1)
            name = original[start+1:name_end]
            body = original[name_end+1:end]
            if transform:
                body = transform(body)
            if key in ROLE_WORKPLACE_BONUSES:
                assert marker.group()==b"\x01FrostpunkPlaceModifier\x00"
                body = split_workplace_efficiency(body)
            description = effect
            if marker.group()==b"\x01FrostpunkPlaceModifier\x00":
                body, description = raise_workplace_research(body, effect)
            descriptions.add(description)
            body = re.sub(rb"\x01@Generated/ModifiersConfig/Modifiers/[^\x00]+/Display name\x00",
                          lambda _:loc("Modifier/"+key,title), body)
            new_id = guid("mastery/"+key+"/"+old_id.hex())
            new_ids[old_id] = new_id
            late_records.append(marker.group()+new_id+b"\x01NI "+key.encode()+b"/"+name+b"\0"+body)
        globals_new = [new_ids[effect_id] for effect_id in global_ids]
        sites_new = [(p[:16],new_ids[p[16:]]) for p in site_pairs]
        extras_new = [(p[:16],new_ids[p[16:]]) for p in extra_pairs]
        rest = (u32(2)+u32(len(globals_new))+b"".join(globals_new)
                +u32(len(sites_new))+b"".join(a+b for a,b in sites_new)
                +u32(len(extras_new))+b"".join(a+b for a,b in extras_new)+tail[pos:])
        requirements = [tier_names[tier]] if tier else []
        required_ids = []
        for parent in parents:
            if isinstance(parent, tuple):
                internal, display = parent
                required_ids.append(bytes.fromhex(vanilla[internal]["guid"]))
                requirements.append(display)
            else:
                required_ids.append(unlocks[parent])
                requirements.append(titles[parent])
        description, = descriptions
        desc = description + "\n\nRequires: " + (", ".join(requirements) or "No prior research") + "."
        cost = {"Wood":wood}
        if steel:
            cost["Steel"] = steel
        if cores:
            cost["Steam Cores"] = cores
        unlocks[key] = technology(key,title,desc,tier,column,required_ids,cost,hours,
                                  icon or tuple(row["layout"][:2]),tab or category,rest=rest,effects=sites_new,
                                  global_effects=globals_new,extra_effects=extras_new,prerequisite_names=requirements)
        titles[key] = title

    warmth = "R 3_Gathering Insulation"
    house = ("F 4_House","House")
    depot = ("R 2_ResourceDepotUpgrade","Resource Depot Upgrade")
    big_depot = ("R 3_Resource Depot Big","Large Resource Depot")
    insulation = ("F 6_House Insulation","House Insulation")
    add("StormShutters","Storm Shutters","Tents, Bunkhouses, and Houses gain one heat level.",2,2,90,55,16,warmth,
        [("F 2_Bunkhouse","Bunkhouse")],target_names=["Tent","Bunkhouse","House"])
    add("CavityWalls","Cavity Walls","Houses gain another heat level from insulated wall cavities.",3,2,140,95,20,warmth,
        ["StormShutters",house],target_names=["House"])
    add("ThermalVestibules","Thermal Vestibules","Bunkhouses and Houses gain another heat level from sealed entrance chambers.",4,2,210,145,26,warmth,
        ["CavityWalls"],target_names=["Bunkhouse","House"])
    add("DeepHouseLagging","Deep House Lagging","Houses gain another heat level.",5,2,280,230,34,warmth,
        ["ThermalVestibules",insulation],target_names=["House"])
    civic = ["Neighborhood watch tower","Guardpost","Prison","CensusStation","HouseOfPrayer","Temple",
             "FaithKeepers","Shrine","WarmSoup","Mechanical Aggitator","HospitalOfMercy","PublicHouse","FightClube","CareHouse"]
    add("CivicLagging","Civic Coldproofing","Faith, Order, and communal buildings gain one heat level, including Temples, Guard Stations, Prisons, and the House of Healing.",
        4,6,115,80,16,warmth,[("F 3_HealthCare Buildings - warmer","Healthcare Insulation")],target_names=civic)
    add("CitywideLagging","Citywide Thermal Envelope","Adds one insulation level to all city buildings that use insulation, including Faith and Order workplaces.",
        1,6,85,60,14,warmth,[],target_names=list(places))

    add("StackedDepots","Stacked Depot Racks","Both sizes of Resource Depot gain a 45% storage capacity bonus.",2,10,45,25,9,
        "R 2_ResourceDepotUpgrade",[depot],transform=storage(1.45))
    add("ModularWarehouses","Modular Warehousing","Both sizes of Resource Depot gain another 50% capacity bonus.",3,10,80,45,13,
        "R 2_ResourceDepotUpgrade",["StackedDepots",big_depot],transform=storage(1.50))
    add("DeepCoalBins","Deep Coal Bins","Resource Depots gain 55% more capacity when assigned to coal.",4,10,90,55,14,
        "R 2_ResourceDepotUpgrade",["ModularWarehouses"],transform=storage(1.55,("Coal",)))
    add("ProvisionCells","Provision Cells","Resource Depots gain 55% more capacity when assigned to raw food or food rations.",5,10,105,65,16,
        "R 2_ResourceDepotUpgrade",["ModularWarehouses"],transform=storage(1.55,("Raw Food","Food Rations")))

    gen_fuel = "H 5 Generator Upgrade - less coal 2"
    add("GeneratorReheat","Generator Reheat Economiser","The Generator gains a further 15% reduction in coal use.",4,14,125,90,17,
        gen_fuel,[(gen_fuel,"Generator Efficiency Upgrade II")],transform=floats((0.9,0.85)))
    add("GeneratorSeal","Generator Pressure Seals","The Generator gains a further 10% reduction in coal use.",5,14,150,105,20,
        gen_fuel,["GeneratorReheat"],transform=floats((0.9,0.90)))
    safety = "H 6_Generator Upgrade - less stress"
    add("GovernorSafeties","Independent Safety Governors","Generator stress gains a 20% slower buildup modifier and a 15% faster recovery modifier.",
        5,16,235,235,34,safety,[(safety,"Generator Safety Bypass")],transform=floats((0.75,0.80),(1.25,1.15)))

    speed = "E 3_ScoutsSpeed"
    speed2 = "E 6_ScoutsSpeed 2"
    add("ScoutBearings","Cold-Weather Sled Bearings","Scouts gain an extra 65% travel speed bonus.",3,18,65,40,12,
        speed,[(speed,"Lighter Scout Sleds")],transform=floats((1.5,1.65)))
    add("ScoutOverhaul","Frostland Sled Overhaul","Scouts gain another 80% travel speed bonus.",5,18,115,70,17,
        speed2,["ScoutBearings",(speed2,"Boosted Scout Sleds")],transform=floats((1.5,1.80)))
    limit = "E 5_ScoutsLimit2"
    add("BeaconDispatch","Beacon Dispatch Office","The Beacon can dispatch two additional scout teams.",
        4,18,155,125,24,limit,[(limit,"Additional Scouts")],transform=two_scout_teams)
    outpost = "E 5_ExpeditionUpgrade"
    add("ConvoyBearings","Outpost Convoy Bearings","Outpost teams and their resource transports gain an extra 20% travel speed bonus.",
        4,20,90,60,14,outpost,[("E 3_ExpeditionCenter","Outpost Depot")],
        transform=lambda p: floats((1.5,1.20) if struct.pack("<f",1.5) in p else (1.2,1.15))(p))
    add("ConvoyRelays","Frostland Relay Stations","Outpost teams and their resource transports gain another travel speed bonus.",
        5,20,125,85,18,outpost,["ConvoyBearings"],
        transform=lambda p: floats((1.5,1.25) if struct.pack("<f",1.5) in p else (1.2,1.20))(p))

    production = "R 2_Sawmill Upgrade"
    add("ToolLibraries","Industrial Tool Libraries","Sawmills, Wall Drills, and Steelworks gain a 30% production bonus from standardised tooling.",
        3,6,75,40,12,production,[("R 2_Sawmill Upgrade","Sawmill Upgrade")],
        target_names=["Sawmill","SteamSawmill","WallDrill","WallDrillSteam","WallDrillAdvanced",
                      "Iron Ore Mine","SteamIronOreMine","AdvancedOreMine"],transform=floats((1.25,1.30)))
    add("MineLifts","Pneumatic Mine Lifts","All grades of Coal Mine and Steelworks gain a 30% production bonus.",
        4,8,100,65,15,production,["ToolLibraries"],
        target_names=["Coal Mine","SteamCoalMine","AdvancedCoalMine","Iron Ore Mine","SteamIronOreMine","AdvancedOreMine"],
        transform=floats((1.25,1.30)),icon=(8,0))
    add("WorkshopBench","Shared Workshop Benches","Workshops gain a 45% workplace efficiency bonus. The normal city research scaling still applies.",
        2,6,45,25,9,"F 6_Plantation upgrade",[],target_names=["Engineers Lab"],transform=floats((1.15,1.45)),icon=(0,2))
    add("WorkshopSteam","Workshop Steam Jacket","Workshops gain one heat level so they can keep researching in deeper cold.",
        3,8,65,35,11,warmth,["WorkshopBench"],target_names=["Engineers Lab"])
    add("CoalCircuit","Coal Circuit Planning","Coal Thumpers produce piles 25% faster. Gathering Posts still need to collect them.",
        3,12,60,35,10,production,[("R 3_SteamCoalThumper","Steam Coal Thumper")],
        target_names=["CoalThumper","CoalThumperSteam"],icon=(8,3))
    add("IndustrialStorm","Industrial Storm Cladding","Coal Mines, Steelworks, and Wall Drills gain one heat level across all grades.",
        5,8,260,230,32,warmth,["MineLifts"],
        target_names=["Coal Mine","SteamCoalMine","AdvancedCoalMine","Iron Ore Mine","SteamIronOreMine","AdvancedOreMine",
                      "WallDrill","WallDrillSteam","WallDrillAdvanced"])
    add("CitywideLagging2","Citywide Thermal Envelope II",
        "Adds another insulation level to all city buildings that use insulation, including Faith and Order workplaces.",
        3,6,185,135,22,warmth,["CitywideLagging"],target_names=list(places))
    add("CitywideLagging3","Citywide Thermal Envelope III",
        "Adds a third citywide insulation level to buildings that use insulation, including Faith and Order workplaces.",
        5,6,320,240,34,warmth,["CitywideLagging2"],target_names=list(places))
    workshop_source = "F 6_Plantation upgrade"
    workshop = ["Engineers Lab"]
    exploration = tabs["exploration"]
    add("WorkshopSpeed1","Workshop Drafting Stations",
        "Workshops gain a 30% efficiency bonus. Citywide research speed still uses the normal Workshop scaling.",
        0,8,15,5,4,workshop_source,[],target_names=workshop,transform=floats((1.15,1.30)),icon=(0,2),tab=exploration)
    add("WorkshopSpeed2","Workshop Reference Library",
        "Workshops gain a further 30% efficiency bonus.",
        0,12,25,10,6,workshop_source,["WorkshopSpeed1"],target_names=workshop,transform=floats((1.15,1.30)),icon=(0,2),tab=exploration)
    add("WorkshopSpeed3","Workshop Test Rigs",
        "Workshops gain a further 40% efficiency bonus.",
        1,12,40,20,9,workshop_source,["WorkshopSpeed2"],target_names=workshop,transform=floats((1.15,1.40)),icon=(0,2),tab=exploration)
    from early_progression import add_early_upgrades
    add_early_upgrades(add, floats, storage, replace_scalar, tabs)
    from last_autumn import add_autumn_upgrades, add_autumn_expansion
    add_autumn_upgrades(add, floats, storage, places, resources)
    from on_the_edge import add_edge_upgrades
    add_edge_upgrades(add, floats, storage, tabs, category, buildings)
    from mastery_expansion import add_expansion
    add_expansion(add, floats, storage, tabs)
    add_autumn_expansion(add, floats)
    from industry_housing import add_industry_housing
    add_industry_housing(add, floats, storage, tabs)
    add_steel_logistics(add, floats, storage, tabs)
    from opening_progression import add_opening_upgrades
    add_opening_upgrades(add, floats, replace_scalar, tabs)
    from resourceful_upgrades import add_resourceful_upgrades
    add_resourceful_upgrades(add, places, resources, tabs)
    from gameplay_upgrades import add_gameplay_upgrades
    add_gameplay_upgrades(add, floats, places, tabs)
    assert len(unlocks)==180
    return u32(struct.unpack_from("<I",modified)[0]+len(late_records))+b"".join(late_records)+modified[4:]
