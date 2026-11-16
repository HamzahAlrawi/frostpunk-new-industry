"""Default-available law trees built from verified native modifier layouts."""
import struct

from research_curation import normalized
from progression_choices import COLD


FAMILIES = (
    ('care', 'Community Care', (-8,-12), ('LocalAid','CommunityHealth','CriticalCare')),
    ('workforce', 'Workforce', (8,-12), ('TradeGuild','MasterCraftsmen','MechanicalMaintenance')),
    ('winter', 'Winter Preparedness', (-12,12), ('HousingCode','DistrictHearths','FoodShelters')),
    ('reserves', 'Public Reserves', (8,12), ('CommunalStockyards','StormReserves','IndustrialCapital')),
)


def default_laws(records, places, neutral_global, neutral_place, techinfo, resources, specs, guid):
    existing={t['id']:t for t in specs}
    native={t['name']:t for t in techinfo}
    labels=dict(places)
    # The Army Warehouse uses the verified production entity binding, which is
    # separate from the normal building catalogue's ID.
    warehouse=existing['EdgeWarehouseSorting']['effects'][0][0]
    labels['Army Warehouse']=bytes.fromhex(warehouse)
    industrial=['GatheringPost','Sawmill','SteamSawmill','WallDrill','WallDrillSteam','WallDrillAdvanced',
                'Coal Mine','SteamCoalMine','AdvancedCoalMine','Iron Ore Mine','SteamIronOreMine','AdvancedOreMine',
                'CoalThumper','CoalThumperSteam','CharcoalKiln','Factory','Engineers Lab','Army Warehouse']
    port=['[Builders]ScaffoldingManufacture','[Builders]PipeFoundry','[Builders]SteelPlateForge',
          '[Builders]Dock_LVL1','[Builders]Dock_LVL2','[Builders]Dock_LVL3',
          '[Builders]ReloadingPostUniversal','[Builders]ReloadingPostUniversal2','[Builders]ReloadingPostUniversal3']
    civic=['PublicHouse','FightClube','CareHouse','HouseOfPrayer','Temple','FaithKeepers',
           'Shrine','Neighborhood watch tower','Guardpost','Prison','CensusStation','HospitalOfMercy']
    autumn_civic=['PublicHouse','[Builders] HouseOfPrayer','[Builders] Public Bath','CareHouse',
                  '[Builders] Labour Union','[Builders] Workers Council','[Builders]FieldPharmacy']
    medical=['Medical Post','Ambulatorium']
    housing=['Tent','Bunkhouse','House']
    autumn_housing=['[Builders] Tent','[Builders] Bunkhouse','[Builders] House']
    food=['Food Processing','Plantation','Steam Plantation']
    autumn_food=['Food Processing','[Builders]DockFishing_LVL1','[Builders]DockFishing_LVL2']

    def register(key,kind,body):
        identity=guid('default-laws/'+key).hex()
        assert identity not in records
        records[identity]=[kind,('NI default laws/'+key).encode(),bytes(body)]
        return identity

    def site_effect(key,names,changes):
        body=bytearray(neutral_place)
        offsets={'human':(84,'f'),'automaton':(88,'f'),'insulation':(96,'i'),'amputation':(173,'f'),'safety':(185,'i')}
        for field,value in changes.items():
            offset,code=offsets[field]
            struct.pack_into('<'+code,body,offset,value)
        modifier=register(key,'Place',body)
        return [(labels[name].hex(),modifier) for name in names],dict(targets=names,**changes)

    def storage_effect(key,factors):
        rest=bytes.fromhex(native['R 2_ResourceDepotUpgrade']['rest'])
        assert rest[:8]==struct.pack('<II',2,0) and struct.unpack_from('<I',rest,8)[0]==2
        kind,_,raw=records[rest[28:44].hex()]
        body=normalized(raw)
        marker=struct.pack('<I',8)+resources['Augmentation parts']
        assert kind=='Place' and body.count(marker)==1
        start=body.index(marker)+4
        wanted={resources[name]:factor for name,factor in factors.items()}
        chunks=[];seen=set()
        for pos in range(start,start+8*24,24):
            raw=body[pos:pos+24]
            assert raw[16:]==struct.pack('<If',0,1.5)
            chunks.append(raw[:20]+struct.pack('<f',wanted.get(raw[:16],1)))
            seen.add(raw[:16])
        assert wanted.keys()<=seen
        body=body[:start]+b''.join(chunks)+body[start+8*24:]
        modifier=register(key,'Place',body)
        return [(places[name].hex(),modifier) for name in ('Resource Depot','Resource Depot Big')],dict(storage=factors,targets=['Resource Depot','Resource Depot Big'])

    def benefit(key,sites=(),*,global_changes=None,storage=None):
        pairs=[];metadata=[]
        for i,(names,changes) in enumerate(sites):
            values,info=site_effect(key+'/site/'+str(i),names,changes)
            pairs.extend(values);metadata.append(info)
        if storage:
            values,info=storage_effect(key+'/storage',storage)
            pairs.extend(values);metadata.append(info)
        body=bytearray(neutral_global)
        for field,value in (global_changes or {}).items():
            assert field in ('cold_illness','heat_radius')
            struct.pack_into('<f',body,166 if field=='cold_illness' else 69,value)
        body=body[:77]+struct.pack('<I',len(pairs))+b''.join(bytes.fromhex(p+m) for p,m in pairs)+body[81:]
        return register(key,'Global',body),dict(sites=metadata,global_changes=global_changes or {})

    hope='GOLD [Common] Hope rise - '
    calm='GOLD [Common] Discontent fall - '
    result=[]

    def add(key,title,description,effects,sites=(),*,global_changes=None,storage=None,
            autumn_title=None,autumn_description=None,autumn_sites=None,autumn_global=None):
        identity='DefaultLaw'+key
        modifier,benefits=benefit(key,sites,global_changes=global_changes,storage=storage)
        alternative=modifier;alternate_benefits=benefits
        if autumn_sites is not None or autumn_global is not None:
            alternative,alternate_benefits=benefit('Autumn/'+key,autumn_sites if autumn_sites is not None else sites,
                                                  global_changes=autumn_global if autumn_global is not None else global_changes,
                                                  storage=storage)
        result.append(dict(id=identity,title=title,description=description,effects=effects,modifier=modifier,
                           research=None,default_available=True,requires_laws=[],excludes_laws=[],introduced_in='3.13.0',
                           book='Adaptation',scenarios=list(COLD),benefits=benefits,
                           autumn_title=autumn_title or title,autumn_description=autumn_description or description,
                           autumn_modifier=alternative,autumn_benefits=alternate_benefits))

    add('LocalAid','Local Aid Societies',
        'Hope rises slightly. Medical Posts gain 75% healing efficiency for human and automaton staff and +1 insulation.',
        [hope+'slightly'],[(medical[:1],dict(human=1.75,automaton=1.75,insulation=1))])
    add('CommunityHealth','Neighbourhood Health Service',
        'Hope rises moderately. Tents, Bunkhouses and Houses gain +1 insulation. Cold-related illness is reduced by 50%.',
        [hope+'moderately'],[(housing,dict(insulation=1))],global_changes=dict(cold_illness=0.5),
        autumn_description='Hope/Motivation improves. All camp accommodation grades gain +1 insulation. Cold-related illness is reduced by 50%.',
        autumn_sites=[(autumn_housing,dict(insulation=1))])
    add('CriticalCare','Critical Care Guarantee',
        'Discontent falls moderately. Infirmaries gain 150% healing efficiency for humans and automatons and +2 insulation. Medical Posts do not amputate under Radical Treatment; that native law must still be signed.',
        [calm+'moderately'],[(['Ambulatorium'],dict(human=2.5,automaton=2.5,insulation=2)),
                             (['Medical Post'],dict(amputation=0))])

    add('TradeGuild','Trade Guild Charter',
        'Hope rises slightly. Human crews gain 75% workplace efficiency at industrial workplaces, including Workshops and the Army Warehouse where present. Automaton efficiency is unchanged.',
        [hope+'slightly'],[(industrial,dict(human=1.75))],
        autumn_description='Hope/Motivation improves. Human crews gain 75% workplace efficiency at extraction, Workshops, Kilns, fabrication, Docks and Reloading Stations.',
        autumn_sites=[([n for n in industrial if n!='Army Warehouse']+port,dict(human=1.75))])
    add('MasterCraftsmen',"Master Craftsmen's Charter",
        'Hope rises moderately. Industrial human crews gain 150% workplace efficiency; their workplaces gain +1 insulation. Automaton efficiency is unchanged.',
        [hope+'moderately'],[(industrial,dict(human=2.5,insulation=1))],
        autumn_description='Hope/Motivation improves. Human crews at extraction, Workshops and Kilns gain 175% workplace efficiency and +1 insulation. Fabrication and port workplaces instead gain 75% human efficiency and +1 insulation.',
        autumn_sites=[([n for n in industrial if n!='Army Warehouse'],dict(human=2.75,insulation=1)),
                       (port,dict(human=1.75,insulation=1))])
    add('MechanicalMaintenance','Mechanical Maintenance Charter',
        'Discontent falls slightly. Industrial human crews gain 75% workplace efficiency and automatons gain 175%; their workplaces gain +2 insulation. Normal automaton workplace permissions still apply.',
        [calm+'slightly'],[(industrial,dict(human=1.75,automaton=2.75,insulation=2))],
        autumn_title='Mechanised Worksites',
        autumn_description='Discontent falls slightly. Fabrication, Docks and Reloading Stations gain 150% workplace efficiency, +2 safety and +1 insulation. This does not create automatons.',
        autumn_sites=[(port,dict(human=2.5,automaton=2.5,safety=2,insulation=1))])

    add('HousingCode','Winter Housing Code',
        'Discontent falls moderately. Tents, Bunkhouses and Houses gain +1 insulation.',
        [calm+'moderately'],[(housing,dict(insulation=1))],
        autumn_title='Camp Housing Code',autumn_description='Discontent falls moderately. All camp accommodation grades gain +1 insulation.',
        autumn_sites=[(autumn_housing,dict(insulation=1))])
    add('DistrictHearths','District Hearths Ordinance',
        'Hope rises moderately. Civic and healthcare buildings gain +2 insulation. All heat zones gain 25% radius.',
        [hope+'moderately'],[(civic+medical,dict(insulation=2))],global_changes=dict(heat_radius=1.25),
        autumn_description='Hope/Motivation improves. Communal, labour-service and healthcare buildings gain +2 insulation. Heat zones, including Braziers, gain 25% radius.',
        autumn_sites=[(autumn_civic+medical,dict(insulation=2))])
    add('FoodShelters','Protected Food Supply',
        'Discontent falls moderately. Cookhouses and both Hothouse grades gain 75% workplace efficiency for humans and automatons and +2 insulation. Scripted storm shutdowns are unchanged.',
        [calm+'moderately'],[(food,dict(human=1.75,automaton=1.75,insulation=2))],
        autumn_description='Discontent falls moderately. Cookhouses and both Fishing Harbour grades gain 75% workplace efficiency and +2 insulation. Scripted shutdowns are unchanged.',
        autumn_sites=[(autumn_food,dict(human=1.75,automaton=1.75,insulation=2))])

    add('CommunalStockyards','Communal Stockyards',
        'Hope rises slightly. Both Resource Depot sizes gain 100% additional coal, wood and steel capacity.',
        [hope+'slightly'],storage={'Coal':2,'Wood':2,'Steel':2})
    add('StormReserves','Storm Reserve Mandate',
        'Hope rises moderately. Both Resource Depot sizes gain 400% additional coal capacity and 300% additional raw-food and food-ration capacity.',
        [hope+'moderately'],storage={'Coal':5,'Raw Food':4,'Food Rations':4})
    add('IndustrialCapital','Industrial Capital Charter',
        'Hope rises moderately. Both Resource Depot sizes gain 400% additional wood and steel capacity. Factories gain 100% workplace efficiency for humans and automatons.',
        [hope+'moderately'],[(['Factory'],dict(human=2,automaton=2))],storage={'Wood':5,'Steel':5},
        autumn_description='Hope/Motivation improves. Both Resource Depot sizes gain 400% additional wood and steel capacity. Profiles Manufactures, Machine Shops and Foundries gain 100% workplace efficiency.',
        autumn_sites=[(port[:3],dict(human=2,automaton=2))])

    by={law['id']:law for law in result}
    for family,title,(x,y),keys in FAMILIES:
        ids=['DefaultLaw'+key for key in keys]
        for index,identity in enumerate(ids):
            law=by[identity]
            law.update(family=family,family_title=title,book_guid='aa9e39dee99e599452414bfb60af2960',
                       position=[x if index==0 else x+(-3 if index==1 else 3),
                                 y if index==0 else y+(-4 if y<0 else 4)],
                       cooldown=12 if index==0 else 24,branch_root=index==0)
            if index:
                law['requires_laws']=[ids[0]]
                law['excludes_laws']=[ids[3-index]]
    assert len(result)==12
    return result
