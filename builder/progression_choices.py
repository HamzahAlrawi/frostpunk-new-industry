"""Specialist research and production choices using verified native schemas."""
import struct

from city_mastery import building_ids
from last_autumn import AUTUMN_TABS, construction_cost_transform
from research_curation import modifiers, normalized, pack_modifiers, place_scalar_offset
from station_recipes import encode_station_recipe, native_production_recipes, string, uint


COLD = ('TechHaven','Winterhome','Default','Default_Endless_Builders','Default_Endless','Refugees','Reconquest')
GENERATOR = tuple(name for name in COLD if name != 'Reconquest')
GROWING = GENERATOR
AUTUMN = ('Builders',)
VERSION = '3.9.0'


def add_choices(technology, specs, techinfo, data, buildings, blueprints, resources,
                guid, localize, costs, requirement, negate, tabs, previous_recipes):
    records = modifiers(data)
    places = building_ids(buildings)
    native = {t['name']:t for t in techinfo}
    existing = {t['id']:t for t in specs}
    additions = []
    recipes = []
    targets = {}
    source_recipes = native_production_recipes(blueprints)
    neutral = bytearray(normalized(records['30aa2c27e02dce83494392ae5c1f2261'][2]))
    assert len(neutral) == 238 and struct.unpack_from('<f',neutral,173)[0] == 0.5
    struct.pack_into('<f',neutral,173,1)
    neutral = bytes(neutral)
    trailer = bytes.fromhex(techinfo[0]['rest'])[-25:]

    def effect(key, kind, body, suffix='main'):
        g = guid('choices/'+key+'/'+suffix).hex()
        assert g not in records
        records[g] = [kind,('NI choices/'+key+'/'+suffix).encode(),body]
        return g

    def place(key, names, changes, suffix='main'):
        body = bytearray(neutral)
        for offset, code, value in changes:
            assert offset in (84,88,96,149,157,161,173,185)
            struct.pack_into('<'+code,body,place_scalar_offset(body,offset),value)
        g = effect(key,'Place',bytes(body),suffix)
        return [(places[name].hex(),g) for name in names]

    def from_technology(key, source, changes=()):
        """Copy complete native effect vectors, including heater conditions."""
        rest = bytes.fromhex(native[source]['rest']);position=4;vectors=[];mapping={}
        for width in (16,32,32):
            n,=struct.unpack_from('<I',rest,position);position+=4;values=[]
            for _ in range(n):
                value=rest[position:position+width];position+=width
                old=value[-16:].hex()
                if old not in mapping:
                    kind,_,body=records[old]
                    for before,after in changes:
                        needle=struct.pack('<f',before)
                        assert body.count(needle)==1,(key,source,before)
                        body=body.replace(needle,struct.pack('<f',after))
                    mapping[old]=effect(key,kind,body,old)
                values.append(mapping[old] if width==16 else (value[:16].hex(),mapping[old]))
            vectors.append(values)
        assert vectors[0] or vectors[1] or vectors[2]
        return vectors

    def reserve(key, name, factors):
        row=native['R 2_ResourceDepotUpgrade'];rest=bytes.fromhex(row['rest'])
        assert rest[:8]==uint(2)+uint(0) and struct.unpack_from('<I',rest,8)[0]==2
        source=rest[28:44].hex();kind,_,body=records[source]
        marker=uint(8)+resources['Augmentation parts'];assert body.count(marker)==1
        start=body.index(marker)+4;assert kind=='Place'
        expected={resources[n]:factor for n,factor in factors.items()}
        seen=set();updated=[]
        for position in range(start,start+8*24,24):
            record=body[position:position+24]
            assert record[16:]==uint(0)+struct.pack('<f',1.5)
            seen.add(record[:16]);updated.append(record[:20]+struct.pack('<f',expected.get(record[:16],1)))
        assert set(expected)<=seen
        body=body[:start]+b''.join(updated)+body[start+8*24:]
        return [(places[name].hex(),effect(key,'Place',body))]

    def coreless(key):
        kind,_,body=records['3c76b6fed8535ab7ba42279f732c57db']
        assert kind=='Global'
        body=construction_cost_transform(places,resources,['Ambulatorium'],{'Steam Cores':1})(body)
        return [effect(key,kind,body)]

    def add(key,title,description,tier,wood,steel,hours,parents,scenarios,tab,
            *,sites=(),globals_=(),extras=(),icon=(0,2),mechanic):
        parents=[bytes.fromhex(existing[p]['guid'] if p in existing else native[p]['guid']) for p in parents]
        rest=uint(2)+uint(len(globals_))+b''.join(bytes.fromhex(g) for g in globals_)
        for values in (sites,extras):
            rest+=uint(len(values))+b''.join(bytes.fromhex(p+g) for p,g in values)
        rest+=trailer
        category=AUTUMN_TABS['construction'] if scenarios==AUTUMN else tabs['exploration']
        research=technology(key,title,description,tier,2,parents,{'Wood':wood,'Steel':steel},hours,
                            icon,category,rest=rest,prerequisite_names=[])
        spec=specs[-1]
        spec.update(scenarios=list(scenarios),preferred_tab=tab,mechanic=mechanic,added_in=VERSION)
        existing[key]=spec;additions.append(key)
        return research

    def recipe(key,title,source,building,paths,output,amount,inputs,hours,research):
        record=encode_station_recipe(source_recipes,key,title,source,building,paths,output,amount,
                                     inputs,hours,research,resources,guid,localize,costs,requirement)
        recipes.append(record)
        for path in paths:
            targets.setdefault('gameentities/buildings/'+path+'.binarytemplate',[]).append(record[0])

    def supersede(old_key,new_research):
        for i,(recipe_id,raw,info) in enumerate(previous_recipes):
            if info['id']!=old_key:continue
            prefix=b'\1'+string('NI '+old_key)+recipe_id
            assert raw.startswith(prefix)
            position=len(prefix);assert raw[position:position+4]==uint(1)
            end=position+4+len(requirement(bytes.fromhex(info['unlock'])))
            assert raw[position+4:end]==requirement(bytes.fromhex(info['unlock']))
            raw=raw[:position]+uint(2)+raw[position+4:end]+negate(new_research)+raw[end:]
            info=dict(info,excludes=[new_research.hex()])
            previous_recipes[i]=(recipe_id,raw,info)
            return
        raise AssertionError(('Missing predecessor recipe',old_key))

    # Raw-food conservation competes with fuel use and kitchen throughput.
    for key,scenarios in [('SlowSimmeredBroth',COLD),('AutumnSlowSimmeredBroth',AUTUMN)]:
        tradeoff=('Conserves raw food but uses more coal and kitchen time than Fuelled Stockpots.' if scenarios==COLD else
                  'Conserves raw food at the cost of coal and Cookhouse throughput.')
        research=add(key,'Slow-Simmered Broth',
            'Unlocks an optional Cookhouse recipe: 2 raw food and 6 coal become 8 standard rations in 30 working minutes. '+tradeoff+' Choose the recipe in the Cookhouse.',
            0,16,5,4,[],scenarios,2,icon=(5,9),mechanic='ration-fuel-trade')
        recipe(key,'Slow-Simmered Broth','Canteen_FoodRations_standard','Cookhouse',
               ['resourceprocessing/foodprocessing'],'Food Rations',8,{'Raw Food':2,'Coal':6},0.5,research)

    stress,_,_=from_technology('BoilerBufferDrums','H 6_Generator Upgrade - less stress',[(0.75,0.5),(1.25,1)])
    _,_,fuel=from_technology('BoilerBufferDrums','H 3_Generator Upgrade - less coal',[(0.9,1.2)])
    add('BoilerBufferDrums','Pressure-Buffer Boiler Drums',
        'Generator stress builds 50% more slowly. Trade-off: the Generator burns 20% more coal at every power and range setting, including when overdrive is off. Optional permanent specialisation for longer overdrive use.',
        0,24,10,5,[],GENERATOR,0,globals_=stress,extras=fuel,icon=(1,6),mechanic='overdrive-fuel-trade')

    for key,scenarios,parent in [('LimbSparingSurgery',COLD,'ConservativeSurgery'),
                                 ('AutumnLimbSparingSurgery',AUTUMN,'AutumnConservativeSurgery')]:
        add(key,'Limb-Sparing Surgery',
            'Medical Posts no longer cause amputations through Radical Treatment. The Radical Treatment law must be active; this does not prevent injuries, illness or deaths from other causes. An alternative to making every clinic an Infirmary.',
            2,48,24,9,[parent],scenarios,2,sites=place(key,['Medical Post'],[(173,'f',0)]),
            icon=(4,9),mechanic='radical-treatment-amputation-prevention')

    for key,scenarios,tier,parent in [('FieldInfirmaries',COLD,3,'F 3_Steam healthcare'),
                                     ('AutumnFieldInfirmaries',AUTUMN,3,'[Builders] FM 3_Steam healthcare')]:
        add(key,'Core-Free Field Infirmaries',
            'Infirmaries cost one fewer Steam Core to construct, removing their core requirement. Wood and steel costs stay the same. Expand advanced medical care without diverting cores from food production or industry.',
            tier,58,32,10,[parent],scenarios,2,globals_=coreless(key),icon=(4,9),mechanic='core-free-infirmaries')

    for key,scenarios,tier,parent in [('CondensateHeaters',COLD,4,'H 4_Boiler Upgrade - less coal'),
                                     ('AutumnCondensateHeaters',AUTUMN,2,'[Builders] HH 2_Heater')]:
        globals_,sites,extras=from_technology(key,'H 4_Boiler Upgrade - less coal')
        for g in {g for _,g in extras}:
            kind,_,body=records[g]
            assert kind=='Place' and body.count(resources['Coal'])==1
            position=body.index(resources['Coal'])+16
            assert body[position:position+8]==struct.pack('<2f',-1,1)
            # Use a positive multiplier, rather than subtracting another unit
            # from low-power heaters that already consume zero coal.
            records[g][2]=body[:position]+struct.pack('<2f',0,0.5)+body[position+8:]
        add(key,'Condensate-Recovery Heaters',
            'Active Heaters use 50% less coal while retaining their full heat output. Works alongside the native Heater Efficiency Upgrade, reducing the cost of dispersed, high-power workplace heating.',
            tier,70 if tier==4 else 38,45 if tier==4 else 20,12 if tier==4 else 8,[parent],scenarios,0,
            globals_=globals_,sites=sites,extras=extras,icon=(7,7),mechanic='conditional-heater-fuel-saving')

    for key,scenarios,tier,predecessor in [('ClosedCycleRetorts',COLD,4,'RetortCharcoal'),
                                         ('AutumnClosedCycleRetorts',AUTUMN,3,'AutumnRetortCharcoal')]:
        research=add(key,'Closed-Cycle Pyrolysis',
            'Upgrades the Retort Kiln recipe: 4 wood and 8 coal produce 96 coal in 2 working hours. Net gain: 88 coal. Sacrifices throughput to conserve wood; Rapid Coking remains available for fast production. Replaces Retort Kiln Batches in the recipe selector.',
            tier,80 if tier==4 else 48,50 if tier==4 else 25,13 if tier==4 else 9,[predecessor],scenarios,3 if scenarios!=AUTUMN else 1,
            icon=(8,4),mechanic='wood-saving-retort-replacement')
        supersede(predecessor,research)
        recipe(key,'Closed-Cycle Pyrolysis','CharcoalKiln_Coal','Charcoal Kiln',['resourceprocessing/charcoalkiln'],
               'Coal',96,{'Wood':4,'Coal':8},2,research)

    research=add('CoreChargedRetorts','Core-Charged Furnace Batches',
        'Unlocks an optional Charcoal Kiln recipe: 20 wood and 1 Steam Core produce 1200 coal in 4 working hours. The core is consumed in every batch. Turns renewable core manufacturing into a high-throughput fuel supply; ordinary kiln recipes remain available.',
        5,140,115,20,['Cores3','ClosedCycleRetorts'],COLD,1,icon=(8,4),mechanic='steam-core-to-fuel-chain')
    recipe('CoreChargedRetorts','Core-Charged Furnace Batches','CharcoalKiln_Coal','Charcoal Kiln',
           ['resourceprocessing/charcoalkiln'],'Coal',1200,{'Wood':20,'Steam Cores':1},4,research)

    research=add('ArtificialSpring','Artificial Spring Cultivation',
        'Unlocks Hothouse burst-growing recipes. A Hothouse spends 1 Steam Core and 24 coal for 100 raw food in 6 working hours; an Industrial Hothouse produces 180. Consumes the core each batch. Build food reserves before storms; this does not bypass weather shutdowns.',
        5,125,95,18,['Cores3','FermentationBeds'],GROWING,1,icon=(4,8),mechanic='steam-core-to-food-chain')
    for key,source,path,building,amount in [
            ('ArtificialSpring','Plantation_Food','resourceextraction/foodplantation','Hothouse',100),
            ('IndustrialArtificialSpring','SteamPlantation_Food','resourceextraction/foodplantation_steam','Industrial Hothouse',180)]:
        recipe(key,'Artificial Spring Cultivation',source,building,[path],'Raw Food',amount,{'Steam Cores':1,'Coal':24},6,research)

    for key,scenarios,tier,factor in [('DistributedCaches',COLD,4,4),('AutumnDistributedCaches',AUTUMN,1,3)]:
        add(key,'Neighbourhood Cache Networks',
            f'Small Resource Depots gain {int((factor-1)*100)}% capacity for coal, wood, steel, raw food and food rations. Large Resource Depots are unaffected. Gives compact, distributed depots a distinct role instead of forcing every stockyard to use large warehouses.',
            tier,85 if tier==4 else 28,55 if tier==4 else 12,13 if tier==4 else 6,[],scenarios,3,
            sites=reserve(key,'Resource Depot',{n:factor for n in ('Coal','Wood','Steel','Raw Food','Food Rations')}),
            icon=(3,6),mechanic='small-depot-specialisation')
    add('PolarProvisionVaults','Polar Provision Vaults',
        'Large Resource Depots gain 500% capacity for raw food and food rations, and 300% capacity for coal. Other resources and small depots are unaffected. Specialise large warehouses as food and heating reserves for prolonged supply interruptions.',
        5,150,120,20,['ModularWarehouses'],COLD,3,
        sites=reserve('PolarProvisionVaults','Resource Depot Big',{'Raw Food':6,'Food Rations':6,'Coal':4}),
        icon=(3,6),mechanic='large-depot-storm-reserves')

    industrial=['GatheringPost','Sawmill','SteamSawmill','WallDrill','WallDrillSteam','WallDrillAdvanced',
                'Coal Mine','SteamCoalMine','AdvancedCoalMine','Iron Ore Mine','SteamIronOreMine','AdvancedOreMine',
                'CoalThumper','CoalThumperSteam','CharcoalKiln','Factory','Engineers Lab']
    # Reuse the established Army Warehouse binding instead of guessing its name.
    warehouse=existing['EdgeWarehouseSorting']['effects'][0][0]
    for key,title,tier,human,robot,heat,parents in [
            ('WinterArtisanGuilds','Winter Artisan Guilds',4,2.5,1,2,['WorkshopBench']),
            ('AutonomousMaintenance','Autonomous Maintenance Network',5,1,2.5,0,['ClockworkSynchronisers','Cores2'])]:
        description=('Human crews gain 150% workplace efficiency at Gathering Posts, resource-extraction buildings, Kilns, Factories and Workshops, plus the Army Warehouse where present. Those workplaces also gain +2 insulation. Automaton efficiency is unchanged; supports a sheltered, human-staffed industrial city.' if human>1 else
                     'Automatons gain 150% workplace efficiency at Gathering Posts, resource-extraction buildings, Kilns, Factories and Workshops, plus the Army Warehouse where present. Human efficiency is unchanged. Normal automaton workplace permissions still apply; supports a city supplied by round-the-clock machine labour.')
        pairs=place(key,industrial,[(84,'f',human),(88,'f',robot),(96,'i',heat)])
        pairs.append((warehouse,pairs[0][1]))
        add(key,title,description,tier,130 if tier==4 else 170,95 if tier==4 else 140,18 if tier==4 else 24,parents,GENERATOR if robot>1 else COLD,0,
            sites=pairs,icon=(2,5) if robot>1 else (8,0),mechanic='automaton-specialisation' if robot>1 else 'human-industry-specialisation')

    construction=[n for n in places if n.startswith('Generator Construction') or n.startswith('[Builders] Endless_Generator Construction')]
    assert len(construction)==11
    for key,scenarios,tier,parent in [('BuilderAssemblyPlatforms',('Default_Endless_Builders',),2,'WorkshopBench'),
                                     ('AutumnAssemblyPlatforms',AUTUMN,1,'AutumnProfileGuardrails')]:
        changes=[(84,'f',2),(88,'f',2)]
        if scenarios==AUTUMN:changes.append((185,'i',1))
        add(key,'Riveted Assembly Platforms',
            'Generator construction workplaces gain 100% workplace efficiency. '+
            ('They also gain +1 workplace safety, helping maintain assembly speed without accepting the full accident risk.' if scenarios==AUTUMN else
             'Applies to staffed Generator construction phases in Endless Builders; finished Generators and ordinary Workshops are unaffected.'),
            tier,38,18,7,[parent],scenarios,1 if scenarios==AUTUMN else 3,
            sites=place(key,construction,changes),icon=(3,6),mechanic='generator-assembly-specialisation')

    research=add('AutumnFarWaterTrawlers','Far-Water Trawling',
        'Unlocks optional Fishing Harbour recipes: 1 ration, 1 wood and 4 coal produce 12 raw food, or 18 at an Advanced Harbour, in 2.5 working hours. Uses less bait per catch than Baited Nets, but more fuel and crew time. A supply-efficiency option rather than the fastest catch.',
        2,40,22,8,['AutumnBaitedNets'],AUTUMN,3,icon=(4,4),mechanic='fishing-bait-throughput-trade')
    for key,source,grade,amount in [('FarWaterTrawlers','[Builders]FishingHarbor1',1,12),
                                  ('AdvancedFarWaterTrawlers','[Builders]FishingHarbor2',2,18)]:
        paths=[f"builders/dock_fishing{'v2' if grade==2 else ''}",f'builders/docks/dockfishingproper_lvl{grade}']
        recipe(key,'Far-Water Trawling',source,'Fishing Harbour',paths,'Raw Food',amount,{'Food Rations':1,'Wood':1,'Coal':4},2.5,research)

    fabrication=['[Builders]ScaffoldingManufacture','[Builders]PipeFoundry','[Builders]SteelPlateForge',
                 '[Builders]Dock_LVL1','[Builders]Dock_LVL2','[Builders]Dock_LVL3',
                 '[Builders]ReloadingPostUniversal','[Builders]ReloadingPostUniversal2','[Builders]ReloadingPostUniversal3']
    add('AutumnArtisanGuilds','Port Craft Apprenticeships',
        'Human crews gain 150% workplace efficiency at Profiles Manufactures, Machine Shops, Foundries, Docks and Reloading Stations. These workplaces also gain +1 insulation, strengthening the whole delivery-to-assembly supply chain before the freeze.',
        2,52,28,10,['AutumnFabricationShifts'],AUTUMN,1,
        sites=place('AutumnArtisanGuilds',fabrication,[(84,'f',2.5),(96,'i',1)]),icon=(10,2),mechanic='port-supply-chain-specialisation')
    assert len(additions)==22
    return pack_modifiers(records),recipes,targets,additions
