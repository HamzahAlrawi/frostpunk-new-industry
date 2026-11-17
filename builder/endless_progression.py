"""Reconstruction: native, save-persistent Endless projects and supply routes.

Content is data first. The compiler below emits only known native event, quest
and dilemma classes. No Lua, DLL, executable or ability-component patch is used.
"""
import struct
from tools.endless_schema import Parameter,append_parameter,append_modes
from tools.native_scenario import (validate_native_samples,event,append_directory,mode_selected,
    set_variable,equals,affordable,change_resource,delayed,guarded,dilemma,start_quest,
    progress_quest,apply_modifier,predefined)
from research_curation import modifiers,normalized,pack_modifiers
from city_mastery import building_ids


PROJECTS = (
    ('Surveyors Camp',{'Wood':300,'Steel':150,'Coal':500,'Food Rations':100},
     'Open a permanent surveying camp. Establish the reconstruction ledger and earn a large Hope increase.',None),
    ('Frostland Storehouses',{'Wood':900,'Steel':600,'Coal':1500,'Food Rations':400},
     'Build a regional reserve network. Both Resource Depot sizes gain 100% capacity for every stored resource.','storage'),
    ('Engineers Exchange',{'Wood':1800,'Steel':1400,'Coal':4000,'Food Rations':900,'Steam Cores':8},
     'Found a technical exchange. Workshops gain 75% workplace efficiency.','research'),
    ('Refuge Clinics',{'Wood':3500,'Steel':2500,'Coal':8000,'Food Rations':1800,'Steam Cores':20},
     'Equip the relief clinics. Medical Posts, Infirmaries and Houses of Healing gain 100% workplace efficiency.','medical'),
    ('The Great Foundry',{'Wood':5500,'Steel':5000,'Coal':16000,'Food Rations':2500,'Steam Cores':40},
     'Connect the city to a new foundry complex. Steelworks and Factories gain 75% workplace efficiency.','industry'),
    ('Sheltered Roads',{'Wood':9000,'Steel':8000,'Coal':25000,'Food Rations':5000,'Steam Cores':70},
     'Enclose the reconstruction supply roads. Every building with insulation gains one insulation level.','warmth'),
    ('Seed Conservatory',{'Wood':15000,'Steel':12000,'Coal':40000,'Food Rations':9000,'Steam Cores':110},
     'Found a seed reserve. Hothouses, Industrial Hothouses and Cookhouses gain 75% workplace efficiency.','food'),
    ('Continental Reserve',{'Wood':22000,'Steel':18000,'Coal':65000,'Food Rations':14000,'Steam Cores':180},
     'Open deep supply vaults. Both Resource Depot sizes gain a further 100% capacity.','storage2'),
    ('Relay Citadels',{'Wood':32000,'Steel':28000,'Coal':95000,'Food Rations':20000,'Steam Cores':280},
     'Equip permanent relay settlements. Coal mines, sawmills and wall drills gain 75% workplace efficiency.','extraction'),
    ('Polar Sanctuary',{'Wood':45000,'Steel':42000,'Coal':140000,'Food Rations':30000,'Steam Cores':450},
     'Complete an inhabited refuge beyond the city. Cold-related illness is reduced by 25%.','health'),
    ('The Northern Railway',{'Wood':60000,'Steel':70000,'Coal':200000,'Food Rations':45000,'Steam Cores':750},
     'Lay the final railway across the Frostland. All heat zones gain 25% radius.','radius'),
    ('A World Rebuilt',{'Wood':80000,'Steel':100000,'Coal':250000,'Food Rations':60000,'Steam Cores':1200},
     'Complete the reconstruction programme. All workplaces gain 75% efficiency. Relief routes and contracts continue indefinitely.','all'),
)

ROUTES = (
    ('Foundry','Foundry Settlement',{'Coal':1600,'Food Rations':200}, {'Steel':600}),
    ('Gardens','Sheltered Gardens',{'Wood':500,'Coal':800,'Steel':200}, {'Food Rations':1000}),
    ('Salvage','Salvage Anchorage',{'Steel':400,'Food Rations':250}, {'Wood':1200,'Steam Cores':2}),
)
CONTRACTS = (
    ('Industrial','Industrial Reserve',{'Coal':3000,'Steel':700,'Steam Cores':2},{'Wood':900,'Food Rations':450}),
    ('Relief','Emergency Provisioning',{'Food Rations':1200,'Wood':600,'Coal':1200},{'Steel':1000,'Steam Cores':4}),
    ('Engineering','Engineering Expedition',{'Wood':1000,'Steel':1000,'Steam Cores':4},{'Coal':6000,'Food Rations':600}),
)


def budget_text(items):
    return ', '.join(f'{value:,} {name.lower()}' for name,value in items.items())


def content():
    """Stable per-track state IDs; repeating states alternate to reject old timers."""
    tracks=[]
    projects=[]
    for index,(title,cost,description,reward) in enumerate(PROJECTS,1):
        projects.append(dict(state=index,title=title,cost=cost,description=description,
                             reward=reward,next=index+1 if index<len(PROJECTS) else 99,cooldown=0.5))
    tracks.append(dict(id='Projects',start=0.5,initial=1,stages=projects))
    for route_index,(key,title,base,cargo) in enumerate(ROUTES):
        stages=[]
        for level,multiplier in enumerate((1,3,8,20,50),1):
            for side in range(2):
                state=level*2+side
                stages.append(dict(state=state,title=f'{title} - Route {level}',
                    cost={k:v*multiplier for k,v in base.items()},
                    cargo={k:v*multiplier for k,v in cargo.items()},
                    description=f'Sustain {title.lower()}. Dispatch supplies for a return shipment one day later. Completed route infrastructure survives a missed delivery.',
                    next=(level+1)*2 if level<5 else level*2+(1-side),
                    failure=level*2+(1-side),deadline=8 if level>1 else None,cooldown=7))
        tracks.append(dict(id=key,start=2+route_index*3,initial=2,stages=stages))
    stages=[]
    for level,multiplier in enumerate((1,3,8,20,50,100),1):
        for flavor,(key,title,base,cargo) in enumerate(CONTRACTS):
            next_flavor=(flavor+1)%len(CONTRACTS)
            stages.append(dict(state=level*10+flavor,title=f'{title} - Grade {level}',
                cost={k:v*multiplier for k,v in base.items()},cargo={k:v*multiplier for k,v in cargo.items()},
                description='An optional industrial contract. Accept for a three-day deadline, or pass without penalty. Payment earns the listed return shipment and a harder commission.',
                next=min(level+1,6)*10+next_flavor,failure=level*10+next_flavor,
                deadline=3,cooldown=7,optional=True))
    tracks.append(dict(id='Contracts',start=3,initial=10,stages=stages))
    return tracks


def rewards(data,buildings,techinfo,guid):
    """Known native global/place modifiers, with explicit human/automaton parity."""
    records=modifiers(data);places=building_ids(buildings)
    neutral=bytearray(normalized(records['d87b131d3367ed86d04efc1f7c1f7a5a'][2]))
    assert len(neutral)==186 and struct.unpack_from('<I',neutral,77)[0]==0
    struct.pack_into('<f',neutral,150,0)
    place=bytearray(normalized(records['30aa2c27e02dce83494392ae5c1f2261'][2]))
    assert len(place)==238
    struct.pack_into('<f',place,173,1)
    native_tech=next(t for t in techinfo if t['name']=='R 2_ResourceDepotUpgrade')
    tail=bytes.fromhex(native_tech['rest'])
    assert tail[:8]==struct.pack('<II',2,0)
    assert struct.unpack_from('<I',tail,8)[0]==2
    storage_id=tail[12+16:12+32].hex()
    storage=normalized(records[storage_id][2])
    marker=struct.pack('<I',8)
    # Eight native per-resource storage scalars; pin the entire vector.
    vector=next(p for p in range(len(storage)) if storage[p:p+4]==marker and
                p+196<=len(storage) and all(storage[q+16:q+24]==struct.pack('<If',0,1.5) for q in range(p+4,p+196,24)))
    def register(key,kind,body):
        identity=guid('endless/reward/'+key).hex()
        assert identity not in records
        records[identity]=[kind,('NI Reconstruction/'+key).encode(),bytes(body)]
        return identity
    owners=[];result={}
    for title,_,description,key in PROJECTS:
        if key is None:continue
        body=bytearray(neutral);site=bytearray(place);names=[]
        if key in ('storage','storage2'):
            site=bytearray(storage)
            for p in range(vector+4,vector+196,24):struct.pack_into('<f',site,p+20,2)
            names=['Resource Depot','Resource Depot Big']
        elif key=='health':struct.pack_into('<f',body,166,0.75)
        elif key=='radius':struct.pack_into('<f',body,69,1.25)
        elif key=='warmth':
            struct.pack_into('<i',site,96,1);names=list(places)
        else:
            struct.pack_into('<ff',site,84,2 if key=='medical' else 1.75,2 if key=='medical' else 1.75)
            names={'research':['Engineers Lab'],'medical':['Medical Post','Ambulatorium','HospitalOfMercy'],
                'industry':['Factory','Iron Ore Mine','SteamIronOreMine','AdvancedOreMine'],
                'food':['Plantation','Steam Plantation','Food Processing'],
                'extraction':['Coal Mine','SteamCoalMine','AdvancedCoalMine','Sawmill','SteamSawmill','WallDrill','WallDrillSteam','WallDrillAdvanced'],
                'all':list(places)}[key]
        if names:
            # Fail the build instead of silently omitting an unrecognised building.
            assert set(names)<=places.keys(),(key,set(names)-places.keys())
            child=register(key+'/places','Place',site)
            pairs=b''.join(places[n]+bytes.fromhex(child) for n in names)
            body=body[:77]+struct.pack('<I',len(names))+pairs+body[81:]
        identity=register(key,'Global',body);result[key]=identity
        owners.append(dict(id='Reconstruction/'+key,title=title,description=description,modifier=identity))
    return pack_modifiers(records),result,owners


def build(source,modifier_data,buildings,techinfo,guid,localize,resources):
    identity=lambda key:guid('endless/'+key).hex()
    enabled=identity('enabled')
    parameter=Parameter('NI Reconstruction',identity('parameter'),[
        dict(name='Disabled',guid=identity('disabled'),default=True,display=None,description=None),
        dict(name='Enabled',guid=enabled,default=False,display=None,description=None)],None,None)
    campaign_values={i:guid('frontiers/campaign/'+str(i)).hex() for i in (1,2,3)}
    campaign_parameter=Parameter('NI Frontier Mode',guid('frontiers/campaign-parameter').hex(),[
        dict(name='None',guid=guid('frontiers/campaign/none').hex(),default=True,display=None,description=None)]+
        [dict(name=name,guid=campaign_values[i],default=False,display=None,description=None)
         for i,name in ((1,'Restoration'),(2,'Whiteout'),(3,'Machine Age'))],None,None)
    mode_definitions=[dict(name=name,title=title,subtitle=subtitle,description=description,value=campaign_values[i])
        for i,name,title,subtitle,description in (
            (1,'Reconstruction','Restoration','Rebuild','Build a capital. Choose its future.'),
            (2,'Whiteout','Whiteout','Endure','Survive the front. Protect the city.'),
            (3,'MachineAge','Machine Age','Automate','Build a working machine commonwealth.'))]
    paths={key:'configs/frostpunk'+key+'config.bin' for key in ('endlessmode','scenarios','gameevents','dilemmas','quests')}
    originals={key:(source/path).read_bytes() for key,path in paths.items()}
    resource_ids={k:v.hex() for k,v in resources.items()}
    dt,qt=validate_native_samples(originals['gameevents'],originals['dilemmas'],originals['quests'],resource_ids)
    modifier_data,bonus_ids,owners=rewards(modifier_data,buildings,techinfo,guid)
    native_effects=(source/'configs/frostpunkeffectsconfig.bin').read_bytes()
    def effect(name):
        token=b'\1\1'+name.encode()+b'\0';at=native_effects.index(token)+len(token)
        return predefined(native_effects[at:at+16].hex())
    hope=effect('GOLD [Common] Hope rise - greatly')
    penalty=effect('GOLD [Common] Discontent rise - slightly')
    tracks=content();events=[];dilemmas=[];quests=[]
    flag=mode_selected(enabled)
    def var(track,field):return 'NI/Reconstruction/'+track+'/'+field
    def cond(track,state,status=None):
        values=[flag,equals(var(track,'stage'),state)]
        if status is not None:values.append(equals(var(track,'status'),status))
        return values
    def setv(track,field,value):return set_variable(var(track,field),value)
    def timer(key,days,effects):return delayed(identity('timer/'+key),days,effects)
    def ready(track,state,key,days):
        return timer(key,days,[guarded(cond(track,state,3),[setv(track,'status',0)])])
    def add_dilemma(key,title,description,choices,small=True):
        records=[]
        for index,(text,detail,conditions,effects) in enumerate(choices):
            records.append(dt.choice('NI '+key+'/'+str(index),identity('choice/'+key+'/'+str(index)),
                text,detail,conditions,effects,localize,'Endless/'+key+'/'+str(index)))
        dilemmas.append(dt.build('NI '+key,identity('dilemma/'+key),title,description,records,localize,'Endless/'+key,small))
        return dilemma(identity('dilemma/'+key))
    def launch(track,stage):
        if stage.get('optional'):
            return [setv(track,'status',4),dilemma(identity('dilemma/'+track+'/'+str(stage['state'])+'/accept'))]
        return activate(track,stage)
    def activate(track,stage):
        state=stage['state'];key=track+'/'+str(state)
        effects=[setv(track,'status',1),start_quest(identity('quest/'+key))]
        if stage.get('deadline'):
            target=stage['failure']
            callback=[guarded(cond(track,state),[setv(track,'status',3),setv(track,'stage',target),penalty,
                ready(track,target,key+'/retry',stage['cooldown'])])]
            effects.append(timer(key+'/deadline',stage['deadline'],callback))
        return effects
    stage_by_track={track['id']:{stage['state']:stage for stage in track['stages']} for track in tracks}
    for track in tracks:
        key=track['id']
        for stage in track['stages']:
            state=stage['state'];root=key+'/'+str(state);qid=identity('quest/'+root)
            events.append(event('NI Reconstruction Start '+root,identity('event/start/'+root),identity('trigger/start/'+root),
                cond(key,state,0),launch(key,stage),0.25))
            price=budget_text(stage['cost']);cargo=stage.get('cargo',{})
            details=stage['description']+'\n\nDispatch: '+price+'.'
            if cargo:details+='\nReturn cargo after one day: '+budget_text(cargo)+'.'
            if stage.get('deadline'):details+=f"\nDeadline: {stage['deadline']} days. A missed accepted delivery raises Discontent slightly; the route or contract will be offered again."
            else:details+='\nNo deadline.'
            quests.append(qt.build('NI '+root,qid,identity('objective/'+root),stage['title'],price,localize,'Endless/Quest/'+root,stage.get('deadline')))
            target=stage['next'];effects=[setv(key,'status',3)]
            effects.extend(change_resource(resource_ids[name],-amount) for name,amount in stage['cost'].items())
            effects.extend([progress_quest(qid,'Dispatch'),setv(key,'stage',target),hope])
            if stage.get('reward'):effects.append(apply_modifier(bonus_ids[stage['reward']]))
            if cargo:effects.append(timer(root+'/cargo',1,[change_resource(resource_ids[name],amount) for name,amount in cargo.items()]))
            if target!=99:
                effects.append(ready(key,target,root+'/next',stage['cooldown']))
            else:
                effects.append(add_dilemma('Completion','A World Rebuilt',
                    'The twelve reconstruction projects are complete. Your city has rebuilt a permanent foothold in the Frostland. Relief routes and industrial contracts continue indefinitely.',
                    [('We carry on.','The city remains playable.',[],[])],False))
            checks=cond(key,state,2)+[affordable(resource_ids[name],amount) for name,amount in stage['cost'].items()]
            later=[guarded(cond(key,state,2),[setv(key,'status',3),timer(root+'/later',0.5,[guarded(cond(key,state,3),[setv(key,'status',1)])])])]
            offer=add_dilemma(root+'/pay',stage['title'],details,
                [('Dispatch supplies',price,checks,effects),('Later','Keep all supplies. Offer again in twelve hours.',[],later)])
            events.append(event('NI Reconstruction '+root,identity('event/'+root),identity('trigger/'+root),
                cond(key,state,1)+checks[3:],[setv(key,'status',2),offer],0.25))
            if stage.get('optional'):
                fail=stage['failure']
                passed=[setv(key,'status',3),setv(key,'stage',fail),ready(key,fail,root+'/pass',stage['cooldown'])]
                add_dilemma(root+'/accept',stage['title'],details,
                    [('Accept contract','The three-day deadline begins now.',cond(key,state,4),activate(key,stage)),
                     ('Pass','No penalty. A new offer arrives in seven days.',[],[guarded(cond(key,state,4),passed)])])
    intro=add_dilemma('Introduction','Reconstruction',
        'The city can do more than survive. Rebuild the Frostland through twelve permanent megaprojects, three expanding relief routes and optional industrial contracts.\n\nThe quest tracker lists each active delivery and its exact budget. A dispatch offer appears once all supplies are in storage. Dispatch is always your choice. Projects have no deadline; established routes allow eight days, accepted contracts three. Return cargo arrives one day after dispatch.\n\nRelief routes and contracts continue after the final project. All progress is saved with this city.',
        [('Begin reconstruction','Projects begin immediately; the first relief route opens on day three.',[],[])],False)
    effects=[set_variable('NI/Reconstruction/initialized',1),timer('intro',0.3,[intro])]
    for track in tracks:
        key=track['id'];initial=track['initial']
        effects.extend([setv(key,'stage',initial),setv(key,'status',3),ready(key,initial,key+'/initial',track['start'])])
    events.insert(0,event('NI Reconstruction Initialize',identity('event/init'),identity('trigger/init'),
        [flag,equals('NI/Reconstruction/initialized',0),equals('NI/Frontiers/version',-1)],effects))
    from frontier_campaigns import build as build_campaigns
    fe,fd,fq,modifier_data,fo,frontiers=build_campaigns(source,modifier_data,buildings,techinfo,guid,localize,resources,dt,qt,enabled,tracks,campaign_values)
    from last_signal import build as build_story
    from tools.story_schema import register
    story_id=lambda key:guid('last-signal/'+key).hex()
    se,sd,sq,story=build_story(source,buildings,techinfo,resources,story_id,frontiers['bonuses'],localize,dt,qt)
    events=fe+se+events;dilemmas+=fd+sd;quests+=fq+sq;owners+=fo
    story_directory='09e8fe41e1464e8d284bec7c9373e8f5'
    assert b'\1\1CustomScenarioEvents\0'+bytes.fromhex(story_directory) in originals['gameevents']
    scenarios=register(originals['scenarios'],story_id,story_directory,localize)
    revised={paths['endlessmode']:append_modes(originals['endlessmode'],mode_definitions,enabled,localize),
        paths['scenarios']:append_parameter(append_parameter(scenarios,parameter),campaign_parameter),
        paths['gameevents']:append_directory(originals['gameevents'],'CustomScenarioEvents','Scenario Builders Quest',events),
        paths['dilemmas']:append_directory(originals['dilemmas'],'CustomScenario','Winterhome Scenario',dilemmas),
        paths['quests']:append_directory(originals['quests'],'CustomScenarios','Scenario Builders',quests)}
    metadata=dict(id='Reconstruction',parameter=parameter.guid,enabled=enabled,disabled=identity('disabled'),
        tracks=tracks,rewards=owners,events=len(events),dilemmas=len(dilemmas),quests=len(quests),
        poll_days=0.25,description='Three separate Endless modes with automatic chapters and timed incidents.',frontiers=frontiers,
        campaign_parameter=campaign_parameter.guid,campaign_values=campaign_values,modes=mode_definitions,story=story)
    return revised,modifier_data,owners,metadata
