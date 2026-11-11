"""Build New Industry from the user's original Frostpunk data, without executable patches."""
from pathlib import Path
import struct, uuid, json, re, gzip, hashlib, sys, os
sys.path.insert(0,str(Path(__file__).resolve().parent/'tools'))
import archive
from archive import entries, read
from opening_progression import EDGE_OPENING, OPENING_STOCK, RESEARCH_SPEED, research_curve, starting_supplies
from resourceful_upgrades import EDGE_RESOURCEFUL
from gameplay_upgrades import EDGE_GAMEPLAY, OUTPOST_TECH
INSTALL_PATH = archive.GAME
archive.GAME = Path(os.environ.get('NI_VANILLA', str(INSTALL_PATH)))
GAME = archive.GAME

OUT=Path(os.environ.get('NI_PACKAGE', str(Path(__file__).resolve().parents[1]/'build/native'))); OUT.mkdir(parents=True,exist_ok=True)
PAY=OUT/'payload'; PAY.mkdir(exist_ok=True)
SRC=Path(__file__).resolve().parent/'cache/extracted'
u32=lambda n:struct.pack('<I',n)
f32=lambda n:struct.pack('<f',n)
string=lambda s:b'\x01'+s.encode()+b'\0' if s else b'\0'
gid=lambda s:uuid.uuid5(uuid.NAMESPACE_URL,'frostpunk-new-industry-v1/'+s).bytes_le
texts={}
def loc(key,value):
    key='Mods/NewIndustry/'+key; texts[key]=value
    return string('@'+key)
def req(g): return b'\1FrostpunkTechnologyRequirement\0'+bytes(17)+g
def neg(g): return b'\1FrostpunkCompositeRequirement\0'+bytes(17)+u32(2)+u32(1)+req(g)
def costs(d): return u32(len(d))+b''.join(RES[k]+u32(v) for k,v in d.items())
RES={}
economy=(SRC/'common/configs/frostpunkeconomyconfig.bin').read_bytes()
for name in ['Coal','Wood','Steel','Wooden Materials','Steel Plates','Steam Tools','Steam Cores','Raw Food','Food Rations','Augmentation parts']:
    p=economy.index(b'\1\1'+name.encode()+b'\0')+len(name)+3
    RES[name]=economy[p:p+16]
TC=(SRC/'common/configs/frostpunktechnologiesconfig.bin').read_bytes()
techinfo=json.loads((Path(__file__).resolve().parent/'cache/tech.json').read_text())
research_columns=json.loads((Path(__file__).resolve().parent/'research_columns.json').read_text())
TECH={t['name']:bytes.fromhex(t['guid']) for t in techinfo}
TIERS={n:TECH[name] for n,name in [(1,'01_TierUnlock 1'),(2,'02_TierUnlock2'),(3,'03_TierUnlock3'),(4,'04_TierUnlock4'),(5,'05_TierUnlock5')]}
CAT=gid('industry-category')
MASTERY=gid('city-mastery-category')
HEATING=bytes.fromhex('3be2ab21909e45aee64283f2019439d3')
EXPLORATION=bytes.fromhex('162334e6bf5c4bbdd54f73a13c7aad25')
RESOURCES=bytes.fromhex('27bd02ddb7af8dbe2b40a7feaad6e865')
FOOD=bytes.fromhex('60914ba3dfa9c3b74145ff87430759f9')
DISPLAY={'Wooden Materials':'Machined Frames','Steel Plates':'Pressure Chambers','Steam Tools':'Steam Manifolds','Augmentation parts':'Prostheses'}
newtechs=[]; recipes=[]; specs=[]
base=techinfo[0];tail=base['tail'];duration=tail+36+base['costcount']*20
TECH_REST=TC[duration+4:techinfo[1]['start']]
assert len(TECH_REST)==41

def technology(key,title,description,stage,col,prereqs,cost,hours,icon=(4,8),category=CAT, *,
               rest=None, effects=(), global_effects=(), extra_effects=(), prerequisite_names=None):
    g=gid('tech/'+key)
    allreq=([TIERS[stage]] if stage else [])+prereqs
    occupied = [t['layout'][2] for t in techinfo
                if t['category'] == category.hex() and t['layout'][3] == stage * 2]
    occupied += [t['column'] for t in specs
                 if t['category'] == category.hex() and t['tier'] == stage]
    planned_column = research_columns.get(category.hex(), {}).get(key)
    choices = ([planned_column] if planned_column is not None
               else sorted(range(2, 21, 2), key=lambda x: (abs(x-col), x)))
    col = next((x for x in choices if all(abs(x-y) >= 2 for y in occupied)), None)
    assert col is not None, (key, stage)
    prefix=b'\1FrostpunkTechnologyEntry\0'+string('NI '+key)+g+b'\1'
    entry=prefix+u32(len(allreq))+b''.join(req(v) for v in allreq)+u32(0)
    entry+=loc('Tech/'+key+'/Name',title)+loc('Tech/'+key+'/Description',description)+loc('Tech/'+key+'/Short',description)
    entry+=struct.pack('<4i',*icon,col,stage*2)+category+costs(cost)+f32(hours)+(TECH_REST if rest is None else rest)
    newtechs.append(entry)
    specs.append(dict(id=key,title=title,tier=stage,column=col,category=category.hex(),requires=[r.hex() for r in allreq],hours=hours,cost=cost,description=description,guid=g.hex(),effects=[(p.hex(),e.hex()) for p,e in effects]))
    if prerequisite_names is not None:
        specs[-1]['prerequisite_names'] = prerequisite_names
        specs[-1]['global_effects'] = [effect.hex() for effect in global_effects]
        specs[-1]['extra_effects'] = [(p.hex(),e.hex()) for p,e in extra_effects]
    return g

BP=(SRC/'common/configs/frostpunkblueprintsconfig.bin').read_bytes()
bp_start=BP.index(b'\1\1Augmentation_parts\0'); bp_end=BP.index(b'\1\1[Builders] ManufactureSteelPlate\0')
prod=BP.index(b'\1FrostpunkResourceProduct\0',bp_start)
icon_start=BP.index(b'\1UI\\Elements\\Resources_Icos.dds\0',bp_start)
# The standard Factory's prosthesis recipe uses queue mode and an hour-based cycle.
BP_FLAGS=BP[icon_start+len(b'\1UI\\Elements\\Resources_Icos.dds\0')+16:prod]
assert BP_FLAGS==b'\0\1\1\0\0\0'
BP_REST=BP[bp_end-11:bp_end]
assert BP_REST==u32(2)+u32(1)+bytes(3)

def recipe(key,title,output,amount,inputs,hours,unlock,next_unlock=None, native_conditions=(0,b''), icon=(1,0)):
    g=gid('recipe/'+key); conditions=[req(unlock)]
    if next_unlock: conditions.append(neg(next_unlock))
    desc='Produce '+str(amount)+' '+DISPLAY.get(output,output)+'. Requires '+', '.join(str(v)+' '+DISPLAY.get(k,k) for k,v in inputs.items())+f'. Base cycle: {hours:g} working hours at full efficiency.'
    extra_count, extra_bytes = native_conditions
    data=b'\1'+string('NI '+key)+g+u32(len(conditions)+extra_count)+b''.join(conditions)+extra_bytes
    data+=loc('Recipe/'+key+'/Name',title)+loc('Recipe/'+key+'/Description',desc)+b'\0\0'
    data+=string('UI\\Elements\\Resources_Icos.dds')+struct.pack('<4i',*icon,4,4)+BP_FLAGS
    data+=b'\1FrostpunkResourceProduct\0'+u32(1)+RES[output]+u32(amount)+u32(0)+costs(inputs)+f32(hours)+BP_REST
    recipes.append((g,data,dict(id=key,title=title,output=output,amount=amount,inputs=inputs,hours=hours,
                                native_prosthetics_requirements=bool(extra_count))))

# Keep only one current core recipe in the stock Factory panel.
core_ids=[]
for index, (title, cycle, cost) in enumerate([
    ("Steam Core Fabrication", 24, {"Steel": 75, "Wood": 40, "Coal": 60}),
    ("Steam Core Assembly", 16, {"Steel": 60, "Wood": 30, "Coal": 50}),
    ("Serial Core Production", 10, {"Steel": 45, "Wood": 20, "Coal": 40}),
]):
    desc = "Factory: " + ", ".join(f"{qty} {name.lower()}" for name,qty in cost.items())
    desc += f" becomes one Steam Core in {cycle} working hours. Each upgrade replaces the earlier recipe."
    parents = core_ids[-1:] or [TECH["E 3_Factory"]]
    core_ids.append(technology(f"Cores{index+1}",title,desc,index+3,18,parents,
                              {"Wood": 90+index*65,"Steel":100+index*75},18+index*9,(0,2),EXPLORATION))
    if index:
        prev_title, prev_cycle, prev_cost = previous
        recipe(f"Cores{index}",prev_title,"Steam Cores",1,prev_cost,prev_cycle,core_ids[-2],core_ids[-1])
    previous = title, cycle, cost
recipe("Cores3",title,"Steam Cores",1,cost,cycle,core_ids[-1])

from vanilla_progression import make_upgrades
mods_path = "configs/frostpunkmodifiersconfig.bin"
new_modifiers = make_upgrades(technology, techinfo,
    (SRC/"common"/mods_path).read_bytes(),
    (SRC/"common/configs/frostpunkbuildingsconfig.bin").read_bytes(), gid, loc, u32)
from city_mastery import make_mastery
new_modifiers = make_mastery(technology, techinfo, (SRC/"common"/mods_path).read_bytes(), new_modifiers,
    (SRC/"common/configs/frostpunkbuildingsconfig.bin").read_bytes(), RES, MASTERY,
    {"heating":HEATING,"exploration":EXPLORATION,"resources":RESOURCES,"food":FOOD}, gid, loc, u32)

salvage=technology("ScrapRecovery", "Scrap Recovery Contracts",
    "Unlocks a Factory queue for salvaging frozen scrap. Spend 12 wood and 30 coal to recover 10 steel in 5 working hours.\n\nRequires: Drafting Machines (II), Factory.",
    2,8,[TECH["E 3_Factory"]],{"Wood":34,"Steel":18},8,(8,0),EXPLORATION,
    prerequisite_names=["Drafting Machines (II)","Factory"])
deep_salvage=technology("DeepScrapRecovery", "Deep Scrap Recovery",
    "Replaces the Factory salvage batch. Spend 8 wood and 26 coal to recover 14 steel in 5 working hours.\n\nRequires: Mechanical Calculators (III), Scrap Recovery Contracts.",
    3,6,[salvage],{"Wood":55,"Steel":35},10,(8,0),EXPLORATION,
    prerequisite_names=["Mechanical Calculators (III)","Scrap Recovery Contracts"])
recipe("ScrapRecovery","Scrap Recovery","Steel",10,{"Wood":12,"Coal":30},5,salvage,deep_salvage,icon=(0,0))
recipe("DeepScrapRecovery","Deep Scrap Recovery","Steel",14,{"Wood":8,"Coal":26},5,deep_salvage,icon=(0,0))

stockpots=technology("FuelledStockpots", "Fuelled Stockpots",
    "Unlocks an optional Cookhouse recipe. Spend 2 raw food and 1 coal to cook 6 standard rations in 9 minutes at full efficiency.\n\nRequires: Drawing Boards (I).",
    1,6,[],{"Wood":24,"Steel":10},6,(5,9),FOOD,prerequisite_names=["Drawing Boards (I)"])
food_start=BP.index(b'\1\1Canteen_FoodRations_standard\0')
food_better=BP.index(b'\1\1Canteen_FoodRations_better\0',food_start)
food_icon=string('UI\\Elements\\Resources_Icons2.dds')
food_product=string('FrostpunkFoodRationProduct')
standard=BP[food_start:food_better]
flags_at=standard.index(food_icon)+len(food_icon)+16
standard_flags=standard[flags_at:flags_at+6]
assert standard_flags==b'\1\1\1\0\0\0'
product_at=standard.index(food_product)+len(food_product)
assert standard[product_at:]==u32(1)+u32(4)+u32(3)+u32(0)+costs({"Raw Food":2})+f32(0.10)+u32(2)+bytes(7)
stockpot_recipe=gid("recipe/FuelledStockpots")
stockpot_inputs={"Raw Food":2,"Coal":1}
stockpot_data=b'\1'+string('NI FuelledStockpots')+stockpot_recipe+u32(1)+req(stockpots)
stockpot_data+=loc('Recipe/FuelledStockpots/Name','Fuelled Stockpots')
stockpot_data+=loc('Recipe/FuelledStockpots/Description','Cook 6 standard rations from 2 raw food and 1 coal in 9 working minutes at full efficiency.')
stockpot_data+=b'\0\0'+food_icon+struct.pack('<4i',0,1,4,4)+standard_flags
stockpot_data+=food_product+u32(1)+u32(6)+u32(3)+u32(0)+costs(stockpot_inputs)+f32(0.15)+u32(2)+bytes(7)
recipes.append((stockpot_recipe,stockpot_data,dict(id="FuelledStockpots",title="Fuelled Stockpots",
    output="Food Rations",amount=6,inputs=stockpot_inputs,hours=0.15,building="Cookhouse")))

from station_recipes import EDGE_RECIPES, attach_recipes, build_station_recipes
station_recipes, station_targets = build_station_recipes(
    technology,BP,TECH,RES,gid,loc,costs,req,{"heating":HEATING,"food":FOOD,"exploration":EXPLORATION})
recipes.extend(station_recipes)

from field_operations import build_operations
_, timed_modifiers, _, suspended_actions = build_operations(
    technology,TECH,SRC,gid,loc,costs,req,HEATING,EXPLORATION)
# Preserve the existing technology and modifier IDs for saves. The engine
# rejects the extended ability config, so ship the native config and actions.
suspended_ids = {action['id'] for action in suspended_actions}
new_modifiers=(u32(struct.unpack_from('<I',new_modifiers)[0]+len(timed_modifiers))
               +b''.join(timed_modifiers)+new_modifiers[4:])

assert {(tab,key,col) for tab,columns in research_columns.items() for key,col in columns.items()} <= {
    (tech['category'],tech['id'],tech['column']) for tech in specs
}

old_category_count=struct.unpack_from('<I',TC,0)[0]
tech_count_pos=techinfo[0]['start']-4
last=techinfo[-1];last_cost_end=last['tail']+36+last['costcount']*20
tech_end=last_cost_end+4+41
assert TC[tech_end:tech_end+4]==u32(4)
category=b'\1'+string('City Mastery')+MASTERY+loc('CityMastery/Tab','City Mastery')+u32(0)
sets=research_curve(TC[tech_end:])
from last_autumn import AUTUMN_TABS
from on_the_edge import EDGE_SHARED
from mastery_expansion import EDGE_COMPATIBLE
from industry_housing import EDGE_ADDITIONS
trade_ids={"ScrapRecovery","DeepScrapRecovery","FuelledStockpots"}
autumn_categories = {category.hex() for category in AUTUMN_TABS.values()}
retired = {
    'StormShutters','CavityWalls','ThermalVestibules','DeepHouseLagging','HouseHeat2',
    'AutumnFabricationKits','AutumnVentilationKits','AutumnDockTimber',
    'AutumnKitchenKits','AutumnHarbourKits','AutumnCanvasPatterns',
}
edge_ids = {spec['id'] for spec in specs if spec['id'].startswith('Edge')}
assert len(edge_ids)==16 and (EDGE_SHARED | EDGE_COMPATIBLE | EDGE_ADDITIONS) <= {spec['id'] for spec in specs}
supported_sets = ['TechHaven','Winterhome','Default','Default_Endless_Builders','Default_Endless','Refugees','Builders','Reconquest']
scenario_additions = {}
for name in supported_sets:
    marker=b'\1\1'+name.encode()+b'\0';p=sets.index(marker)+len(marker)+16
    n=struct.unpack_from('<I',sets,p)[0];end=p+4+n*16
    assert n<200
    members = {sets[i:i+16] for i in range(p+4,end,16)}
    additions = []
    for spec in specs:
        # Keep retired and suspended definitions registered for saves.
        if spec['id'] in retired or spec['id'] in suspended_ids:
            continue
        if (name == 'Builders') != (spec['category'] in autumn_categories):
            continue
        if name == 'Reconquest':
            if spec['id'] not in EDGE_SHARED | EDGE_COMPATIBLE | EDGE_ADDITIONS | EDGE_OPENING | EDGE_RESOURCEFUL | EDGE_GAMEPLAY | EDGE_RECIPES | edge_ids | trade_ids:
                continue
        elif spec['id'] in edge_ids:
            continue
        if spec['id'] == 'StarterHuntingKits' and TECH['F 1_HuntersUpgrade'] not in members:
            continue
        if not all(bytes.fromhex(g) in members for g in spec['requires']):
            assert spec['id'] in {'HuntingTrails','HuntingSleds','FlightRigs','ConvoyBearings','ConvoyRelays',
                                  'HangarCargoSlings','OutpostDispatch','HuntersFieldKits',OUTPOST_TECH}, (name,spec['id'],'missing prerequisite')
            continue
        item = bytes.fromhex(spec['guid'])
        additions.append(item)
        members.add(item)
    scenario_additions[name] = [item.hex() for item in additions]
    sets=sets[:p]+u32(n+len(additions))+sets[p+4:end]+b''.join(additions)+sets[end:]
newTC=u32(old_category_count+1)+TC[4:tech_count_pos]+category+u32(len(techinfo)+len(newtechs))+TC[tech_count_pos+4:tech_end]+b''.join(newtechs)+sets

# Increase actual kiln batch yields on its three existing production recipes.
for name, before, after in [('CharcoalKiln_Coal',21,28),('CharcoalKiln_Coal2',28,35),('CharcoalKiln_Coal3',28,42)]:
    marker = b'\1\1'+name.encode()+b'\0'
    start = BP.index(marker)
    end = BP.index(b'\1\1'+({'CharcoalKiln_Coal':'CharcoalKiln_Coal2','CharcoalKiln_Coal2':'CharcoalKiln_Coal3',
                             'CharcoalKiln_Coal3':'Canteen_FoodRations_standard'}[name]).encode()+b'\0',start+len(marker))
    header = b'\1FrostpunkResourceProduct\0'+u32(1)+RES['Coal']
    pos = BP.index(header,start,end)+len(header)
    assert BP[pos:pos+32]==u32(before)+u32(0)+costs({'Wood':7}),name
    BP = BP[:pos]+u32(after)+BP[pos+4:]
for key, description in [
    ('KilnUpgrade', 'Charcoal Kilns now produce 35 coal per 7 wood.'),
    ('KilnUpgrade2', 'Charcoal Kilns now produce 42 coal per 7 wood and finish each batch in 45 minutes at full efficiency.'),
]:
    texts[f'Technologies/{key}/Description'] = description
    texts[f'Technologies/{key}/ShortDescription'] = description

# Production blueprints are the first vector; extraction blueprints follow.
bp_endprod=BP.index(b'\1\1CoalMine_Coal\0')-4
assert struct.unpack_from('<I',BP,bp_endprod)[0]<100
newBP=u32(struct.unpack_from('<I',BP,0)[0]+len(recipes))+BP[4:bp_endprod]+b''.join(x[1] for x in recipes)+BP[bp_endprod:]

# Increase the core stockpile allowance.
newEC=economy
p=newEC.index(b'\1\1Steam Cores\0')+len(b'\1\1Steam Cores\0')+16
assert struct.unpack_from('<I',newEC,p)[0]==50
newEC=newEC[:p]+u32(10000)+newEC[p+4:]

# Add the Factory recipes to its native queue. Remove its one-core construction
# requirement so a city with zero remaining cores can still bootstrap production.
factory_path='gameentities/buildings/resourceprocessing/prefabfactory.binarytemplate'
factory=(SRC/'templates'/factory_path).read_bytes()
pc=factory.index(b'\1FrostpunkProductionComponentTemplate\0')+len(b'\1FrostpunkProductionComponentTemplate\0')+16
n=struct.unpack_from('<I',factory,pc)[0];assert n==9
pe=pc+4+n*16
factory_recipes=[x[0] for x in recipes if x[2].get('building','Factory')=='Factory']
factory=factory[:pc]+u32(n+len(factory_recipes))+factory[pc+4:pe]+b''.join(factory_recipes)+factory[pe:]
ec=factory.index(b'\1FrostpunkBuildingEconomicsComponentTemplate\0')+len(b'\1FrostpunkBuildingEconomicsComponentTemplate\0')+16
assert factory[ec:ec+4]==u32(3)
factory=factory[:ec]+costs({'Wood':80,'Steel':60})+factory[ec+4+3*20:]

cookhouse_path='gameentities/buildings/resourceprocessing/foodprocessing.binarytemplate'
cookhouse=(SRC/'templates'/cookhouse_path).read_bytes()
pc=cookhouse.index(b'\1FrostpunkProductionComponentTemplate\0')+len(b'\1FrostpunkProductionComponentTemplate\0')+16
assert cookhouse[pc:pc+4]==u32(5)
pe=pc+4+5*16
cookhouse=cookhouse[:pc]+u32(6)+cookhouse[pc+4:pe]+stockpot_recipe+cookhouse[pe:]

def update_lang(b):
    assert struct.unpack_from('<I',b,0)[0]==len(b)-4
    count=struct.unpack_from('<I',b,4)[0];p=8;table={}
    for _ in range(count):
        n=struct.unpack_from('<H',b,p)[0];p+=2;k=b[p:p+n];p+=n
        n=struct.unpack_from('<H',b,p)[0];p+=2;v=b[p:p+n*2];p+=n*2;table[k]=v
    assert p==len(b),(p,len(b))
    table.update({k.encode():v.encode('utf-16-le') for k,v in texts.items()})
    chunks=[u32(len(table))]
    for k,v in sorted(table.items()):
        a=k;c=v;chunks.append(struct.pack('<H',len(a))+a+struct.pack('<H',len(c)//2)+c)
    payload=b''.join(chunks)
    return u32(len(payload))+payload

scenarios_path='configs/frostpunkscenariosconfig.bin'
patches={
 'common':{'configs/frostpunktechnologiesconfig.bin':newTC,'configs/frostpunkblueprintsconfig.bin':newBP,'configs/frostpunkeconomyconfig.bin':newEC,mods_path:new_modifiers},
 'templates':{factory_path:factory,cookhouse_path:cookhouse},'localizations':{}}
patches['common'][scenarios_path]=starting_supplies((SRC/'common'/scenarios_path).read_bytes(),RES)
for path, additions in station_targets.items():
    patches['templates'][path]=attach_recipes((SRC/'templates'/path).read_bytes(),additions)
for p in (SRC/'localizations').glob('*.lang'):
    patches['localizations'][p.name]=update_lang(p.read_bytes())

from archive import NAMES
manifest={'name':'Frostpunk: New Industry','version':'3.7.0','game_path':str(INSTALL_PATH),'technology_sets':supported_sets,'scenario_additions':scenario_additions,'retired_technologies':sorted(retired),'archives':{},'technologies':specs,'recipes':[x[2] for x in recipes],'field_operations':[],'suspended_field_operations':suspended_actions,'opening_stock_bonus':OPENING_STOCK,'base_research_multiplier':RESEARCH_SPEED,'sources':['https://github.com/Mystik738/frostract']}
for base,files in patches.items():
    records=entries(base);byname={NAMES.get(e[1]):e for e in records};items=[]
    with (GAME/(base+'.dat')).open('rb') as src:
        for name,newdata in files.items():
            e=byname[name];original=read(src,e)
            assert original!=newdata
            payload=f'{base}-{e[1]:08x}.bin.gz';(PAY/payload).write_bytes(gzip.compress(newdata,compresslevel=9,mtime=0))
            items.append({'name':name,'hash':e[1],'payload':payload,'original_sha256':hashlib.sha256(original).hexdigest(),'new_sha256':hashlib.sha256(newdata).hexdigest(),'size':len(newdata)})
    manifest['archives'][base]={'entries':items,'original_files':{ext:hashlib.file_digest((GAME/(base+ext)).open('rb'),'sha256').hexdigest() for ext in ['.dat','.idx']}}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(f'Built {len(newtechs)} technologies, {len(recipes)} recipes, {len(texts)} text entries in {len(patches["localizations"])} languages.')
print('Payload bytes:',sum(p.stat().st_size for p in PAY.iterdir()))


