"""Validate new laws, native preservation, visible branches and icon subjects."""
import gzip
import json
from pathlib import Path
import re
import struct
from collections import defaultdict

from civic_progression import law_records, book_records, law_layout, law_exclusion_group, law_layout_errors, LAW_BOOK, NATIVE_BOOK_NAMES
from icon_curation import RESOURCE_ICONS
from research_curation import modifiers, normalized
from city_mastery import building_ids

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'builder/cache/extracted/common/configs'


def main():
    manifest = json.loads((ROOT/'build/native/manifest.json').read_text())
    payload = {e['name']:gzip.decompress((ROOT/'build/native/payload'/e['payload']).read_bytes())
               for group in manifest['archives'].values() for e in group['entries']}
    original = (SOURCE/'frostpunksocietyconfig.bin').read_bytes()
    data = payload['configs/frostpunksocietyconfig.bin']
    _, native_end, native = law_records(original)
    _, revised_end, revised = law_records(data)
    assert len(native) == 112 and len(revised) == 144
    assert all(revised[name] == record for name,record in native.items()), 'Native laws changed'
    assert list(revised)[:112]==list(native), 'Native law order changed'
    assert original[native_end:] == data[revised_end:], 'Native society tail changed'
    old_start,old_books=book_records(original)
    new_start,new_books=book_records(data)
    assert tuple(new_books)==NATIVE_BOOK_NAMES+(LAW_BOOK,), 'Native book indices changed'
    assert old_start==new_start and all(new_books[name]==raw for name,raw in old_books.items()), 'Native book unlocks or UI resources changed'
    restored=(data[:new_start]+struct.pack('<I',4)+b''.join(new_books[name] for name in NATIVE_BOOK_NAMES)
              +struct.pack('<I',112)+b''.join(revised[name] for name in native)+data[revised_end:])
    assert restored==original, 'Removing additions must restore the entire original society config byte for byte'
    # Native mutually exclusive laws are two halves of ONE visual circle, not
    # independent full nodes. Pin that rule against all shipped choice groups.
    groups=defaultdict(list)
    for name,raw in native.items():
        group=law_exclusion_group(raw)
        if group:
            _,position,book=law_layout(raw);groups[book,group].append(position)
    assert len(groups)==13
    assert all(len(positions)==2 and positions[0]==positions[1] for positions in groups.values())
    added_groups=defaultdict(list)
    for law in manifest['laws']:
        if law.get('exclusion_group'):
            raw=revised['NI '+law['id']]
            assert law_exclusion_group(raw)==law['exclusion_group']
            _,position,book=law_layout(raw);added_groups[book,law['exclusion_group']].append(position)
    assert len(added_groups)==8
    assert all(len(positions)==2 and positions[0]==positions[1] for positions in added_groups.values()),'Split choice halves have different positions'
    assert not law_layout_errors(manifest['laws'],native)
    hidden=new_books[LAW_BOOK]
    gate=b'\1FrostpunkTechnologyRequirement\0'+bytes(17)+bytes.fromhex(manifest['laws'][0]['research'])
    neg=b'\1FrostpunkCompositeRequirement\0'+bytes(17)+struct.pack('<II',2,1)+gate
    header_end=hidden.index(0,2)+17
    assert hidden[header_end:header_end+4]==struct.pack('<I',2)
    assert hidden[header_end+4:header_end+4+len(gate)+len(neg)]==gate+neg, 'Legacy book must require P and NOT(P)'
    records = modifiers(payload['configs/frostpunkmodifiersconfig.bin'])
    technologies = {t['guid']:t for t in manifest['technologies']}
    native_techs = {t['name']:t for t in json.loads((ROOT/'builder/cache/tech.json').read_text())}
    source_effects = (SOURCE/'frostpunkeffectsconfig.bin').read_bytes()
    places=building_ids((SOURCE/'frostpunkbuildingsconfig.bin').read_bytes())
    places['Army Warehouse']=bytes.fromhex(next(t for t in manifest['technologies'] if t['id']=='EdgeWarehouseSorting')['effects'][0][0])
    economy=(SOURCE/'frostpunkeconomyconfig.bin').read_bytes()
    resource_ids={}
    for name in ('Augmentation parts','Coal','Wood','Steel','Raw Food','Food Rations'):
        p=economy.index(b'\1\1'+name.encode()+b'\0')+len(name)+3
        resource_ids[name]=economy[p:p+16]
    law_by_id={law['id']:law for law in manifest['laws']}
    prefab = b'\1FrostpunkPredefinedEffect\0'
    apply = b'\1FrostpunkApplyModifierEffect\0'
    for law in manifest['laws']:
        raw = revised['NI '+law['id']]
        # Decode the actual prerequisite vector. Metadata alone cannot prove a
        # supposedly default law is free of an accidentally inherited tech gate.
        p=raw.index(0,len(b'\1FrostpunkSociotechEntry\0')+1)+18
        count=struct.unpack_from('<I',raw,p)[0];p+=4
        tech=b'\1FrostpunkTechnologyRequirement\0'+bytes(17)
        signed=b'\1FrostpunkSociotechRequirement\0'+bytes(17)
        exclusion=b'\1FrostpunkSociotechExclusionRequirement\0'+bytes(17)
        negate=b'\1FrostpunkCompositeRequirement\0'+bytes(17)+struct.pack('<II',2,1)
        actual_tech=[];actual_signed=[];actual_excluded=[];actual_groups=[]
        for _ in range(count):
            negative=raw.startswith(negate,p)
            if negative:p+=len(negate)
            if raw.startswith(tech,p):
                assert not negative
                p+=len(tech);actual_tech.append(raw[p:p+16].hex());p+=16
            elif raw.startswith(exclusion,p):
                assert not negative
                p+=len(exclusion)
                assert raw[p]==1
                end=raw.index(0,p+1);actual_groups.append(raw[p+1:end].decode());p=end+1
            else:
                assert raw.startswith(signed,p),'Unexpected law prerequisite type'
                p+=len(signed)
                (actual_excluded if negative else actual_signed).append(raw[p:p+16].hex());p+=16
        assert raw[p:p+4]==bytes(4)
        assert actual_tech==([law['research']] if law.get('research') else [])
        assert actual_signed==law.get('required_law_guids',[])
        assert actual_excluded==([law['legacy_equivalent']] if law.get('legacy_equivalent') else [])
        assert actual_groups==([law['exclusion_group']] if law.get('exclusion_group') else [])
        if law.get('default_available'):
            assert not actual_tech
            if law['branch_root']:assert count==0
            else:
                assert len(actual_signed)==len(actual_groups)==1 and count==2
                assert law_by_id[law['requires_laws'][0]]['book_guid']==law['book_guid']
                members=[other for other in manifest['laws'] if other.get('exclusion_group')==law['exclusion_group']]
                assert {other['id'] for other in members}=={law['id'],*law['excludes_laws']}
        assert apply + bytes.fromhex(law['modifier']) in raw
        assert records[law['modifier']][0] == 'Global'
        global_body = normalized(records[law['modifier']][2])
        n = struct.unpack_from('<I',global_body,77)[0]
        assert len(global_body) == 186+n*32
        for p in range(81,81+n*32,32):
            assert records[global_body[p+16:p+32].hex()][0] == 'Place'
        if law.get('benefits'):
            actual_pairs={(global_body[p:p+16].hex(),global_body[p+16:p+32].hex()) for p in range(81,81+n*32,32)}
            expected_targets=set()
            for info in law['benefits']['sites']:
                for name in info['targets']:
                    target=places[name].hex();expected_targets.add(target)
                    matching=[modifier for site,modifier in actual_pairs if site==target]
                    assert len(matching)==1,(law['id'],name)
                    body=normalized(records[matching[0]][2])
                    for field,offset,code in [('human',84,'f'),('automaton',88,'f'),('insulation',96,'i'),('amputation',173,'f'),('safety',185,'i')]:
                        if field in info:assert struct.unpack_from('<'+code,body,offset)[0]==info[field],(law['id'],name,field)
                    if 'storage' in info:
                        start=body.index(struct.pack('<I',8)+resource_ids['Augmentation parts'])+4
                        for q in range(start,start+8*24,24):
                            expected=next((factor for resource,factor in info['storage'].items() if resource_ids[resource]==body[q:q+16]),1)
                            assert struct.unpack_from('<If',body,q+16)==(0,expected),(law['id'],name,'storage')
            assert {site for site,_ in actual_pairs}==expected_targets
            for field,value in law['benefits']['global_changes'].items():
                offset=69 if field=='heat_radius' else 166+n*32
                assert struct.unpack_from('<f',global_body,offset)[0]==value,(law['id'],field)
        for g in law['native_effects']:
            assert prefab + bytes.fromhex(g) in raw and bytes.fromhex(g) in source_effects
        assert b'Oneliners/' not in raw and bytes.fromhex('1fb45ef57ba8a9994640f8a9e0a89eca') not in raw
        loc = raw.index(b'\1@Mods/NewIndustry/Laws/')
        for _ in range(2):loc=raw.index(0,loc+1)+1
        assert raw[loc] == 0
        assert struct.unpack_from('<4i',raw,loc+1) == (*law['icon'],*law['position'])
        assert raw[loc+17:loc+33].hex()==law['book_guid']
        assert struct.unpack_from('<f',raw,loc+42)[0] == law['cooldown']
        assert struct.unpack_from('<I',raw,loc+46)[0] == 2
        assert struct.unpack_from('<I',raw,loc+50)[0] == 0
        group_at=loc+66
        if law.get('exclusion_group'):
            expected=b'\1'+law['exclusion_group'].encode()+b'\0'
            assert raw[group_at:group_at+len(expected)]==expected
            effect_vector=group_at+len(expected)
        else:
            assert raw[group_at]==0
            effect_vector=group_at+1
        assert struct.unpack_from('<I',raw,effect_vector)[0] == len(law['native_effects'])+1
        effect_start=effect_vector+4
        switch=b'\1FrostpunkSwitchEffect\0'
        first=raw.index(switch,effect_start) if 'Hope rise' in law['effects'][0] else raw.index(prefab,effect_start)
        assert first==effect_start, 'On-sign effects are not at the native effect-vector offset'
        if law.get('research'):assert all(law['research'] in ids for ids in manifest['scenario_additions'].values())
    active=set().union(*map(set,manifest['scenario_additions'].values()))
    by_id={t['id']:t for t in technologies.values()}
    tc=payload['configs/frostpunktechnologiesconfig.bin']
    marker=b'\1\1TechHaven\0';p=tc.index(marker)+len(marker)+16
    n=struct.unpack_from('<I',tc,p)[0]
    arks={tc[i:i+16].hex() for i in range(p+4,p+4+16*n,16)}
    for key in ('Cores1','Cores2','Cores3','MassCoreFabrication'):
        t=by_id[key]
        assert t['guid'] in arks and t['tab']=='Industry' and t['column']==2, 'Arks core manufacturing must be visible in Industry column one'
    native_guid={t['guid']:t for t in native_techs.values()}
    for g in active:
        t=technologies[g]
        assert t['icon']==list(native_techs[t['icon_source']]['layout'][:2])
        parents=[technologies[p] for p in t['requires'] if p in technologies]
        assert len(parents)<=1
        for p in t['requires']:
            if p in native_guid:assert 'TierUnlock' in native_guid[p]['name'], ('Hidden native requirement',t['id'])
        for p in parents:
            assert p['category']==t['category'] and p['column']==t['column'] and p['tier']<t['tier']
    # Independently read the actual output icon in every emitted recipe.
    blueprints=payload['configs/frostpunkblueprintsconfig.bin']
    economy=(SOURCE/'frostpunkeconomyconfig.bin').read_bytes()
    for resource,expected in RESOURCE_ICONS.items():
        start=economy.index(b'\1\1'+resource.encode()+b'\0')
        native_atlas=re.search(rb'\x01UI\\[^\0]+\.dds\0',economy[start:])
        assert struct.unpack_from('<2i',economy,start+native_atlas.end())==expected
    for recipe in manifest['recipes']:
        start=blueprints.index(b'\1\1NI '+recipe['id'].encode()+b'\0')
        atlas=re.search(rb'\x01UI\\[^\0]+\.dds\0',blueprints[start:])
        expected=(0,1) if recipe['output']=='Food Rations' else RESOURCE_ICONS[recipe['output']]
        assert struct.unpack_from('<2i',blueprints,start+atlas.end())==expected,(recipe['id'],'wrong output icon')
    print(f"Verified eight joined choice circles against 13 native pairs, compact connections, 16 policies per mode, parent/exclusion gates and passive values, native book preservation, Arks cores, {len(active)} research nodes and 43 output icons.")


if __name__=='__main__':main()
