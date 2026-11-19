"""Decode actual Reconstruction payloads and audit native state transitions."""
import gzip
import json
import math
from pathlib import Path
import re
import struct
from tools.native_binary import Cursor,SchemaError,string
from tools.endless_schema import parameters,modes
from tools.scenario_reader import event,choice,quest
from tools.scenario_model import World
from tools.native_scenario import DilemmaTemplate

ROOT=Path(__file__).resolve().parents[1]


def appended(original,current,folder,next_folder,expected):
    token=b'\1'+string(folder);count_at=original.index(token)+len(token)+16
    old_count=int.from_bytes(original[count_at:count_at+4],'little')
    end=original.index(b'\1'+string(next_folder),count_at)
    assert current[:count_at]==original[:count_at]
    assert int.from_bytes(current[count_at:count_at+4],'little')==old_count+expected
    assert current[count_at+4:end]==original[count_at+4:end]
    assert current.endswith(original[end:]),'Native directory or tail changed'
    return current[end:len(current)-len(original[end:])]


def decode(original,payload,meta):
    records={}
    folders={'gameevents':('CustomScenarioEvents','Scenario Builders Quest','events'),
             'dilemmas':('CustomScenario','Winterhome Scenario','dilemmas'),
             'quests':('CustomScenarios','Scenario Builders','quests')}
    dt=DilemmaTemplate(original['dilemmas'])
    for key,(folder,next_folder,count_key) in folders.items():
        data=appended(original[key],payload[key],folder,next_folder,meta[count_key]);c=Cursor(data);rows=[]
        for _ in range(meta[count_key]):
            if key=='gameevents':row=event(c)
            elif key=='quests':row=quest(c)
            else:
                name,guid=c.entry();prefix=c.take(dt.choices_at-dt.header_end)
                assert prefix[16:]==dt.source[dt.header_end+16:dt.choices_at]
                assert prefix[:16].hex() in ('0ce922d2839700b94741c2c0ba95d45c','117d01fade7e1a897e8a1e117d01fade')
                choices=[choice(c) for _ in range(c.count(8))]
                # The donor's root tail is preserved, changing only its labels.
                tail=dt.source[dt.choice_end:];literals=re.split(rb'\x01@Generated/[^\0]+\0',tail)
                labels=[]
                for index,literal in enumerate(literals):
                    assert c.take(len(literal))==literal
                    if index+1<len(literals):labels.append(c.string())
                row=dict(name=name,guid=guid,choices=choices,labels=labels)
            rows.append(row)
        assert c.position==len(data),(key,c.position,len(data),'Trailing bytes')
        assert len({row['guid'] for row in rows})==len(rows)
        records[key]=rows
    span,before=parameters(original['scenarios']);after_span,after=parameters(payload['scenarios'])
    assert before==after[:-2] and len(after)==9 and after[-2].guid==meta['parameter'] and after[-1].guid==meta['campaign_parameter']
    from validate_last_signal import validate_registration
    validate_registration(original['scenarios'][:span.start],payload['scenarios'][:after_span.start],meta['story'])
    assert payload['scenarios'][after_span.end:]==original['scenarios'][span.end:]
    original_modes=modes(original['endlessmode'])
    assert payload['endlessmode'][:4]==(6).to_bytes(4,'little')
    assert payload['endlessmode'][4:len(original['endlessmode'])]==original['endlessmode'][4:]
    clone=payload['endlessmode'][len(original['endlessmode']):]
    assert clone.startswith(string('Reconstruction')) and bytes.fromhex(meta['enabled']) in clone
    for mode in meta['modes']:
        assert clone.count(string(mode['name']))==1 and clone.count(bytes.fromhex(mode['value']))==1
    return records


def audit(records,meta,resource_ids):
    events=records['gameevents'];dilemmas={r['guid']:r for r in records['dilemmas']};quests={r['guid']:r for r in records['quests']}
    flag=('mode',meta['enabled'],False)
    story_flag=('scenario',meta['story']['scenario'],False)
    road_flag=('any',[story_flag,('scenario',meta['story']['winter_road']['scenario'],False)])
    faultline_flag=('scenario',meta['story']['faultline']['scenario'],False)
    assert all(e['conditions'][0]==(road_flag if e['name'].startswith('NI Winter Road ')
                                   else faultline_flag if e['name'].startswith('NI Faultline ')
                                   else story_flag if e['name'].startswith(('NI Last Signal ','NI Lifeline ')) else flag)
               and e['enabled'] and e['weight']==1 for e in events)
    assert all(t[0] in ('start','quest','scout_return','construction','signal') or t[2] in (0.25,0.5,1,2)
               or e['name'].startswith('NI Faultline ') and any(math.isclose(t[2],period,rel_tol=1e-6)
                                                              for period in (1/24,1/96))
               for e in events for t in e['triggers'])
    for row in dilemmas.values():
        for c in row['choices']:
            assert c['text'] and c['description'] and c['disabled']
            if any(a[0]=='resource' and a[2][1]<0 for a in c['effects']):
                assert c['conditions'][:3][0]==flag and len(c['conditions'])>=5
                assert c['effects'][0][0]=='set','Lock the offer before spending'
    empty=World(meta['enabled'],events,dilemmas,quests);empty.start();empty.run(20)
    assert not empty.completed and all(v>=0 for v in empty.stock.values())
    assert len(empty.active)<=5,'Only one active objective per track'
    for selected in (None,meta['disabled']):
        world=World(selected,events,dilemmas,quests);world.start();world.run(100)
        assert not world.variables and not world.open and not world.active and not world.queue
    stock={guid:1_000_000_000 for guid in resource_ids.values()}
    world=World(meta['enabled'],events,dilemmas,quests,stock);world.variables['NI/Frontiers/version']=-1;world.start();world.run(200)
    assert world.variables['NI/Reconstruction/Projects/stage']==99
    assert len(world.modifiers)==len([r for r in meta['rewards'] if r['id'].startswith('Reconstruction/')])==11
    assert len(world.completed)>90 and len(world.active)<=5 and len(world.queue)<20
    assert all(world.variables['NI/Reconstruction/'+track['id']+'/stage']>=10 for track in meta['tracks'][1:])
    # Save/load checkpoint with pending timers and open delivery choices.
    saved=World(meta['enabled'],events,dilemmas,quests,stock);saved.variables['NI/Frontiers/version']=-1;saved.start();saved.run(4,False)
    restored=saved.checkpoint();restored.start() # GameStarted must not reset a saved city.
    saved.run(40);restored.run(40)
    assert saved.__dict__==restored.__dict__,'Load changed progress or replayed initialization'
    # Every individual budget is debited exactly once. Repeated/stale clicks fail.
    offers=0
    for guid,row in dilemmas.items():
        if not row['name'].endswith('/pay'):continue
        delivery=row['choices'][0];w=World(meta['enabled'],events,dilemmas,quests,stock)
        for condition in delivery['conditions']:
            if condition[0]=='compare' and condition[2][0]=='variable':w.variables[condition[2][1]]=condition[3][1]
        progress=next(a for a in delivery['effects'] if a[0]=='progress');w.active[progress[1]]=None
        before=dict(w.stock);assert w.click(guid)
        for action in delivery['effects']:
            if action[0]=='resource':assert before[action[1]]-w.stock[action[1]]==-action[2][1]
        paid=dict(w.stock);assert not w.click(guid) and paid==w.stock
        # A prompt opened while affordable becomes unavailable if stock is used elsewhere.
        stale=World(meta['enabled'],events,dilemmas,quests,stock);stale.variables=dict(w.variables)
        for condition in delivery['conditions']:
            if condition[0]=='compare' and condition[2][0]=='variable':stale.variables[condition[2][1]]=condition[3][1]
        first_debit=next(a for a in delivery['effects'] if a[0]=='resource')
        stale.stock[first_debit[1]]=-first_debit[2][1]-1
        assert not stale.click(guid)
        assert stale.click(guid,1),'An obsolete prompt must always be dismissible'
        offers+=1
    # Cooldown graph proves an old deadline cannot target a subsequent occurrence.
    for track in meta['tracks']:
        by={stage['state']:stage for stage in track['stages']}
        for stage in track['stages']:
            if not stage.get('deadline'):continue
            assert stage['next']!=stage['state'] and stage['failure']!=stage['state']
            # Find the fastest possible return to this state under any sequence
            # of successful and failed deliveries, using only cooldown time.
            pending=[(stage['state'],0)];seen={};returns=[]
            while pending:
                state,elapsed=pending.pop()
                if elapsed>=seen.get(state,float('inf')):continue
                seen[state]=elapsed
                for target in {by[state]['next'],by[state]['failure']}:
                    total=elapsed+by[state]['cooldown']
                    if target==stage['state']:returns.append(total)
                    else:pending.append((target,total))
            if returns:assert min(returns)>stage['deadline']
    return dict(passed=True,events=len(events),dilemmas=len(dilemmas),quests=len(quests),
        payment_cases=offers,simulated_days=200,completed_deliveries=len(world.completed),
        original_modes_preserved=3,story_isolation=True,model_checkpoint=True)


def main():
    manifest=json.loads((ROOT/'build/native/manifest.json').read_text());meta=manifest['endless']
    names=('gameevents','dilemmas','quests','scenarios','endlessmode')
    originals={n:(ROOT/'builder/cache/extracted/common/configs'/('frostpunk'+n+'config.bin')).read_bytes() for n in names}
    payload={e['name']:gzip.decompress((ROOT/'build/native/payload'/e['payload']).read_bytes()) for e in manifest['archives']['common']['entries']}
    current={n:payload['configs/frostpunk'+n+'config.bin'] for n in names}
    from faultline_tutorial import PATH as TUTORIAL_PATH
    from faultline_buildings import BUILDINGS_PATH
    structures={row['path'] for row in meta['story']['faultline']['buildings']}
    templates={e['name']:gzip.decompress((ROOT/'build/native/payload'/e['payload']).read_bytes())
               for e in manifest['archives']['templates']['entries'] if e['name'] in structures}
    # Starting-stock edits precede the parameter section and are audited separately.
    from opening_progression import starting_supplies
    resources={k:bytes.fromhex(v) for k,v in manifest['configuration']['resource_ids'].items()}
    originals['scenarios']=starting_supplies(originals['scenarios'],resources)
    decoded=decode(originals,current,meta)
    result=audit(decoded,meta,manifest['configuration']['resource_ids'])
    from validate_tooltips import language_table
    references=set()
    for data in (*current.values(),payload[TUTORIAL_PATH],*templates.values()):
        references.update(match[1:].decode() for match in re.findall(rb'\x01(@Mods/NewIndustry/(?:Endless|Frontiers|LastSignal|Faultline)/[^\0]+)\0',data))
    languages=0
    for item in manifest['archives']['localizations']['entries']:
        table=language_table(gzip.decompress((ROOT/'build/native/payload'/item['payload']).read_bytes()))
        assert all(table.get(key.encode(),b'').strip(b'\0') for key in references),(item['name'],'Missing mode text')
        languages+=1
    assert languages==13
    result.update(localized_references=len(references),language_tables=languages)
    from validate_frontiers import audit as audit_frontiers
    result['frontiers']=audit_frontiers(decoded,meta,manifest['configuration']['resource_ids'])
    from validate_last_signal import audit as audit_story
    result['last_signal']=audit_story(decoded,meta,manifest['configuration']['resource_ids'])
    from validate_lifeline import audit as audit_lifeline
    result['lifeline']=audit_lifeline(decoded,meta,manifest['configuration']['resource_ids'])
    from validate_winter_road import audit as audit_winter
    result['winter_road']=audit_winter(decoded,meta,manifest['configuration']['resource_ids'])
    from validate_faultline import audit as audit_faultline, audit_assets, audit_movie
    from faultline_cinematics import CONFIG as CINEMATICS
    from faultline_models import DESIGNS
    from template_catalog import CATALOG_ASSET, CATALOG_KEY, read_catalog
    from tools.native_mesh import audit_mesh, bounds
    from winter_road_maps import WORLD, WORLD_DONOR
    from tools import archive
    result['faultline']=audit_faultline(decoded,meta,manifest['configuration']['resource_ids'])
    messages, = (e for e in archive.entries('common') if e[1]==archive.murmur(TUTORIAL_PATH.encode()))
    with (archive.GAME/'common.dat').open('rb') as source:
        stock_messages=archive.read(source,messages)
    result['faultline'].update(audit_assets((ROOT/'builder/cache/extracted/common'/BUILDINGS_PATH).read_bytes(),
        payload[BUILDINGS_PATH],stock_messages,payload[TUTORIAL_PATH],templates,meta['story']['faultline'],
        manifest['configuration']['resource_ids']))
    original_templates = {entry[1]:entry for entry in archive.entries('templates')}
    with (archive.GAME/'templates.dat').open('rb') as source:
        _, stock_records, stock_folders, stock_paths = read_catalog(archive.read(source, original_templates[CATALOG_KEY]))
        plot_bounds = {name:bounds(archive.read(source, original_templates[archive.murmur(
            (design[2].lower()+'.binarytemplate').encode())])) for name,design in DESIGNS.items()}
    template_entries = {e['name']:e for e in manifest['archives']['templates']['entries']}
    catalog = template_entries[CATALOG_ASSET]
    assert catalog['hash'] == CATALOG_KEY and 'original_hash' not in catalog
    _, records, folders, paths = read_catalog(gzip.decompress((ROOT/'build/native/payload'/catalog['payload']).read_bytes()))
    assert stock_folders.keys() == folders.keys()
    assert all(path == paths[uid] and stock_records[uid] == records[uid] for uid, path in stock_paths.items())
    new_uids = set(paths) - set(stock_paths)
    assert all([uid for uid in new_members if uid not in new_uids] == members
               for folder, (_, members) in stock_folders.items() for _, new_members in [folders[folder]])
    campaign = meta['story']['faultline']
    required = campaign['buildings']+campaign['models']
    assert new_uids == {bytes.fromhex(row['guid']) for row in required}
    mesh_triangles = {}
    for row in required:
        uid = bytes.fromhex(row['guid'])
        path = paths[uid].relative_to('templates').as_posix()
        data=gzip.decompress((ROOT/'build/native/payload'/template_entries[path]['payload']).read_bytes())
        assert path == row['path'] and data.startswith(uid + records[uid][1])
        assert template_entries[path]['hash'] == archive.murmur(path.encode())
        if 'triangles' in row:
            low, high = audit_mesh(data,row['triangles'])
            name = row['name']
            stock_low, stock_high = plot_bounds[name]
            assert all(a<=b<=c<=d for a,b,c,d in zip(stock_low,low,high,stock_high,strict=True)), name
            assert all(high[i]-low[i] >= .72*(stock_high[i]-stock_low[i]) for i in (0,2)), name
            assert row['triangles'] <= 9000, name
            mesh_triangles[name] = row['triangles']
            prefab=next(building for building in campaign['buildings'] if building['name']==row['name'])
            assert templates[prefab['path']].count(string(path.removesuffix('.binarytemplate')))>=2
    result['faultline']['registered_template_guids'] = len(required)
    result['faultline']['model_triangles'] = mesh_triangles
    movie, = manifest['archives']['videos']['entries']
    assert movie['name']==campaign['opening_movie']['file']
    assert movie['hash']==archive.murmur(movie['name'].encode()) and not manifest['archives']['sequences']['entries']
    intro_record, = (entry for entry in archive.entries('common') if entry[1]==archive.murmur(CINEMATICS.encode()))
    with (archive.GAME/'common.dat').open('rb') as source:
        stock_cinematics=archive.read(source,intro_record)
    video=gzip.decompress((ROOT/'build/native/payload'/movie['payload']).read_bytes())
    audit_movie(stock_cinematics,payload[CINEMATICS],video,campaign)
    result['faultline']['native_intro_movie']=True
    world=next(e for e in manifest['archives']['scenes']['entries'] if e['name']==WORLD.lower()+'.binaryscene')
    donor, = (e for e in archive.entries('scenes') if e[1]==archive.murmur((WORLD_DONOR.lower()+'.binaryscene').encode()))
    assert world['original_hash']==donor[1]
    with (archive.GAME/'scenes.dat').open('rb') as source:
        stock_world=archive.read(source,donor)
    revised_world=gzip.decompress((ROOT/'build/native/payload'/world['payload']).read_bytes())
    assert revised_world.replace(WORLD.encode()+b'\0',WORLD_DONOR.encode()+b'\0',1)==stock_world, 'Frostland object stream changed'
    result['winter_road']['native_world_layout_preserved']=True
    technology_data=payload['configs/frostpunktechnologiesconfig.bin']
    token=b'\1\1Default_Endless\0';at=technology_data.index(token)+len(token)+16
    count=struct.unpack_from('<I',technology_data,at)[0]
    members={technology_data[p:p+16].hex() for p in range(at+4,at+4+16*count,16)}
    assert all(g['target'] in members for q in meta['frontiers']['missions'] for g in q['goals'] if g['kind']=='research')
    token=b'\1\1Default\0';at=technology_data.rindex(token)+len(token)+16
    count=struct.unpack_from('<I',technology_data,at)[0]
    members={technology_data[p:p+16].hex() for p in range(at+4,at+4+16*count,16)}
    assert all(g['target'] in members for q in meta['story']['acts'] for g in q['goals'] if g['kind']=='research')
    winter=meta['story']['winter_road']
    assert all(g['target'] in members for q in winter['missions']+winter['projects'] for g in q['goals'] if g['kind']=='research')
    assert all(g['target'] in members for q in meta['story']['faultline']['missions'] for g in q['goals'] if g['kind']=='research')
    blueprint_data=payload['configs/frostpunkblueprintsconfig.bin']
    assert all(bytes.fromhex(uid) in blueprint_data for ids in winter['recipes'].values() for uid in ids)
    result['frontiers']['research_targets_available']=True
    (ROOT/'build/endless-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
