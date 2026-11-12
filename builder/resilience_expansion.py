"""Further factory, heating and construction strategies for the 3.10 release."""
import struct

from last_autumn import construction_cost_transform
from progression_choices import COLD, GENERATOR, GROWING, AUTUMN
from research_curation import normalized


NEW_VERSION='3.10.0'


def add_resilience(*,add,place,reserve,recipe,supersede,clone,effect,records,places,resources,existing):
    def research(*args,**kwargs):
        return add(*args,**kwargs,introduced_in=NEW_VERSION)

    def global_effect(key,changes,suffix='global'):
        body=bytearray(normalized(records['d87b131d3367ed86d04efc1f7c1f7a5a'][2]))
        assert len(body)==186
        struct.pack_into('<f',body,150,0)
        for offset,value in changes:
            assert offset in (65,69,166)
            assert body[offset:offset+4]==struct.pack('<f',1)
            struct.pack_into('<f',body,offset,value)
        return effect(key,'Global',bytes(body),suffix)

    def free_heaters(key,names):
        _,_,categories=clone(key,'H 4_Boiler Upgrade - less coal')
        ids={g for _,g in categories};assert len(ids)==1
        g,=ids;kind,_,body=records[g];assert kind=='Place'
        start=body.index(resources['Coal'])+16
        assert body[start:start+8]==struct.pack('<2f',-1,1)
        records[g][2]=body[:start]+struct.pack('<2f',0,0)+body[start+8:]
        return [(places[name].hex(),g) for name in names]

    for key,modes in [('PreventiveMedicine',COLD),('AutumnPreventiveMedicine',AUTUMN)]:
        research(key,'Preventive Field Medicine',
            'Citizens have a 25% lower chance of illness caused by cold. Medical Posts also gain 75% healing efficiency for human staff and automatons. Available before Drawing Boards, helping prevent and treat the opening wave of sickness.',
            0,18,6,4,[],modes,2,
            globals_=[global_effect(key,[(166,0.75)])],
            sites=place(key,['Medical Post'],[(84,'f',1.75),(88,'f',1.75)]),icon=(4,9),mechanic='opening-prevention-and-treatment')

    key='ClosedLoopMetallurgy'
    unlock=research(key,'Closed-Loop Metallurgy',
        'Upgrades the Factory salvage queue: 1 Steam Core and 30 coal become 120 steel in 8 working hours. The core is consumed. Links renewable core production to steel reclamation, offering an alternative to expanding Steelworks. Replaces Deep Scrap Recovery.',
        5,145,110,22,['DeepScrapRecovery','Cores3'],COLD,3,icon=(8,0),mechanic='core-to-steel-reclamation')
    supersede('DeepScrapRecovery',unlock)
    recipe(key,'Closed-Loop Metallurgy','Augmentation_parts','Factory',['resourceprocessing/prefabfactory'],
           'Steel',120,{'Steam Cores':1,'Coal':30},8,unlock,resource_icon=(0,0))

    key='MassCoreFabrication'
    unlock=research(key,'Core Fabrication Cells',
        'Upgrades the Factory core queue to a batch of 3 Steam Cores for 90 steel, 50 wood and 100 coal in 10 working hours. Costs per core fall to 30 steel, about 16.7 wood and 33.3 coal. Replaces Serial Core Production in the selector.',
        5,180,150,26,['Cores3'],COLD,0,icon=(0,2),mechanic='multi-core-factory-batches')
    supersede('Cores3',unlock)
    recipe(key,'Core Fabrication Cells','Augmentation_parts','Factory',['resourceprocessing/prefabfactory'],
           'Steam Cores',3,{'Steel':90,'Wood':50,'Coal':100},10,unlock,resource_icon=(0,2))

    for key,modes,tier,parent in [('PressureKitchens',COLD,4,'FuelledStockpots'),
                                 ('AutumnPressureKitchens',AUTUMN,2,'AutumnSlowSimmeredBroth')]:
        upgrade=' Replaces Fuelled Stockpots; ordinary ration recipes and Slow-Simmered Broth remain available.' if modes==COLD else ''
        unlock=research(key,'Steel-Assisted Pressure Kitchens',
            'Unlocks a Cookhouse recipe: 2 raw food, 4 coal and 1 steel become 10 standard rations in 30 working minutes. Steel maintains the pressure vessels. Conserves raw food by spending industrial materials.'+upgrade,
            tier,65 if tier==4 else 32,35 if tier==4 else 16,12 if tier==4 else 7,[parent],modes,3 if modes==COLD else 2,
            icon=(5,9),mechanic='steel-assisted-ration-production')
        if modes==COLD:supersede('FuelledStockpots',unlock)
        recipe(key,'Steel-Assisted Pressure Kitchens','Canteen_FoodRations_standard','Cookhouse',
               ['resourceprocessing/foodprocessing'],'Food Rations',10,{'Raw Food':2,'Coal':4,'Steel':1},0.5,unlock)

    key='TimberSubstrateBeds'
    unlock=research(key,'Timber-Substrate Growing Beds',
        'Upgrades Coal-Heated Seedbeds with a wood-fed growing recipe: 4 wood and 1 coal produce 8 raw food in 2 working hours. Industrial Hothouses spend 8 wood and 2 coal for 16 raw food. Conserves coal and needs no ration starter, but grows more slowly than the previous heated recipe. Replaces Coal-Heated Seedbeds in each selector.',
        4,75,40,13,['CoalHeatedSeedbeds'],GROWING,1,icon=(4,8),mechanic='wood-for-growing-fuel-trade')
    for recipe_key,old,source,path,building,amount,wood,coal in [
            (key,'CoalHeatedSeedbeds','Plantation_Food','resourceextraction/foodplantation','Hothouse',8,4,1),
            ('IndustrialTimberSubstrateBeds','IndustrialCoalSeedbeds','SteamPlantation_Food','resourceextraction/foodplantation_steam','Industrial Hothouse',16,8,2)]:
        supersede(old,unlock)
        recipe(recipe_key,'Timber-Substrate Growing Beds',source,building,[path],'Raw Food',amount,{'Wood':wood,'Coal':coal},2,unlock)

    key='ReclamationStockyards'
    sites=reserve(key,'Resource Depot Big',{'Wood':5,'Steel':5})
    sites+=place(key,['Factory'],[(84,'f',2),(88,'f',2)],'factory')
    research(key,'Reclamation Stockyards',
        'Large Resource Depots gain 400% capacity for wood and steel. Factories gain 100% workplace efficiency for both work roles. Gives the core-and-steel reclamation industry room to store its inputs and output; small depots and food storage are unaffected.',
        5,150,120,22,['ClosedLoopMetallurgy','ModularWarehouses'],COLD,0,sites=sites,icon=(3,6),mechanic='factory-and-bulk-material-districts')

    for key,modes,tier,parents in [
            ('ProtectedHealthcareHeaters',COLD,4,['CondensateHeaters','FieldInfirmaries']),
            ('AutumnHealthcareHeaters',AUTUMN,3,['AutumnCondensateHeaters','AutumnFieldInfirmaries'])]:
        research(key,'Protected Healthcare Heating',
            'Heaters in Medical Posts and Infirmaries use no coal. They retain their normal heat output and must still be unlocked and switched on. Supports dispersed medical care without adding a heating-fuel burden.',
            tier,80 if tier==4 else 45,45 if tier==4 else 24,14 if tier==4 else 9,parents,modes,2,
            sites=free_heaters(key,['Medical Post','Ambulatorium']),icon=(7,7),mechanic='coal-free-clinic-heaters')
    key='AutumnCoreFreeFabrication'
    kind,_,body=records['3c76b6fed8535ab7ba42279f732c57db'];assert kind=='Global'
    body=construction_cost_transform(places,resources,['[Builders]PipeFoundry','[Builders]SteelPlateForge'],{'Steam Cores':1})(body)
    research(key,'Core-Free Fabrication Halls',
        'Machine Shops and Foundries cost one fewer Steam Core to construct, removing their core requirement. Wood and steel costs are unchanged. Expand component production without waiting for more imported cores.',
        2,45,25,9,['[Builders] GM 2_SteelPlateForge'],AUTUMN,1,
        globals_=[effect(key,kind,body)],icon=(10,2),mechanic='core-free-component-factories')

    for key,modes,tier,parents,names in [
            ('IndustrialHeatRecovery',COLD,5,['CondensateHeaters','MasteryFactoryLines'],['Factory','Engineers Lab']),
            ('AutumnIndustrialHeaters',AUTUMN,3,['AutumnCondensateHeaters','AutumnCoreFreeFabrication'],
             ['[Builders]ScaffoldingManufacture','[Builders]PipeFoundry','[Builders]SteelPlateForge','Engineers Lab'])]:
        text=('Heaters in Factories and Workshops use no coal.' if modes==COLD else
              'Heaters in Profiles Manufactures, Machine Shops, Foundries and Workshops use no coal.')
        research(key,'Industrial Heat Recuperators',text+
            ' Normal Heater unlocks, switches and power levels still apply. Production ingredients are unchanged; this improves workplace heating.',
            tier,120 if tier==5 else 52,85 if tier==5 else 28,18 if tier==5 else 10,parents,modes,0,
            sites=free_heaters(key,names),icon=(7,7),mechanic='coal-free-industrial-heaters')

    for key,modes,tier,parents in [('CompactHeatingGrid',GENERATOR,4,['SteamTrunklines']),
                                  ('EdgeCompactHeatingGrid',('Reconquest',),4,['EdgeBrazierNetworks']),
                                  ('AutumnCompactHeat',AUTUMN,3,['AutumnSteamTrunklines'])]:
        radius=global_effect(key,[(69,0.8)],'radius')
        globals_=[radius];sites=[];extras=[]
        if modes==GENERATOR:
            g,s,e=clone(key,'H 3_Generator Upgrade - less coal',[(0.9,0.75)])
            globals_+=g;sites+=s;extras+=e
            g,s,e=clone(key,'H 5_Steamhub Upgrade - less coal',[(0.666667,0.6)])
            globals_+=g;sites+=s;extras+=e
            text='The Generator uses 25% less coal and Steam Hubs use 40% less coal.'
        else:
            target,source=existing['EdgeBrazierGrates']['effects'][0]
            kind,_,body=records[source];assert kind=='Place'
            p=body.index(resources['Coal'])+16
            assert body[p:p+8]==struct.pack('<2f',0,0.75)
            body=body[:p]+struct.pack('<2f',0,0.6)+body[p+8:]
            sites=[(target,effect(key,kind,body,'brazier'))]
            text='Braziers use 40% less coal.'
        research(key,'Compact Heating Grids',text+
            ' Trade-off: all heat-zone radii shrink by 20%. Heater power is unaffected. Optional permanent specialisation for compact districts rather than wide heat coverage.',
            tier,95 if tier==4 else 48,60 if tier==4 else 25,16 if tier==4 else 9,parents,modes,0,
            globals_=globals_,sites=sites,extras=extras,icon=(1,6),mechanic='heat-coverage-for-fuel-trade')

    key='RecuperatingAccumulators'
    globals_,_,_=clone(key,'H 6_Generator Upgrade - less stress',[(0.75,1),(1.25,2)])
    _,_,extras=clone(key,'H 3_Generator Upgrade - less coal',[(0.9,0.85)])
    research(key,'Recuperating Accumulators',
        'Generator stress recovers 100% faster and the Generator uses 15% less coal. Develops Pressure-Buffer Boiler Drums into a system for recovering between overdrive periods; the earlier research and other fuel modifiers remain active.',
        4,110,75,18,['BoilerBufferDrums','MasteryOverdriveRecovery'],GENERATOR,3,
        globals_=globals_,extras=extras,icon=(1,6),mechanic='overdrive-recovery-and-fuel-reclamation')

    key='EndlessRelayWorkshops'
    globals_,sites,extras=clone(key,'E 3_ScoutsSpeed',[(1.5,2.5)])
    sites+=place(key,['Factory'],[(84,'f',1.75),(88,'f',1.75)],'factory')
    research(key,'Frostland Relay Workshops',
        'Scouts travel 150% faster and Factories gain 75% workplace efficiency for both work roles. Supports repeated Frostland exploration and processing recovered resources after Endless storms. Adds no expedition teams.',
        4,85,55,14,['ScoutOverhaul','MasteryFactoryLines'],('Default_Endless','Default_Endless_Builders'),3,
        globals_=globals_,sites=sites,extras=extras,icon=(2,10),mechanic='endless-exploration-and-reclamation')

    key='EdgeRecoveryLots'
    unlock=research(key,'Warehouse Recovery Lots',
        'Upgrades Warehouse Cutting Torches: 1 Steam Core and 20 coal produce 100 steel and 40 wood together in 6 working hours. The core is consumed. Adds a wood-recovery route to the core economy while preserving the Warehouse selector size.',
        4,80,60,14,['EdgeWarehouseSalvage','Cores2'],('Reconquest',),3,icon=(8,0),mechanic='warehouse-mixed-material-recovery')
    supersede('WarehouseSalvage',unlock)
    recipe(key,'Warehouse Recovery Lots','[Reconquest]Vault_Multitasking','Army Warehouse',['reconquest/vault'],
           'Steel',100,{'Steam Cores':1,'Coal':20},6,unlock,byproducts={'Wood':40},resource_icon=(0,0))

    key='AutumnReusableFormwork'
    unlock=research(key,'Reusable Formwork Systems',
        'Unlocks an optional Profiles Manufacture recipe: 1 steam exchanger and 18 wood produce 3 structural profiles in 2 working hours. Uses Machine Shop output to conserve timber and accelerate profile production.',
        2,38,20,8,['AutumnSteamCuredProfiles','AutumnFuelTemperedExchangers'],AUTUMN,1,
        icon=(3,6),mechanic='exchanger-fed-profile-production')
    recipe(key,'Reusable Formwork Systems','[Builders] Manufacture Scaffoldings','Profiles Manufacture',
           ['builders/constructionsite/scaffoldingsmanufacture'],'Wooden Materials',3,{'Steam Tools':1,'Wood':18},2,unlock)

    key='AutumnRefractoryCasting'
    unlock=research(key,'Sacrificial Mould Casting',
        'Unlocks an optional Foundry recipe: 1 structural profile, 10 steel and 45 coal produce 2 steel composites in 3 working hours. Consumes a profile as mould material to save steel and fuel.',
        3,48,28,9,['AutumnCharcoalAlloy','AutumnReusableFormwork'],AUTUMN,1,
        icon=(9,10),mechanic='profile-fed-composite-production')
    recipe(key,'Sacrificial Mould Casting','[Builders] ManufactureSteelPlate','Foundry',
           ['builders/constructionsite/metalplateforge'],'Steel Plates',2,{'Wooden Materials':1,'Steel':10,'Coal':45},3,unlock)

    key='AutumnCompositeDies'
    unlock=research(key,'Composite Exchanger Dies',
        'Unlocks an optional Machine Shop recipe: 1 steel composite, 12 steel and 20 coal produce 3 steam exchangers in 3 working hours. Converts Foundry output into faster, steel-efficient exchanger production, completing a component-reuse chain.',
        3,48,28,9,['AutumnFuelTemperedExchangers','AutumnRefractoryCasting'],AUTUMN,1,
        icon=(10,2),mechanic='composite-fed-exchanger-production')
    recipe(key,'Composite Exchanger Dies','[Builders] Factory Pipe','Machine Shop',
           ['builders/constructionsite/pipefoundry'],'Steam Tools',3,{'Steel Plates':1,'Steel':12,'Coal':20},3,unlock)

    key='AutumnColdCurrentLures'
    unlock=research(key,'Cold-Current Wooden Lures',
        'Upgrades Baited Nets with a bait-free recipe: 2 wood and 2 coal produce 8 raw food in 1 working hour, or 12 at an Advanced Fishing Harbour. Conserves food rations by spending wood and fuel. Replaces Baited Nets; Far-Water Trawling and Dockside Smokehouses remain available.',
        2,36,18,8,['AutumnBaitedNets'],AUTUMN,3,icon=(4,4),mechanic='bait-free-fishing-trade')
    for recipe_key,old,source,grade,amount in [('ColdCurrentLures','BaitedNets','[Builders]FishingHarbor1',1,8),
                                             ('AdvancedColdCurrentLures','AdvancedBaitedNets','[Builders]FishingHarbor2',2,12)]:
        supersede(old,unlock)
        paths=[f"builders/dock_fishing{'v2' if grade==2 else ''}",f'builders/docks/dockfishingproper_lvl{grade}']
        recipe(recipe_key,'Cold-Current Wooden Lures',source,'Fishing Harbour',paths,'Raw Food',amount,{'Wood':2,'Coal':2},1,unlock)

    key='AutumnForagerMealRoutes'
    globals_,sites,extras=clone(key,'[Builders] FF 1_ForagersSpeedUpgrade',[(1.5,2)])
    sites+=place(key,['Food Processing'],[(84,'f',1.75),(88,'f',1.75)],'kitchens')
    research(key,'Forager Meal Routes',
        'Foragers travel 100% faster and Cookhouses gain 75% workplace efficiency. Moves crews between food sites sooner while increasing the capacity to process their deliveries. Adds no forager teams.',
        1,30,14,7,['AutumnRelayMarkers'],AUTUMN,3,globals_=globals_,sites=sites,extras=extras,
        icon=(2,10),mechanic='forager-and-kitchen-throughput')

    key='AutumnSafetyInfirmary'
    unsafe=['[Builders]ScaffoldingManufacture','[Builders]PipeFoundry','[Builders]SteelPlateForge',
            '[Builders]ReloadingPostUniversal','[Builders]ReloadingPostUniversal2','[Builders]ReloadingPostUniversal3']
    sites=place(key,unsafe,[(185,'i',1)],'safety')
    sites+=place(key,['Medical Post','Ambulatorium'],[(84,'f',2),(88,'f',2)],'medicine')
    research(key,'Industrial Safety Dispensaries',
        'Profiles Manufactures, Machine Shops, Foundries and Reloading Stations gain +1 safety. Medical Posts and Infirmaries gain 100% healing efficiency. Combines accident-risk management with stronger treatment capacity; it does not prevent every accident.',
        2,42,22,8,['AutumnMedicalRotas','AutumnMachineGuards'],AUTUMN,2,sites=sites,
        icon=(4,9),mechanic='worksite-safety-and-treatment')
