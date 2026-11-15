"""Validate new laws, native preservation, visible branches and icon subjects."""
import gzip
import json
from pathlib import Path
import re
import struct

from civic_progression import law_records
from icon_curation import RESOURCE_ICONS
from research_curation import modifiers, normalized

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
    assert len(native) == 112 and len(revised) == 116
    assert all(revised[name] == record for name,record in native.items()), 'Native laws changed'
    assert original[native_end:] == data[revised_end:], 'Native society tail changed'
    category = data.index(b'\1\1Civic Charters\0')
    assert struct.unpack_from('<I',data,category-4)[0] == 5
    assert data.count(b'\1\1Civic Charters\0') == 1
    records = modifiers(payload['configs/frostpunkmodifiersconfig.bin'])
    technologies = {t['guid']:t for t in manifest['technologies']}
    native_techs = {t['name']:t for t in json.loads((ROOT/'builder/cache/tech.json').read_text())}
    source_effects = (SOURCE/'frostpunkeffectsconfig.bin').read_bytes()
    prefab = b'\1FrostpunkPredefinedEffect\0'
    apply = b'\1FrostpunkApplyModifierEffect\0'
    for law in manifest['laws']:
        raw = revised['NI '+law['id']]
        marker = b'\1FrostpunkTechnologyRequirement\0' + bytes(17) + bytes.fromhex(law['research'])
        assert marker in raw
        assert apply + bytes.fromhex(law['modifier']) in raw
        assert records[law['modifier']][0] == 'Global'
        global_body = normalized(records[law['modifier']][2])
        n = struct.unpack_from('<I',global_body,77)[0]
        assert len(global_body) == 186+n*32
        for p in range(81,81+n*32,32):
            assert records[global_body[p+16:p+32].hex()][0] == 'Place'
        for g in law['native_effects']:
            assert prefab + bytes.fromhex(g) in raw and bytes.fromhex(g) in source_effects
        assert b'Oneliners/' not in raw and bytes.fromhex('1fb45ef57ba8a9994640f8a9e0a89eca') not in raw
        loc = raw.index(b'\1@Mods/NewIndustry/Laws/')
        for _ in range(2):loc=raw.index(0,loc+1)+1
        assert raw[loc] == 0
        assert struct.unpack_from('<4i',raw,loc+1) == (*law['icon'],*law['position'])
        assert struct.unpack_from('<f',raw,loc+42)[0] == 18
        assert struct.unpack_from('<I',raw,loc+46)[0] == 2
        assert struct.unpack_from('<I',raw,loc+50)[0] == 0
        assert struct.unpack_from('<I',raw,loc+67)[0] == len(law['native_effects'])+1
        effect_start=loc+71
        switch=b'\1FrostpunkSwitchEffect\0'
        first=raw.index(switch,effect_start) if 'Hope rise' in law['effects'][0] else raw.index(prefab,effect_start)
        assert first==effect_start, 'On-sign effects are not at the native effect-vector offset'
        assert all(law['research'] in ids for ids in manifest['scenario_additions'].values())
    active=set().union(*map(set,manifest['scenario_additions'].values()))
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
    print(f"Verified 4 signable laws, 112 byte-identical native laws, native scenario-switched Hope/Motivation effects, all {len(active)} active research nodes and 43 output icons.")


if __name__=='__main__':main()
