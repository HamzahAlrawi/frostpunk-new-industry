"""Curate distinct research effects while retaining existing technology GUIDs.

Only native, previously verified Place/Global modifier fields are written. No
abilities, building component layouts, or save files are changed here.
"""
import hashlib
import re
import struct


REMOVED_TEAMS = frozenset({
    "AutumnExtraForagers", "AutumnForagerRosters", "AutumnForagerWeb",
    "BeaconDispatch", "EdgeFieldTeams", "MasteryScoutDispatch", "OutpostNetworkCharters",
})


def normalized(body):
    return re.sub(rb"\x01@(?:Generated/ModifiersConfig/Modifiers|Mods/NewIndustry/Modifier)/[^\0]+\0", b"\0", body)


def modifiers(data):
    marks = list(re.finditer(rb"\x01Frostpunk([A-Za-z]+)Modifier\0(.{16})", data, re.S))
    assert len(marks) == struct.unpack_from("<I", data)[0]
    result = {}
    for i, match in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(data)
        assert data[match.end()] == 1
        name_end = data.index(0, match.end() + 1, end)
        result[match[2].hex()] = [match[1].decode(), data[match.end() + 1:name_end], data[name_end + 1:end]]
    assert len(result) == len(marks)
    return result


def pack_modifiers(records):
    return struct.pack("<I", len(records)) + b"".join(
        b"\1Frostpunk" + kind.encode() + b"Modifier\0" + bytes.fromhex(guid)
        + b"\1" + name + b"\0" + body for guid, (kind, name, body) in records.items())


def place_scalar_offset(body, offset):
    """Locate scalars after the native optional icon-atlas string.

    A 257-byte Place modifier is not the 238-byte layout plus a trailing safety
    label: safety research includes UI\\Tiles\\Icons.dds at byte 32. Its 19-byte
    expansion shifts the efficiency vectors and every following scalar.
    """
    assert body[25:27] == b'\0\0', 'Normalize the optional display name first'
    shift = 0
    if body[32]:
        atlas = b'\1UI\\Tiles\\Icons.dds\0'
        assert body[32:32+len(atlas)] == atlas, 'Unrecognized Place icon layout'
        shift = len(atlas)-1
    assert len(body) == 238+shift, ('Unrecognized Place body',len(body),shift)
    assert struct.unpack_from('<II',body,76+shift) == (0,2), 'Invalid efficiency vector counts'
    return offset+shift


def effect_signature(tech, records):
    effects = [("global", "", records[g][0], normalized(records[g][2]).hex()) for g in tech.get("global_effects", [])]
    effects += [(kind, target, records[g][0], normalized(records[g][2]).hex())
                for kind in ("effects", "extra_effects") for target, g in tech.get(kind, [])]
    # An empty modifier vector is an unlock, not a duplicate of all other recipes.
    # Recipe-unlock GUIDs are checked independently against their blueprint records.
    if not effects:
        return "unlock:" + tech["guid"]
    return hashlib.sha256(repr(sorted(effects)).encode()).hexdigest()


def curate(specs, data, guid, places, technology_info):
    records = modifiers(data)
    by_id = {tech["id"]: tech for tech in specs}
    changed = set()
    for tech in specs:
        tech.setdefault("global_effects", [])
        tech.setdefault("extra_effects", [])

    def modify(key, changes, *, title=None, description=None):
        tech = by_id[key]
        for effect in dict.fromkeys(g for _, g in tech["effects"]):
            kind, _, raw = records[effect]
            body = bytearray(normalized(raw))
            assert kind == "Place" and len(body) in (238, 257), (key, kind, len(body))
            if any(offset in (84, 88) for offset, _, _ in changes):
                # Role bonuses replace the general efficiency field; do not multiply
                # the old general bonus by a second, newly introduced role bonus.
                struct.pack_into("<f", body, place_scalar_offset(body,72), 1)
            for offset, code, value in changes:
                assert offset in (84, 88, 96, 149, 157, 161, 173, 177, 185)
                struct.pack_into("<" + code, body, place_scalar_offset(body,offset), value)
            records[effect][2] = bytes(body)
        if title:
            tech["title"] = title
        if description:
            tech["description"] = description
        changed.add(key)

    def add_place(key, suffix, names, changes):
        effect = guid("curation/" + key + "/" + suffix).hex()
        body = bytearray(normalized(records["30aa2c27e02dce83494392ae5c1f2261"][2]))
        assert len(body) == 238 and struct.unpack_from("<f", body, 173)[0] == 0.5
        struct.pack_into("<f", body, 173, 1)
        for offset, code, value in changes:
            assert offset in (84, 88, 96, 149, 157, 161, 173, 185)
            struct.pack_into("<" + code, body, offset, value)
        records[effect] = ["Place", ("NI curated/" + key + "/" + suffix).encode(), bytes(body)]
        by_id[key]["effects"] += [(places[name].hex(), effect) for name in names]
        changed.add(key)

    def add_global(key, offset, value):
        assert offset in (69, 166)
        effect = guid("curation/" + key + "/global").hex()
        body = bytearray(normalized(records["d87b131d3367ed86d04efc1f7c1f7a5a"][2]))
        assert len(body) == 186
        assert abs(struct.unpack_from("<f", body, 150)[0] - 0.1) < 1e-6
        struct.pack_into("<f", body, 150, 0)
        struct.pack_into("<f", body, offset, value)
        records[effect] = ["Global", ("NI curated/" + key).encode(), bytes(body)]
        by_id[key]["global_effects"].append(effect)
        changed.add(key)

    # Retain definitions and IDs for old saves, but make their added capacity zero.
    for key in sorted(REMOVED_TEAMS):
        modify(key, [(177, "i", 0)], description="Retired. This mod no longer adds expedition team slots.")
    relay = by_id["AutumnRelayMarkers"]
    relay["requires"] = [by_id["AutumnForagerSleds"]["guid"] if g == by_id["AutumnExtraForagers"]["guid"] else g
                         for g in relay["requires"]]

    modify("GatheringHeat3", [(96, "i", 2), (157, "f", 1.25)], title="Enclosed Collection Networks",
           description="Gathering Posts gain +2 insulation and 25% more collection radius. Reach scattered piles without opening another exposed post.")
    modify("WorkshopSteam", [(96, "i", 2), (88, "f", 2)], title="Automated Design Chambers",
           description="Workshops gain +2 insulation. Automatons working in Workshops gain an additional 100% workplace efficiency; human research efficiency is unchanged.")
    modify("IndustrialHeat", [(96, "i", 2), (84, "f", 1.75), (88, "f", 1.75)], title="Hot Rolling Halls",
           description="All grades of Steelworks gain +2 insulation and 75% workplace efficiency for human crews and automatons.")
    modify("CoalMineHeat", [(96, "i", 2), (84, "f", 1.75), (88, "f", 1.75)], title="Pressurised Mine Cabins",
           description="All grades of Coal Mine gain +2 insulation and 75% workplace efficiency for human crews and automatons.")
    modify("MedicalHeat4", [(96, "i", 2)], title="Sealed Healthcare Districts",
           description="Buildings covered by Healthcare Insulation III gain +2 insulation. Medical Posts and Infirmaries also gain 100% healing efficiency.")
    add_place("MedicalHeat4", "recovery", ["Medical Post", "Ambulatorium"], [(84, "f", 2), (88, "f", 2)])
    modify("CookhouseHeat2", [(96, "i", 2), (84, "f", 1.75), (88, "f", 1.75)], title="Steam-Jacketed Kitchens",
           description="Cookhouses gain +2 insulation and 75% workplace efficiency for human crews and automatons. This accelerates every available ration recipe.")
    modify("HothouseHeat4", [(96, "i", 2), (84, "f", 1.75), (88, "f", 1.75)], title="Winter Conservatories",
           description="Both Hothouse grades gain +2 insulation and 75% workplace efficiency for human crews and automatons, including alternate growing recipes.")
    modify("MedicalEfficiency2", [(173, "f", 0.5)], title="Medical Post Triage",
           description="Medical Posts gain 75% healing efficiency for human crews and automatons. Radical Treatment amputation risk is halved while that law is active.")
    modify("WardProtocols", [(84, "f", 2), (88, "f", 2), (96, "i", 1)], title="Infirmary Recovery Suites",
           description="Infirmaries gain 100% healing efficiency for human crews and automatons, plus +1 insulation. Faster recovery frees beds sooner.")
    modify("SeedSelection2", [(84, "f", 2.25), (88, "f", 2.25)], title="High-Yield Seed Banks",
           description="Both Hothouse grades gain 125% workplace efficiency for human crews and automatons. Applies to every growing recipe.")
    modify("MasteryIrrigation", [(96, "i", 1)], title="Warm-Water Irrigation",
           description="Both Hothouse grades gain 75% workplace efficiency for human crews and automatons and +1 insulation, supporting food production during cold snaps.")
    modify("HuntingSleds", [(161, "i", 6)], title="Frostland Game Logistics",
           description="Hunters' Huts and Hunters' Hangars bring home 6 additional raw food per hunt at full staffing. The logistics upgrade follows hunters into either building grade.")
    add_place("HuntingSleds", "hangars", ["Flying Hunter's Hut"], [(161, "i", 6)])
    # These upgrades retain their original native consumption/output fields.
    def replace_float(key, before, after, description, *, count=1):
        tech = by_id[key]
        ids = tech["global_effects"] + [g for field in ("effects", "extra_effects") for _, g in tech[field]]
        assert ids, key
        for effect in dict.fromkeys(ids):
            body = records[effect][2]
            needle = struct.pack("<f", before)
            assert body.count(needle) == count, (key, before, body.count(needle))
            records[effect][2] = body.replace(needle, struct.pack("<f", after))
        by_id[key]["description"] = description
        changed.add(key)
    replace_float("HubReturnLines", 0.85, 0.70, "Steam Hubs use 30% less coal, preserving heat coverage. A late-game improvement over basic pipe lagging.")
    replace_float("GeneratorDraught", 0.80, 0.70, "The Generator uses 30% less coal at every power and range setting. Starter Generator Grates remain a separate earlier improvement.")
    replace_float("MasterySteelFeeders", 1.30, 1.45, "All three Steelworks grades gain 45% more steel output through continuous feed handling.")
    replace_float("CoalCircuit", 1.25, 1.75, "Both Coal Thumper grades produce coal piles 75% faster. Gathering Posts gain 25% collection radius, easing the collection bottleneck around thumpers.")
    add_place("CoalCircuit", "collection", ["GatheringPost"], [(157, "f", 1.25)])
    add_global("CitywideLagging2", 166, 0.75)
    by_id["CitywideLagging2"]["description"] = "All buildings that use insulation gain +1 insulation. Citizens also have a 25% lower chance of illness caused by cold, protecting travel between heated buildings."
    add_global("CitywideLagging3", 69, 1.25)
    by_id["CitywideLagging3"]["description"] = "All buildings that use insulation gain +1 insulation. Every heat zone also gains 25% radius, extending Generator, Steam Hub and Brazier coverage where present."
    add_place("HouseInsulatedFloors", "bunkhouses", ["Bunkhouse"], [(96, "i", 1)])
    by_id["HouseInsulatedFloors"]["title"] = "District Underfloor Heating"
    by_id["HouseInsulatedFloors"]["description"] = "Houses and Bunkhouses gain +1 insulation. Keep older residential districts viable alongside fully upgraded Houses."

    for prefix in ("", "Autumn"):
        modify(prefix + "WorkshopSpeed2", [(84, "f", 2), (88, "f", 2)],
               description="Workshops gain 100% workplace efficiency for human researchers and automatons. Normal citywide Workshop research scaling still applies.")
        modify(prefix + "WorkshopSpeed3", [(84, "f", 2.25), (88, "f", 2.25), (96, "i", 1)],
               description="Workshops gain 125% workplace efficiency for human researchers and automatons, plus +1 insulation. Normal citywide Workshop research scaling still applies.")
    modify("WorkshopBench", [(84, "f", 2.5), (88, "f", 2.5)], title="Collaborative Design Bureau",
           description="Workshops gain 150% workplace efficiency for human researchers and automatons. Normal citywide Workshop research scaling still applies.")

    modify("AutumnDockRosters", [(84, "f", 2), (88, "f", 2), (96, "i", 1)], title="All-Weather Dock Rosters",
           description="All Dock grades gain 100% unloading efficiency and +1 insulation, improving throughput while preparing the port for the freeze.")
    add_place("AutumnPortClearing", "collection", ["GatheringPost"], [(157, "f", 1.25)])
    by_id["AutumnPortClearing"]["title"] = "Dockside Collection Routes"
    by_id["AutumnPortClearing"]["description"] = "All Dock grades gain 75% unloading efficiency. Gathering Posts gain 25% collection radius to collect dockside piles more easily before Reloading Stations are available."
    modify("AutumnHeavyCargo", [(84, "f", 2), (88, "f", 2), (96, "i", 1)], title="Sheltered Cargo Gantries",
           description="All Reloading Station grades gain 100% gathering efficiency and +1 insulation, combining heavy handling with cold protection.")
    modify("AutumnCraneRigging", [(84, "f", 2.25), (88, "f", 2.25), (185, "i", 1)], title="Interlocked Crane Rigging",
           description="All Reloading Station grades gain 125% gathering efficiency and +1 workplace safety. Faster machinery no longer needs to sacrifice safe handling.")
    modify("AutumnSeasonalFishing", [(84, "f", 2), (88, "f", 2)], title="Seasonal Catch Planning",
           description="Both Fishing Harbour grades gain 100% fishing efficiency, accelerating every available catch or ration recipe.")
    add_place("AutumnNetCrews", "kitchens", ["Food Processing"], [(84, "f", 1.75), (88, "f", 1.75)])
    by_id["AutumnNetCrews"]["title"] = "Harbour-to-Kitchen Crews"
    by_id["AutumnNetCrews"]["description"] = "Fishing Harbours and Cookhouses gain 75% workplace efficiency. Processing capacity grows alongside the catch so raw food does not queue at the kitchens."
    modify("AutumnColdwaterNets", [(84, "f", 2.25), (88, "f", 2.25), (96, "i", 1)], title="Coldwater Trawling Gear",
           description="Both Fishing Harbour grades gain 125% fishing efficiency and +1 insulation. Applies to standard fishing and alternate harbour recipes.")
    modify("AutumnFabricationSafety", [(185, "i", 2), (96, "i", 1)], title="Protected Fabrication Halls",
           description="Profiles Manufactures, Machine Shops and Foundries gain +2 workplace safety and +1 insulation, making high-output component production safer and more weather resistant.")
    modify("AutumnEmergencyWards", [(84, "f", 2.25), (88, "f", 2.25), (96, "i", 1)], title="Emergency Recovery Wards",
           description="Medical Posts and Infirmaries gain 125% healing efficiency and +1 insulation, providing a distinct emergency-care improvement over routine medical rotas.")
    modify("EdgeWarehouseWinches", [(84, "f", 2.25), (88, "f", 2.25), (96, "i", 1)], title="Enclosed Warehouse Winches",
           description="The Army Warehouse gains 125% workplace efficiency and +1 insulation. Applies to its steel, Steam Core, and salvage recipes.")
    modify("EdgeCoalCrews", [(84, "f", 2), (88, "f", 2), (96, "i", 1)], title="Heated Coal-Mine Crews",
           description="All Coal Mine grades gain 100% workplace efficiency for human crews and automatons, plus +1 insulation.")

    # Move transient-resource and exploration improvements into the period when
    # those resources and destinations are still useful. Change the real tier
    # requirement and prerequisite GUIDs as well as the displayed row and price.
    vanilla = {t['name']:t for t in technology_info}
    tiers = {vanilla[n]['guid'] for n in ('01_TierUnlock 1','02_TierUnlock2','03_TierUnlock3','04_TierUnlock4','05_TierUnlock5')}
    tier_ids = {i:vanilla[n]['guid'] for i,n in enumerate(('01_TierUnlock 1','02_TierUnlock2','03_TierUnlock3','04_TierUnlock4','05_TierUnlock5'),1)}
    timings = {
        'GatheringLogistics':(1,26,10,6,['R 1_Gathering Upgrade']),
        'SawmillOutput2':(1,28,10,6,['R 1_Sawmill']),
        'SawmillSurvey':(0,25,8,5,['R 1_Sawmill']),
        'HuntingSleds':(1,28,12,6,['HuntingTrails']),
        'FlightRigs':(3,55,30,10,['F 3_Flying Hunters']),
        'ScoutBearings':(2,40,22,8,['E 3_ScoutsSpeed']),
        'ScoutOverhaul':(3,65,40,12,['ScoutBearings']),
        'ConvoyBearings':(2,40,22,8,['E 3_ExpeditionCenter']),
        'ConvoyRelays':(3,65,40,12,['ConvoyBearings']),
        'MedicalHeat3':(3,65,35,10,['F 3_HealthCare Buildings - warmer']),
        'HothouseHeat3':(3,65,35,10,['F 2_Plantation']),
        'WardProtocols':(3,65,35,10,['F 3_Steam healthcare']),
        'SeedSelection2':(3,70,40,12,['CropRotation']),
        'GatheringHeat3':(3,65,35,10,['R 3_Gathering Insulation']),
        'MiningCoreMounts':(2,45,30,8,['R 2_Coal Mine']),
        'DeepScrapRecovery':(2,40,25,7,['ScrapRecovery']),
    }
    for key,(tier,wood,steel,hours,parents) in timings.items():
        tech=by_id[key]
        tech['previous_tier']=tech['tier']
        tech['tier']=tier;tech['cost']={'Wood':wood,'Steel':steel};tech['hours']=hours
        tech['requires']=([tier_ids[tier]] if tier else [])+[
            by_id[p]['guid'] if p in by_id else vanilla[p]['guid'] for p in parents]
        assert not (set(tech['requires']) & tiers - {tier_ids.get(tier)})
        changed.add(key)
    by_id['CoalReserveBins']['requires']=[by_id['CoalStorageCompactors']['guid'] if g==by_id['DepotShelving']['guid'] else g
                                        for g in by_id['CoalReserveBins']['requires']]
    changed.add('CoalReserveBins')
    modify('GatheringLogistics',[(149,'f',1.75),(157,'f',1.25)],title='Collection Relay Depots',
           description='Gathering Posts collect resources 75% faster and gain 25% collection radius. Available early enough to help clear starting piles and later supply Coal Thumpers.')
    modify('SawmillOutput2',[(149,'f',1.5),(96,'i',1)],title='Cold-Weather Sawmill Tooling',
           description='Both Sawmill grades produce 50% more wood and gain +1 insulation. An early upgrade for extracting timber before nearby trees run out.')
    modify('SawmillSurvey',[(157,'f',1.5),(96,'i',1)],title='Extended Timber Surveys',
           description='Both Sawmill grades gain 50% cutting radius and +1 insulation. Reach more trees from each site during the opening days.')
    modify('FlightRigs',[(161,'i',20)],title='Heavy-Lift Hunting Rigs',
           description="Hunters' Hangars bring home 20 additional raw food per hunt at full staffing. Available in the middle game while Frostland food still matters.")

    # Late-game engineering should solve storm-scale throughput and reserve
    # problems, rather than sell a small opening-game bonus at a high-tier price.
    modify('IndustrialStorm',[(96,'i',3),(84,'f',2),(88,'f',2)],title='Stormproof Industrial Districts',
           description='All grades of Coal Mine, Steelworks and Wall Drill gain +3 insulation and 100% workplace efficiency for human crews and automatons. A major retrofit for sustained production in extreme cold.')
    modify('CoalMineOutput3',[(84,'f',2.5),(88,'f',2.5)],title='Deep-Seam Extraction Systems',
           description='Every Coal Mine grade gains 150% workplace efficiency for human crews and automatons, supporting large endgame heating networks.')
    modify('DrillOutput',[(149,'f',2),(96,'i',1)],title='Deep-Wall Pressure Drilling',
           description='All Wall Drill grades produce 100% more wood and gain +1 insulation, sustaining late-game expansion after sawmill forests are exhausted.')
    modify('SteelOutput',[(149,'f',2.25),(96,'i',1)],title='High-Pressure Steel Refining',
           description='All Steelworks grades produce 125% more steel and gain +1 insulation, supplying core fabrication and major industrial expansion.')
    modify('ThumperOutput2',[(149,'f',2)],title='Balanced Coal Production Lines',
           description='Both Coal Thumper grades produce piles 100% faster. Gathering Posts also collect resources 100% faster, expanding both sides of the coal supply chain.')
    add_place('ThumperOutput2','collection',['GatheringPost'],[(149,'f',2)])
    replace_float('ToolLibraries',1.30,1.75,'Sawmills, Wall Drills and Steelworks produce 75% more resources across all grades, sharing an upgraded industrial tooling network.')
    replace_float('MineLifts',1.30,1.75,'Every Coal Mine and Steelworks grade produces 75% more resources through high-capacity industrial lifts.')
    replace_float('MasteryWorksNetwork',1.35,2.0,'Every Sawmill, Steelworks, Coal Mine and Wall Drill grade produces 100% more resources. This late-game network supports permanent high-volume industry.')
    replace_float('ModularWarehouses',1.50,2.0,'Both Resource Depot sizes gain 100% storage capacity for every supported resource.',count=8)
    replace_float('DeepCoalBins',1.55,2.5,'Both Resource Depot sizes gain 150% more coal capacity, providing a substantial reserve for prolonged storms.')
    replace_float('CoalReserveBins',1.60,2.0,'Both Resource Depot sizes gain 100% more coal capacity. Build a substantial heating reserve before the final storm.')
    replace_float('ProvisionCells',1.55,3.0,'Both Resource Depot sizes gain 200% more raw-food and food-ration capacity for prolonged supply interruptions.',count=2)
    replace_float('GeneratorReheat',0.85,0.65,'The Generator uses 35% less coal at every power and range setting, supporting sustained high-output heating.')
    replace_float('GeneratorSeal',0.90,0.60,'The Generator uses 40% less coal at every power and range setting. A substantial final-tier improvement for permanent high-power heating.')
    replace_float('GovernorSafeties',0.80,0.50,'Generator stress builds 50% more slowly and recovers 50% faster, making overdrive a practical storm-management tool.')
    replace_float('GovernorSafeties',1.15,1.50,by_id['GovernorSafeties']['description'])
    modify('CivicLagging',[(96,'i',2)],title='Civic Storm Shelters',
           description='Faith, Order and communal buildings gain +2 insulation, including Temples, Guard Stations, Prisons, Care Houses and Houses of Healing. Sustain essential civic services during extreme cold.')
    source=by_id['AutumnBulkStockyards']['effects'][0][1]
    stockyard=normalized(records[source][2]);needle=struct.pack('<f',1.6)
    assert stockyard.count(needle)==3
    for effect in {g for _,g in by_id['StackedDepots']['effects']}:
        records[effect][2]=stockyard.replace(needle,struct.pack('<f',1.75))
    by_id['StackedDepots']['title']='Industrial Stockyard Racks'
    by_id['StackedDepots']['description']='Both Resource Depot sizes gain 75% more coal, wood and steel capacity. Reserve space for industrial inputs without expanding food storage.'
    changed.add('StackedDepots')

    def copy_effects(key,source,changes):
        mapping={}
        for field in ('global_effects','effects','extra_effects'):
            for value in by_id[source][field]:
                old=value if field=='global_effects' else value[1]
                if old not in mapping:
                    kind,_,body=records[old]
                    body=normalized(body)
                    for before,after in changes:
                        needle=struct.pack('<f',before)
                        assert body.count(needle)==1,(key,source,before)
                        body=body.replace(needle,struct.pack('<f',after))
                    new=guid('curation/'+key+'/'+source+'/'+old).hex()
                    records[new]=[kind,('NI curated/'+key+'/'+source).encode(),body]
                    mapping[old]=new
                by_id[key][field].append(mapping[old] if field=='global_effects' else (value[0],mapping[old]))
        changed.add(key)
    copy_effects('GeneratorReheat','MasteryOverdriveRecovery',[(1.2,1.3)])
    by_id['GeneratorReheat']['description']='The Generator uses 35% less coal at every power and range setting. Generator stress also recovers 30% faster, improving recovery between overdrive periods.'
    copy_effects('GeneratorSeal','MasteryOverdriveValves',[(0.85,0.75),(1.15,1.0)])
    by_id['GeneratorSeal']['description']='The Generator uses 40% less coal at every power and range setting. Stress builds 25% more slowly, supporting sustained high-power heating and longer overdrive use.'
    replace_float('SteelworksContinuousCasting',1.45,2.0,'All Steelworks grades produce 100% more steel. Resource Depots also gain 100% steel capacity, giving the increased output somewhere to go.')
    # Clone the already supported, steel-only storage vector rather than creating
    # a new serialization layout or writing offsets into its variable-size body.
    storage_ids={}
    for target,old in by_id['SteelworksIngotRacks']['effects']:
        if old not in storage_ids:
            kind,_,body=records[old];needle=struct.pack('<f',1.8)
            assert kind=='Place' and body.count(needle)==1
            new=guid('curation/SteelworksContinuousCasting/storage/'+old).hex()
            records[new]=[kind,b'NI curated/ContinuousCasting/storage',body.replace(needle,struct.pack('<f',2))]
            storage_ids[old]=new
        by_id['SteelworksContinuousCasting']['effects'].append((target,storage_ids[old]))
    return pack_modifiers(records), changed


def rebuild_entries(specs, entries, technology_info, loc, req, costs):
    """Rebuild the same native entry schema after effects and layout are final."""
    native_titles = {}
    # Callers can provide localized native titles without redistributing the table.
    for row in technology_info:
        native_titles[row["guid"]] = row.get("title", row["name"])
    titles = native_titles | {t["guid"]: t["title"] for t in specs}
    for i, (tech, original) in enumerate(zip(specs, entries)):
        display = re.search(rb"\x01@Mods/NewIndustry/Tech/[^\0]+/Name\0", original)
        assert display
        position = display.start()
        for _ in range(3):
            assert original[position] == 1
            position = original.index(0, position + 1) + 1
        icon = struct.unpack_from("<2i", original, position)
        count, = struct.unpack_from("<I", original, position + 32)
        rest = original[position + 40 + count * 20:]
        assert rest[:4] == struct.pack("<I", 2)
        trailer = rest[-25:]
        assert trailer[4:16] == b"\1TECH_ENTRY\0"
        effects = (struct.pack("<II", 2, len(tech["global_effects"]))
                   + b"".join(bytes.fromhex(g) for g in tech["global_effects"]))
        for key in ("effects", "extra_effects"):
            effects += struct.pack("<I", len(tech[key])) + b"".join(bytes.fromhex(p + e) for p, e in tech[key])
        required_titles = [titles[g] for g in tech["requires"]]
        tech["prerequisite_names"] = required_titles
        description = tech["description"].split("\n\nRequires:")[0]
        tech["description"] = description + "\n\nRequires: " + (", ".join(required_titles) or "No prior research") + "."
        tech["icon"] = list(icon)
        entry = b"\1FrostpunkTechnologyEntry\0\1NI " + tech["id"].encode() + b"\0" + bytes.fromhex(tech["guid"]) + b"\1"
        entry += struct.pack("<I", len(tech["requires"])) + b"".join(req(bytes.fromhex(g)) for g in tech["requires"]) + bytes(4)
        for field, suffix in (("title", "Name"), ("description", "Description"), ("description", "Short")):
            entry += loc("Tech/" + tech["id"] + "/" + suffix, tech[field])
        entry += struct.pack("<4i", *icon, tech["column"], tech["tier"] * 2) + bytes.fromhex(tech["category"])
        entries[i] = entry + costs(tech["cost"]) + struct.pack("<f", tech["hours"]) + effects + trailer
