"""Three branching city campaigns, automatic missions and a crisis director."""
import re
import struct
from city_mastery import building_ids
from research_curation import modifiers,normalized,pack_modifiers
from tools.native_binary import u32,f32,string
from tools.native_scenario import (typed,event,equals,compare,variable,integer,affordable,
    set_variable,change_resource,apply_modifier,predefined,delayed,guarded,dilemma,
    start_quest,progress_quest,amount)
from tools.mission_schema import MissionWriter,completed_event
from frontier_expansion import DOCTRINES,FRONT_DAYS,FRONT_HEAT,extend

PREFIX='NI/Frontiers/'
GROUPS={
    'homes':['Tent','Bunkhouse','House'],
    'housing':['House'],
    'medical':['Medical Post','Ambulatorium','HospitalOfMercy'],
    'industry':['Factory','Iron Ore Mine','SteamIronOreMine','AdvancedOreMine'],
    'food':['Food Processing','Plantation','Steam Plantation'],
    'workshops':['Engineers Lab'],
    'extraction':['Sawmill','SteamSawmill','WallDrill','WallDrillSteam','WallDrillAdvanced',
                  'Coal Mine','SteamCoalMine','AdvancedCoalMine','CoalThumper','CoalThumperSteam'],
    'civic':['PublicHouse','FightClube','CareHouse','HouseOfPrayer','Temple','FaithKeepers',
             'Neighborhood watch tower','Guardpost','Prison','Shrine','HospitalOfMercy'],
}


def build_goal(text,names,quantity=1):return dict(kind='build',text=text,names=names,quantity=quantity)
def tech_goal(text,name):return dict(kind='research',text=text,technology=name)
def produce_goal(quantity):return dict(kind='produce',text=f'Manufacture {quantity} new automatons',quantity=quantity)
def automate_goal(fraction):return dict(kind='automate',text=f'Assign automatons to more than {fraction:.0%} of workplaces',quantity=fraction)


def campaigns():
    saw=['Sawmill','SteamSawmill'];steel=['Iron Ore Mine','SteamIronOreMine','AdvancedOreMine']
    med=GROUPS['medical'];coal=['Coal Mine','SteamCoalMine','AdvancedCoalMine','CoalThumper','CoalThumperSteam']
    return extend([
      dict(id=1,key='Restoration',title='The Restoration',
        description='Build a regional capital. Choose civic self-sufficiency or industrial expansion, develop real districts and prove the city can sustain them.',
        branches=[dict(title='Civic Commonwealth',description='Homes and civic buildings gain +1 insulation; healthcare gains 100% efficiency. Industry loses 15% efficiency. No upkeep.',bonus='civic'),
                  dict(title='Industrial League',description='Factories and Steelworks gain 100% efficiency; Workshops gain 75%. Upkeep: 150 coal and 10 steel every six hours. Bonuses pause if supplies run short.',bonus='league',upkeep={'Coal':150,'Steel':10},period=0.25)],
        missions=[
          dict(phase=1,title='A functioning settlement',goals=[build_goal('Build a Workshop',['Engineers Lab']),build_goal('Build a healthcare workplace',med),build_goal('Build a Cookhouse',['Food Processing'])]),
          dict(phase=2,title='Build the supply chains',goals=[build_goal('Build a Sawmill or Steam Sawmill',saw),build_goal('Build a Steelworks',steel),tech_goal('Research Drawing Boards','01_TierUnlock 1')]),
          dict(phase=3,path=1,title='The civic quarter',goals=[build_goal('Build four Houses',['House'],4),build_goal('Build an Infirmary',['Ambulatorium']),build_goal('Build a Hothouse',['Plantation','Steam Plantation'])]),
          dict(phase=3,path=2,title='The industrial quarter',goals=[build_goal('Build a Factory',['Factory']),produce_goal(2),tech_goal('Research Steam Core Fabrication (Industry, tier II)','mod:Cores1')]),
          dict(phase=4,path=1,title='A healthy city',goals=[build_goal('Build two Infirmaries',['Ambulatorium'],2),tech_goal('Research Healthcare Insulation','F 6_Healthcare Buildings - warmer'),build_goal('Build a Public House',['PublicHouse'])]),
          dict(phase=4,path=2,title='Mechanise the frontier',goals=[produce_goal(4),build_goal('Build a Wall Drill',['WallDrill','WallDrillSteam','WallDrillAdvanced']),tech_goal('Research Automaton Integration','E 4_Automaton Efficiency')]),
          dict(phase=5,title='The regional capital',goals=[build_goal('Build two Large Resource Depots',['Resource Depot Big'],2),build_goal('Build eight Houses',['House'],8),tech_goal('Research Difference Engine','04_TierUnlock4')]),
          dict(phase=6,title='Prove the capital can endure',checks=12,reserves={'Coal':10000,'Wood':3000,'Steel':3000,'Food Rations':4000,'Steam Cores':10},goals=[])]),
      dict(id=2,key='Whiteout',title='The Whiteout',
        description='Four thermal fronts arrive 2, 5, 9 and 13 days after the city begins. Build redundant heating and healthcare, choose how to protect the city, then keep the Generator and storm reserves running.',
        branches=[dict(title='Emergency Heat Grid',description='Every insulated building gains +2 insulation. Upkeep: 250 coal every six hours. The extra heat pauses when fuel is unavailable.',bonus='grid',upkeep={'Coal':250},period=0.25),
                  dict(title='Shelter Network',description='Homes, healthcare and civic buildings gain +3 insulation. Workshop efficiency falls by 20%. Industry gets no extra heat. No upkeep.',bonus='shelter')],
        missions=[
          dict(phase=1,title='Prepare the emergency services',goals=[build_goal('Build two Workshops',['Engineers Lab'],2),build_goal('Build two healthcare workplaces',med,2),build_goal('Build four homes',GROUPS['homes'],4)]),
          dict(phase=2,title='Establish heat redundancy',goals=[tech_goal('Research Steam Hubs','H 1_SteamHub'),build_goal('Build two Steam Hubs',['Steam Hub'],2),tech_goal('Research Generator Power Upgrade I','H 2_Generator Upgrade - power 1')]),
          dict(phase=3,title='Protect the vulnerable',goals=[build_goal('Build six Houses',['House'],6),build_goal('Build an Infirmary',['Ambulatorium']),tech_goal('Research Healthcare Insulation','F 6_Healthcare Buildings - warmer')]),
          dict(phase=4,title='Keep the fuel coming',goals=[build_goal('Build three coal mines or Coal Thumpers',coal,3),produce_goal(2),tech_goal('Research Generator Efficiency Upgrade','H 3_Generator Upgrade - less coal')]),
          dict(phase=5,title='The last heating reserve',goals=[tech_goal('Research House Insulation','F 6_House Insulation'),tech_goal('Research Generator Power Upgrade II','H 4_Generator Upgrade - power 2'),build_goal('Build two Large Resource Depots',['Resource Depot Big'],2)]),
          dict(phase=6,title='Hold through the whiteout',checks=16,reserves={'Coal':12000,'Wood':1500,'Steel':1500,'Food Rations':3500},goals=[])]),
      dict(id=3,key='Commonwealth',title='The Machine Commonwealth',
        description='Create a working automaton economy. Production objectives count new machines, staffing objectives require actual assignments, and the city must finance the system it builds.',
        branches=[dict(title='Closed-loop Industry',description='Industrial and extraction workplaces: automaton efficiency +150%, human efficiency -25%. Upkeep: one Steam Core per day. Bonuses pause without a core.',bonus='closed',upkeep={'Steam Cores':1},period=1),
                  dict(title='Human-machine Partnership',description='Industrial and extraction workplaces: automaton efficiency +75%, human efficiency +50%. Medical workplace efficiency falls by 15%. No upkeep.',bonus='partnership')],
        missions=[
          dict(phase=1,title='Lay the industrial foundations',goals=[build_goal('Build two Workshops',['Engineers Lab'],2),build_goal('Build a Sawmill',saw),build_goal('Build a Steelworks',steel)]),
          dict(phase=2,title='Commission the first machines',goals=[tech_goal('Research the Factory','E 3_Factory'),build_goal('Build a Factory',['Factory']),tech_goal('Research Steam Core Fabrication (Industry, tier II)','mod:Cores1'),produce_goal(2)]),
          dict(phase=3,title='Build the machine workforce',goals=[produce_goal(4),tech_goal('Research Automaton Integration','E 4_Automaton Efficiency')]),
          dict(phase=4,title='Put the machines to work',goals=[automate_goal(0.30),produce_goal(4),build_goal('Build a second Factory',['Factory'],2)]),
          dict(phase=5,title='An autonomous production network',goals=[tech_goal('Research Engineer Automatons','E 5_Automaton Engineers'),automate_goal(0.50),produce_goal(6)]),
          dict(phase=6,title='Sustain the machine commonwealth',checks=8,reserves={},goals=[automate_goal(0.50)])])],
        build_goal,tech_goal,produce_goal,automate_goal)


def bonus_library(data,buildings,guid):
    records=modifiers(data);places=building_ids(buildings);owners=[];ids={}
    neutral=bytearray(normalized(records['d87b131d3367ed86d04efc1f7c1f7a5a'][2]));struct.pack_into('<f',neutral,150,0)
    site=bytearray(normalized(records['30aa2c27e02dce83494392ae5c1f2261'][2]));struct.pack_into('<f',site,173,1)
    def add(key,title,description,groups=(),illness=1,recovery=1):
        body=bytearray(neutral);pairs=[];bindings={}
        for names,human,automaton,heat in groups:
            assert set(names)<=places.keys()
            for name in set(names):
                old=bindings.get(name,(1,1,0));bindings[name]=(old[0]*human,old[1]*automaton,old[2]+heat)
        packages={}
        for name,values in sorted(bindings.items()):packages.setdefault(values,[]).append(name)
        for index,((human,automaton,heat),names) in enumerate(packages.items()):
            value=bytearray(site);struct.pack_into('<ff',value,84,human,automaton);struct.pack_into('<i',value,96,heat)
            identity=guid('frontiers/bonus/'+key+'/'+str(index)).hex()
            records[identity]=['Place',('NI Frontiers/'+key+'/'+str(index)).encode(),bytes(value)]
            pairs.extend(places[n]+bytes.fromhex(identity) for n in names)
        struct.pack_into('<f',body,166,illness)
        assert body[126:130]==f32(1)
        struct.pack_into('<f',body,126,recovery)
        body=body[:77]+u32(len(pairs))+b''.join(pairs)+body[81:]
        identity=guid('frontiers/bonus/'+key).hex();records[identity]=['Global',('NI Frontiers/'+key).encode(),bytes(body)]
        ids[key]=identity;owners.append(dict(id='Frontiers/'+key,title=title,description=description,modifier=identity))
    g=GROUPS;all_names=list(places);warm=list(dict.fromkeys(g['homes']+g['medical']+g['civic']))
    coefficients=(
        [(g['homes']+g['civic'],1,1,1),(g['medical'],1.6,1.6,0),(g['industry'],0.9,0.9,0)],
        [(g['industry'],1.65,1.65,0),(g['workshops'],1.3,1.3,0)],
        [(all_names,1,1,2)],
        [(warm,1,1,2),(g['workshops'],0.85,0.85,0)],
        [(g['industry']+g['extraction'],0.8,1.9,0)],
        [(g['industry']+g['extraction'],1.3,1.4,0),(g['medical'],0.9,0.9,0)],
    )
    for (key,title,description,_),bindings in zip(DOCTRINES,coefficients):
        add(key,title,description,bindings)
    for level,heat in enumerate(FRONT_HEAT,1):
        add('front'+str(level),'Whiteout Thermal Front',f'The current front costs {heat} insulation levels citywide.',[(all_names,1,1,-heat)])
    add('works','Regional Public Works','Wall Drills, Steelworks and healthcare gain 30% efficiency.',
        [(['WallDrill','WallDrillSteam','WallDrillAdvanced','Iron Ore Mine','SteamIronOreMine','AdvancedOreMine']+g['medical'],1.3,1.3,0)])
    add('reservegrid','Reserve Heat Grid','Homes and healthcare gain one insulation level.',
        [(g['homes']+g['medical'],1,1,1)])
    add('machineworks','Independent Machine Works','Extraction and industrial automatons gain 30% efficiency.',
        [(g['industry']+g['extraction'],1,1.3,0)])
    add('signal_homes','Signal: Residential Circuit','Homes and medical wards gain one insulation level. Workshops lose 15% efficiency.',
        [(g['homes']+g['medical'],1,1,1),(g['workshops'],0.85,0.85,0)])
    add('signal_relay','Signal: Relay Circuit','Workshops and extraction gain 25% efficiency. Homes lose one insulation level.',
        [(g['workshops']+g['extraction'],1.25,1.25,0),(g['homes'],1,1,-1)])
    add('signal_ward','Signal: Ward Circuit','Medical wards gain 50% efficiency and two insulation levels. Industry loses 20% efficiency.',
        [(g['medical'],1.5,1.5,2),(g['industry'],0.8,0.8,0)])
    add('signal_heat','Signal: Steam Circuit','Coal extraction gains 40% efficiency. Medical wards lose one insulation level.',
        [(['Coal Mine','SteamCoalMine','AdvancedCoalMine','CoalThumper','CoalThumperSteam'],1.4,1.4,0),(g['medical'],1,1,-1)])
    add('signal_open','Signal: Open Frequency','Hothouses and Cookhouses gain 35% efficiency; industrial workplaces lose 20%.',
        [(g['food'],1.35,1.35,0),(g['industry'],0.8,0.8,0)])
    add('signal_archive','Signal: Archive Frequency','Workshops and Steelworks gain 35% efficiency; Cookhouses lose 20%.',
        [(g['workshops']+['Iron Ore Mine','SteamIronOreMine','AdvancedOreMine'],1.35,1.35,0),(['Food Processing'],0.8,0.8,0)])
    add('quarantine','Emergency Quarantine','For two days: healthcare +100% efficiency; industrial efficiency -35%.',[(g['medical'],2,2,0),(g['industry'],0.65,0.65,0)])
    add('stretch','Stretched Provisions','For two days: food workplace efficiency +100%, cold-related illness +30%.',[(g['food'],2,2,0)],1.3)
    add('engineers','Engineers on Repair Duty','For two days: Factory efficiency +100%; Workshop efficiency -50%.', [(['Factory'],2,2,0),(g['workshops'],0.5,0.5,0)])
    add('retool','New Machine Assemblies','Factory efficiency +75% while the programme runs.',[(['Factory'],1.75,1.75,0)])
    add('rest','Maintenance Shutdown','For two days: Factory efficiency -40%.',[(['Factory'],0.6,0.6,0)])
    add('seal','Sealed Districts','For two days: citywide +2 insulation; industry and food workplace efficiency -25%.',[(all_names,1,1,2),(g['industry']+g['food'],0.75,0.75,0)])
    add('burn','Emergency Fuel Burn','Citywide +3 insulation while the reserve burn lasts.',[(all_names,1,1,3)])
    add('push','Exposed Production Drive','For two days: workplaces +50% efficiency; citywide insulation -1.',[(all_names,1.5,1.5,-1)])
    add('community','Community Service Programme','Homes/civic services +1 insulation; healthcare +50% efficiency.',[(warm,1,1,1),(g['medical'],1.5,1.5,0)])
    add('council','Civic Assembly','Food and healthcare efficiency +75%; industry efficiency -25%.',[(g['food']+g['medical'],1.75,1.75,0),(g['industry'],0.75,0.75,0)])
    add('overclock','Fabrication Drive','Industry efficiency +125%; food workplace efficiency -25%.',[(g['industry'],2.25,2.25,0),(g['food'],0.75,0.75,0)])
    add('relief','Expanded Relief Services','Healthcare +100%, food +75%, industry -25% efficiency.',[(g['medical'],2,2,0),(g['food'],1.75,1.75,0),(g['industry'],0.75,0.75,0)])
    add('care','Consolidated Warm Wards','Healthcare +2 insulation but -25% efficiency; food efficiency +50%.',[(g['medical'],0.75,0.75,2),(g['food'],1.5,1.5,0)])
    coal=['Coal Mine','SteamCoalMine','AdvancedCoalMine','CoalThumper','CoalThumperSteam']
    add('coalshift','Forced Coal Extraction','Coal mine/thumper efficiency +75%; citywide insulation -1.',[(coal,1.75,1.75,0),(all_names,1,1,-1)])
    add('housing','Sheltered Housing Blocks','Homes +3 insulation; industry efficiency -25%.',[(g['homes'],1,1,3),(g['industry'],0.75,0.75,0)])
    add('thermal_kits','Distributed Thermal Kits','Homes, healthcare and civic services gain +3 insulation.',[(warm,1,1,3)])
    add('restcity','Recovery Shifts','All workplace efficiency -35%; cold-related illness -50%.',[(all_names,0.65,0.65,0)],0.5)
    add('driven','Demanded Production Drive','All workplace efficiency +75%; cold-related illness +50%.',[(all_names,1.75,1.75,0)],1.5)
    add('equipment','Protected Work Shifts','All workplace efficiency +25%; citywide insulation +1.',[(all_names,1.25,1.25,1)])
    add('survey','Specialists on Rescue Duty','Industry efficiency +50%; healthcare efficiency -35%.',[(g['industry'],1.5,1.5,0),(g['medical'],0.65,0.65,0)])
    add('servo','Standardised Automation','Industry/extraction: automaton efficiency +100%, human efficiency -35%.',[(g['industry']+g['extraction'],0.65,2,0)])
    add('human','Human Industrial Expertise','Industry/extraction: human efficiency +100%, automaton efficiency -25%.',[(g['industry']+g['extraction'],2,0.75,0)])
    add('shared','Joint Production Standards','Industry/extraction human and automaton efficiency +50%.',[(g['industry']+g['extraction'],1.5,1.5,0)])
    add('masterwork','The Factory Masterwork','Industry efficiency +150%; healthcare efficiency +25%.',[(g['industry'],2.5,2.5,0),(g['medical'],1.25,1.25,0)])
    add('neglect','Emergency Heat Restrictions','Citywide insulation -1; industry efficiency -25%.',[(all_names,1,1,-1),(g['industry'],0.75,0.75,0)])
    add('workprogramme','Factory Repair Programme','Factory efficiency -25% while the repair programme is active.', [(['Factory'],0.75,0.75,0)])
    add('road/public','Public Ward Charter','Homes and medical buildings gain one insulation level.',
        [(g['homes']+g['medical'],1,1,1)])
    add('road/works','Works Council Charter','Coal works and Steelworks gain 35% workplace efficiency.',
        [(coal+['Iron Ore Mine','SteamIronOreMine','AdvancedOreMine'],1.35,1.35,0)])
    add('road/school','School House Repairs','Bunkhouses and Houses gain one insulation level.',
        [(['Bunkhouse','House'],1,1,1)])
    add('road/embargo','Coal Bins Locked','Coal mine and thumper workplace efficiency falls by 35% until the coal dispute ends.',
        [(coal,0.65,0.65,0)])
    add('road/exposed','Loose Steam Joint','All insulated buildings lose two insulation levels during the Long Night.',
        [(all_names,1,1,-2)])
    add('road/braced','Braced Steam Joint','Emergency fittings limit the Long Night’s heat loss to one insulation level citywide.',
        [(all_names,1,1,-1)])
    add('road/home','Home Heating Charter','Homes and medical buildings permanently gain one insulation level.',
        [(g['homes']+g['medical'],1,1,1)])
    add('faultline/ward','Ward Circuit','Homes and medical buildings gain +1 insulation. Coal works, Steelworks and Factories lose 25% efficiency.',
        [(g['homes']+g['medical'],1,1,1),(coal+g['industry'],0.75,0.75,0)])
    add('faultline/works','Works Circuit','Coal works, Steelworks and Factories gain 40% efficiency. Homes lose one insulation level.',
        [(coal+g['industry'],1.4,1.4,0),(g['homes'],1,1,-1)])
    add('faultline/bypass','Shelter Bypass','Cookhouses and medical buildings gain +1 insulation. Workshops lose 30% efficiency.',
        [(['Food Processing']+g['medical'],1,1,1),(g['workshops'],0.7,0.7,0)])
    add('faultline/trip','Main Circuit Tripped','All insulated buildings lose two insulation levels until Generator stress drops to 14%.',
        [(all_names,1,1,-2)])
    add('faultline/accumulator','Pressure Accumulator','Generator stress recovers 35% faster with overdrive off.',
        recovery=1.35)
    add('faultline/isolation','Isolated Return Line','Medical buildings permanently gain one insulation level. Unlocks the surveyed bypass when scouts bring home its route.',
        [(g['medical'],1,1,1)])
    add('faultline/shelters','Relief Kitchens','Cookhouses gain 30% workplace efficiency for the remainder of Faultline.',
        [(['Food Processing'],1.3,1.3,0)])
    add('faultline/ward_crew','Station Medics','Medical buildings gain 25% healing efficiency.',
        [(g['medical'],1.25,1.25,0)])
    add('faultline/works_crew','Station Fitters','Steelworks and Factories gain 25% workplace efficiency.',
        [(g['industry'],1.25,1.25,0)])
    add('faultline/accord','Interdistrict Heating Accord','Homes and medical buildings gain +1 insulation after the shelters join the heating network.',
        [(g['homes']+g['medical'],1,1,1)])
    add('faultline/leak','Broken Mile Leak','All insulated buildings lose one heat level until the emergency repair is complete.',
        [(all_names,1,1,-1)])
    add('faultline/resettled','Reclaimed Steam Lines','Steelworks and Factories gain one insulation level from the dismantled ridge pipe.',
        [(g['industry'],1,1,1)])
    return pack_modifiers(records),ids,owners


def build(source,data,buildings,techinfo,guid,localize,resources,dt,qt,enabled,legacy_tracks,campaign_values):
    identity=lambda key:guid('frontiers/'+key).hex()
    from tools.native_scenario import mode_selected
    flag=mode_selected(enabled);events=[];dilemmas=[];quests=[]
    records,bonuses,owners=bonus_library(data,buildings,guid)
    places={k:v.hex() for k,v in building_ids(buildings).items()};tech={t['name']:t['guid'] for t in techinfo}
    bp=(source/'configs/frostpunkblueprintsconfig.bin').read_bytes();automaton_blueprints=[]
    for name in ('Automatons','CheaperAutomatons','Automatons_upgraded','CheaperAutomatons_upgraded','Automatons_upgraded2','CheaperAutomatons_upgraded2'):
        token=b'\1'+string(name);p=bp.index(token)+len(token);automaton_blueprints.append(bp[p:p+16].hex())
    auto_start=bp.index(b'\1'+string('Automatons'));auto_end=bp.index(b'\1'+string('CheaperAutomatons'),auto_start)
    auto_record=bp[auto_start:auto_end]
    assert auto_record[-11:]==u32(2)+u32(1)+bytes(3)
    automaton_hours=struct.unpack_from('<f',auto_record,len(auto_record)-15)[0]
    assert automaton_hours==4
    writer=MissionWriter((source/'configs/frostpunkquestsconfig.bin').read_bytes(),qt)
    native_effects=(source/'configs/frostpunkeffectsconfig.bin').read_bytes()
    def effect(name):
        token=b'\1'+string(name);p=native_effects.index(token)+len(token);return predefined(native_effects[p:p+16].hex())
    hope=effect('GOLD [Common] Hope rise - moderately');calm=effect('GOLD [Common] Discontent fall - greatly')
    despair=effect('GOLD [Common] Hope fall - moderately');unrest=effect('GOLD [Common] Discontent rise - moderately')
    def eq(name,value):return equals(PREFIX+name,value)
    def setv(name,value,op=0):return set_variable(PREFIX+name,value,op)
    def conditions(campaign=None,phase=None):
        result=[flag]
        if campaign is not None:result.append(eq('campaign',campaign))
        if phase is not None:result.append(eq('phase',phase))
        return result
    def timer(key,days,actions):return delayed(identity('timer/'+key),days,actions)
    def ready_after(key,cid,index):
        return timer('ready/'+key,2,[guarded(conditions(cid)+[eq('alert',0),eq('incident',index)],[setv('ready',1)])])
    def remove(key):return typed('FrostpunkRemoveModifierEffect')+bytes.fromhex(bonuses[key])
    effect_tokens=set()
    def temporary(key,bonus,days):
        token=(int(identity('effect-owner/'+key+'/'+bonus)[:8],16)&0x7fffffff) or 1
        assert token not in effect_tokens;effect_tokens.add(token)
        slot='effect/'+bonus
        return [guarded([compare(variable(PREFIX+slot),4,integer(1))],[remove(bonus)]),
            setv(slot,token),apply_modifier(bonuses[bonus]),
            timer('expiry/'+key,days,[guarded([eq(slot,token)],[remove(bonus),setv(slot,0)])])]
    def paid(cost):return [affordable(resources[n].hex(),v) for n,v in cost.items()]
    def spend(cost):return [change_resource(resources[n].hex(),-v) for n,v in cost.items()]
    def dialog(key,title,description,options,small=True):
        choices=[]
        for i,(text,detail,checks,actions) in enumerate(options):
            # Recheck at effect execution too, so cached/double UI submissions
            # cannot pay twice or sign both mutually exclusive doctrines.
            if checks:actions=[guarded(checks,actions)]
            choices.append(dt.choice('NI Frontiers '+key+'/'+str(i),identity('choice/'+key+'/'+str(i)),text,detail,checks,actions,localize,'Frontiers/'+key+'/'+str(i)))
        dilemmas.append(dt.build('NI Frontiers '+key,identity('dilemma/'+key),title,description,choices,localize,'Frontiers/'+key,small,subtitle='New Frontiers'))
        return dilemma(identity('dilemma/'+key))
    stories=campaigns();mission_meta=[]
    for story in stories:
        cid=story['id'];key=story['key'];opts=[]
        for path,branch in enumerate(story['branches'],1):
            check=conditions(cid,3)+[eq('path',0)]
            first=next(m for m in story['missions'] if m['phase']==3 and m.get('path',path)==path)
            first_key=key+'/3'+('/'+str(path) if first.get('path') else '')
            opts.append((branch['title'],branch['description'],check,
                [setv('path',path),setv('status',1),setv('funded',1),apply_modifier(bonuses[branch['bonus']]),start_quest(identity('quest/'+first_key))]))
            upkeep=branch.get('upkeep')
            if upkeep:
                active=conditions(cid)+[eq('path',path),eq('active',1)]
                charge=event('NI Frontiers upkeep '+key,identity('event/upkeep/'+key),identity('trigger/upkeep/'+key),
                    active+[eq('funded',1)]+paid(upkeep),spend(upkeep),branch['period'])
                # Missing any one resource pauses the whole package once.
                for name,cost in upkeep.items():
                    # Known >= comparator, reversed: cost-1 >= stock.
                    missing=compare(integer(cost-1),4,amount(resources[name].hex()))
                    events.append(event('NI Frontiers pause '+key+'/'+name,identity('event/pause/'+key+'/'+name),identity('trigger/pause/'+key+'/'+name),
                        active+[eq('funded',1),missing],[setv('funded',0),remove(branch['bonus'])],branch['period']))
                events.append(charge)
                events.append(event('NI Frontiers resume '+key,identity('event/resume/'+key),identity('trigger/resume/'+key),
                    active+[eq('funded',0)]+paid({n:v*2 for n,v in upkeep.items()}),
                    [setv('funded',1),apply_modifier(bonuses[branch['bonus']])],0.25))
        branch_offer=dialog('Branch/'+key,'Choose the city you will build',story['description']+'\n\nThis choice changes your city rules and the next objectives. Upkeep is automatic; unfunded bonuses pause and resume when twice the next payment is available.',opts,False)
        events.append(event('NI Frontiers branch '+key,identity('event/branch/'+key),identity('trigger/branch/'+key),
            conditions(cid,3)+[eq('path',0),eq('status',0)],[setv('status',4),branch_offer],0.25))
        quiet=[setv('active',0)]
        for path_number,branch in enumerate(story['branches'],1):
            if branch.get('upkeep'):
                quiet.append(guarded([eq('path',path_number)],[remove(branch['bonus']),setv('funded',0)]))
        extension_gate=conditions(cid,99)+[eq('won',1),eq('expansion',0)]
        dialog('Victory/'+key,story['title']+' - achieved','The founding is complete. A new district proposal is available.',
            [('Keep the frontier active','Continue with incidents and upkeep.',[],[guarded(extension_gate,[setv('active',1)])]),
             ('Let the city breathe','Suspend incidents and paid doctrines.',[],[guarded(extension_gate,quiet)])],False)
        offer=dialog('SecondArc/'+key,'Beyond the founding',
            'The founding chapters are complete. Three new projects build a specialised district and prove it can pay its operating costs. There is no overall deadline; recurring incidents continue.',
            [('Develop the district','Start the next three chapters and keep incidents and doctrine upkeep active.',extension_gate,
              [setv('expansion',1),setv('active',1),setv('phase',7),setv('status',1),setv('checks',0),start_quest(identity('quest/'+key+'/7'))]),
             ('Keep playing without projects','Incidents and any active doctrine upkeep continue if already enabled.',[],[guarded(extension_gate,[setv('expansion',2)])]),
             ('Let the city breathe','Stop new incidents and suspend any doctrine that charges upkeep. Existing deadlines still apply.',[],
              [guarded(extension_gate,[setv('expansion',2)]+quiet)])],False)
        events.append(event('NI Frontiers expansion '+key,identity('event/expansion/'+key),identity('trigger/expansion/'+key),
            extension_gate+[eq('expansion_offered',0)],[setv('expansion_offered',1),offer],0.25))
        ending_gate=conditions(cid,100)+[eq('expansion',3)]
        ending=dialog('DistrictComplete/'+key,'The frontier is here to stay',
            'The district is fully operational. Its permanent reward stays with the city; you can continue with incidents or suspend them.',
            [('Keep the frontier active','Incidents and doctrine upkeep continue.',[],[guarded(ending_gate,[setv('expansion',4)])]),
             ('Let the city breathe','Suspend paid doctrines and new incidents. The district reward remains.',[],
              [guarded(ending_gate,[setv('expansion',4)]+quiet)])],False)
        for mission in story['missions']:
            phase=mission['phase'];path=mission.get('path');mkey=key+'/'+str(phase)+(('/'+str(path)) if path else '')
            qid=identity('quest/'+mkey);goals=[]
            for goal in mission['goals']:
                goal=dict(goal)
                if goal['kind']=='build':goal['target']=[places[n] for n in goal.pop('names')]
                elif goal['kind']=='research':
                    name=goal.pop('technology');goal['target']=guid('tech/'+name[4:]).hex() if name.startswith('mod:') else tech[name]
                elif goal['kind']=='produce':goal['target']=automaton_blueprints
                goals.append(goal)
            if mission.get('checks'):
                reserve=', '.join(f'{v:,} {n.lower()}' for n,v in mission['reserves'].items())
                bill=', '.join(f'{v:,} {n.lower()}' for n,v in mission.get('payment',{}).items())
                goes_cold='Wait for all four fronts. ' if cid==2 and phase==6 else ''
                goals.append(dict(kind='checks',quantity=mission['checks'],text=f"Complete {mission['checks']} operating checks",
                    description=goes_cold+f'Every six game hours: keep the Generator on and retain {reserve}. '
                    +(f'Each successful check spends {bill} above those reserves. ' if bill else 'These reserves are retained. ')
                    +'Checks pause while conditions fail. Doctrine upkeep is separate.'))
            quests.append(writer.build('NI Frontiers '+mkey,qid,story['title']+': '+mission['title'],goals,identity,localize,'Frontiers/Mission/'+mkey))
            gate=conditions(cid,phase)+([eq('path',path)] if path else [])
            if phase>=3:gate.append(compare(variable(PREFIX+'path'),4,integer(1)))
            events.append(event('NI Frontiers start '+mkey,identity('event/start/'+mkey),identity('trigger/start/'+mkey),gate+[eq('status',0)],
                [setv('status',1),start_quest(qid)],0.25))
            actions=[setv('phase',phase+1),setv('status',1),hope]
            if phase==2:actions += [setv('status',4),branch_offer]
            elif phase not in (6,9):
                next_missions=[m for m in story['missions'] if m['phase']==phase+1]
                for target in next_missions:
                    next_key=key+'/'+str(phase+1)+('/'+str(target['path']) if target.get('path') else '')
                    start=start_quest(identity('quest/'+next_key))
                    actions.append(guarded([eq('path',target['path'])],[start]) if target.get('path') else start)
            if phase==6:
                actions=[setv('phase',99),setv('status',2),setv('won',1),hope,calm]
                actions.extend(remove('front'+str(i)) for i in range(1,5))
            elif phase==9:
                actions=[setv('phase',100),setv('status',2),setv('expansion',3),apply_modifier(bonuses[mission['reward']]),hope,calm,ending]
            events.append(completed_event('NI Frontiers complete '+mkey,identity('event/complete/'+mkey),identity('trigger/complete/'+mkey),qid,gate+[eq('status',1)],actions))
            if mission.get('checks'):
                payment=mission.get('payment',{});floor=dict(mission['reserves'])
                for resource,quantity in payment.items():floor[resource]=floor.get(resource,0)+quantity
                check=gate+[eq('status',1),typed('FrostpunkGeneratorIsActiveExpression')+b'\0']+paid(floor)
                if cid==2 and phase==6:check.append(eq('front',4))
                check.append(compare(integer(mission['checks']-1),4,variable(PREFIX+'checks')))
                events.append(event('NI Frontiers operating check '+mkey,identity('event/check/'+mkey),identity('trigger/check/'+mkey),check,
                    spend(payment)+[setv('checks',1,1),progress_quest(qid,'Stability')],0.25))
            mission_meta.append(dict(campaign=cid,phase=phase,path=path,guid=qid,title=mission['title'],goals=goals,
                reserves=mission.get('reserves',{}),payment=mission.get('payment',{}),reward=mission.get('reward')))
    for level,days in enumerate(FRONT_DAYS,1):
        actions=([remove('front'+str(level-1))] if level>1 else [])+[apply_modifier(bonuses['front'+str(level)]),setv('front',level)]
        # Scheduled only by choosing Whiteout; choosing another campaign cannot
        # receive the front. Victory guards reject late callbacks.
        stories[1].setdefault('front_timers',[]).append(timer('front/'+str(level),days,[guarded(conditions(2)+[eq('won',0)],actions)]))
    from frontier_events import content as incident_content
    incidents=incident_content();work_orders=[]
    for cid in (1,2,3):
      for index,item in enumerate(i for i in incidents if i['campaign']==cid):
        if item['options'][-1]['cost'] or item['options'][-1]['repair']:
            fallback=next(i for i,o in enumerate(item['options']) if not o['cost'] and not o['repair'])
            item['options'].append(item['options'].pop(fallback))
        ikey=str(cid)+'/'+str(index);title=item['title'];response=identity('response/'+ikey)
        check=conditions(cid)+[eq('alert',1),eq('incident',index)]
        penalty={1:'restcity',2:'neglect',3:'rest'}[cid]
        penalty_text={1:'workplace efficiency -35% and emergency recovery shifts for two days',2:'citywide insulation -1 and industry efficiency -25% for two days',3:'Factory efficiency -40% for two days'}[cid]
        def expire(key=ikey,bonus=penalty,next_index=(index+1)%6):
            return [setv('alert',0),setv('incident',next_index),unrest,ready_after('failed/'+key,cid,next_index)]+temporary('penalty/'+key,bonus,2)
        def reward(option,key):
            result=[];bonus=option.get('bonus')
            if bonus:result += temporary('effect/'+key,bonus,option['duration'])
            if option.get('cargo'):result.append(timer('cargo/'+key,1,[change_resource(resources[n].hex(),v) for n,v in option['cargo'].items()]))
            if option.get('morale',0)>0:result += [hope,calm]
            elif option.get('morale',0)<0:result.append(despair)
            return result
        quests.append(writer.build('NI Frontiers response '+ikey,response,title+' - response due',
            [dict(kind='checks',label='Decision',quantity=1,text='Choose a response before the deadline',description=f"Respond within {item['response_days']*24:g} game hours. If ignored: {penalty_text}.")],
            identity,localize,'Frontiers/Response/'+ikey,deadline=item['response_days']))
        options=[]
        for number,option in enumerate(item['options']):
            key=ikey+'/'+str(number);cost=option['cost']
            if option['repair']:option['description']+=f' If unfinished: {penalty_text}; Discontent rises moderately.'
            actions=[progress_quest(response,'Decision')]+spend(cost)
            if option['repair']:
                work=identity('work/'+key);pending=conditions(cid)+[eq('alert',2),eq('incident',index)]
                goals=[dict(kind='produce',text=f"Manufacture {option['repair']} new repair automatons",quantity=option['repair'],target=automaton_blueprints)]
                quests.append(writer.build('NI Frontiers work '+key,work,title+' - repair programme',goals,identity,localize,'Frontiers/Work/'+key,deadline=option['work_days']))
                actions += [setv('alert',2),apply_modifier(bonuses['workprogramme']),start_quest(work),
                    timer('work/'+key,option['work_days'],[guarded(pending,[remove('workprogramme')]+expire('work/'+key))])]
                success=dict(option,bonus=option['reward'])
                events.append(completed_event('NI Frontiers repaired '+key,identity('event/repaired/'+key),identity('trigger/repaired/'+key),work,pending,
                    [setv('alert',0),setv('incident',(index+1)%6),remove('workprogramme'),hope,ready_after('repaired/'+key,cid,(index+1)%6)]+reward(success,key)))
                work_orders.append(dict(guid=work,campaign=cid,incident=index,choice=number,quantity=option['repair'],deadline=option['work_days']))
            else:actions += [setv('alert',0),setv('incident',(index+1)%6),ready_after('responded/'+key,cid,(index+1)%6)]+reward(option,key)
            guards=check+paid(cost)
            # Every window has a permanently dismissible free alternative.
            if number==2 and not cost:options.append((option['title'],option['description'],[],[guarded(guards,actions)]))
            else:options.append((option['title'],option['description'],guards,actions))
        offer=dialog('Incident/'+ikey,title,item['description']+f"\n\nRespond within {item['response_days']*24:g} game hours. If ignored: {penalty_text}, and Discontent rises moderately. Repair programmes have their own stated deadline. Cargo arrives one day after resolution.",options)
        item.update(index=index,response_quest=response,dilemma=identity('dilemma/Incident/'+ikey),timeout_bonus=penalty)
        events.append(event('NI Frontiers incident '+ikey,identity('event/incident/'+ikey),identity('trigger/incident/'+ikey),
            conditions(cid)+[eq('active',1),eq('alert',0),eq('incident',index),compare(variable(PREFIX+'phase'),4,integer(3)),
             eq('ready',1)],
            [setv('alert',1),setv('ready',0),start_quest(response),offer,timer('response/'+ikey,item['response_days'],[guarded(check,expire())])],0.25))
    events.append(event('NI Frontiers director migration',identity('event/director'),identity('trigger/director'),
        [flag,eq('version',1),eq('director_version',0)],[setv('director_version',2),setv('ready',0),
            timer('director-migration',2,[setv('ready',1)])],0.25))
    options=[]
    for story in stories:
        actions=[setv('campaign',story['id']),setv('phase',1),setv('status',0),setv('path',0),setv('won',0),
                 setv('active',1),setv('director_version',2),setv('ready',0),setv('incident',0),setv('alert',0),setv('checks',0),setv('front',0),
                 ready_after('initial/'+story['key'],story['id'],0)]+story.pop('front_timers',[])
        actions += [setv('status',1),start_quest(identity('quest/'+story['key']+'/1'))]
        story['opening_actions']=actions
        options.append((story['title'],story['description'],[flag,eq('campaign',0)],actions))
    selection=dialog('Selection','Choose your frontier',
        'Three city campaigns with six chapters each. Construct districts, research the technologies shown in the tracker, manufacture new machines and meet operating conditions. Chapters complete automatically. Each campaign branches into two city doctrines and introduces recurring incidents with real trade-offs.',options,False)
    init=[setv('version',1),setv('campaign',0),set_variable('NI/Reconstruction/initialized',1)]
    for track in legacy_tracks:init += [set_variable('NI/Reconstruction/'+track['id']+'/stage',99),set_variable('NI/Reconstruction/'+track['id']+'/status',3)]
    for story in stories:
        intro=dialog('Opening/'+story['key'],story['title'],story['description']+'\n\nComplete the six founding chapters automatically, then continue this Endless mode with its own recurring incidents and deadlines.',
            [('Begin','The first objectives are already tracked. Event response windows range from 36 hours to five days.',[],[])],False)
        init.append(guarded([mode_selected(campaign_values[story['id']])],story.pop('opening_actions')+[timer('opening/'+story['key'],0.01,[intro])]))
    init.append(timer('selection',0.01,[guarded([eq('campaign',0)],[selection])]))
    events.insert(0,event('NI Frontiers new city',identity('event/init'),identity('trigger/init'),
        [flag,eq('version',0),equals('NI/Reconstruction/initialized',0)],init))
    migration=dialog('Migration','New Endless modes are available',
        'This city began with the earlier supply-dispatch mode. Its deliveries and earned bonuses remain available. Start a new city in Restoration, Whiteout or Machine Age for the new rules and timed events.',
        [('Continue this city','Keep existing project progress. Start a new city for the new campaigns.',[],[setv('version',-1)])],False)
    events.append(event('NI Frontiers existing city',identity('event/migrate'),identity('trigger/migrate'),
        [flag,eq('version',0),equals('NI/Reconstruction/initialized',1)],[setv('version',-1),migration],0.25))
    return events,dilemmas,quests,records,owners,dict(campaigns=stories,missions=mission_meta,bonuses=bonuses,automaton_hours=automaton_hours,
        incidents=incidents,work_orders=work_orders,incident_cooldown_days=2,owned_temporary_effects=True,
        front_days=FRONT_DAYS,front_heat=FRONT_HEAT,selector=identity('dilemma/Selection'))
