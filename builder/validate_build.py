"""Validate the owned native build independently of its public installer.

Run after build_mod.py. This examines emitted binary records, not just catalog
metadata. Game inputs remain local and are never needed by the public CI tests.
"""
import gzip
import json
from pathlib import Path
import re
import struct
import uuid

from research_curation import effect_signature, modifiers, normalized, place_scalar_offset, REMOVED_TEAMS
from research_layout import geometry_errors
from city_mastery import building_ids
from station_recipes import PRODUCTION


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'builder/cache/extracted/common/configs'


def validate_recipes(manifest,payload):
    """Check actual blueprint requirements, resource prices, durations and queues."""
    data=payload['configs/frostpunkblueprintsconfig.bin']
    economy=(SOURCE/'frostpunkeconomyconfig.bin').read_bytes();resources={}
    for name in ('Coal','Wood','Steel','Wooden Materials','Steel Plates','Steam Tools','Steam Cores','Raw Food','Food Rations','Augmentation parts'):
        p=economy.index(b'\1\1'+name.encode()+b'\0')+len(name)+3
        resources[name]=economy[p:p+16]
    def text(value):return b'\1'+value.encode()+b'\0'
    def gid(value):return uuid.uuid5(uuid.NAMESPACE_URL,'frostpunk-new-industry-v1/'+value).bytes_le
    for recipe in manifest['recipes']:
        recipe_guid=gid('recipe/'+recipe['id'])
        prefix=b'\1'+text('NI '+recipe['id'])+recipe_guid
        start=data.index(prefix);position=start+len(prefix)
        count,=struct.unpack_from('<I',data,position);position+=4;positive=[];negative=[]
        technology=text('FrostpunkTechnologyRequirement')+bytes(17)
        composite=text('FrostpunkCompositeRequirement')+bytes(17)+struct.pack('<2I',2,1)
        for _ in range(count):
            negated=data[position:position+len(composite)]==composite
            if negated:position+=len(composite)
            assert data[position:position+len(technology)]==technology,(recipe['id'],'unexpected requirement type')
            position+=len(technology)
            (negative if negated else positive).append(data[position:position+16].hex());position+=16
        assert positive==[recipe['unlock']] and negative==recipe.get('excludes',[]),(recipe['id'],'requirements differ from metadata')
        for _ in range(2):
            assert data[position]==1;position=data.index(0,position+1)+1
        assert data[position:position+2]==bytes(2);position+=2
        assert data[position]==1;position=data.index(0,position+1)+1+16
        assert data[position:position+6] in (b'\1\1\1\0\0\0',b'\0\1\1\0\0\0');position+=6
        food=recipe['output']=='Food Rations'
        product=text('FrostpunkFoodRationProduct' if food else 'FrostpunkResourceProduct')
        assert data[position:position+len(product)]==product;position+=len(product)
        assert struct.unpack_from('<I',data,position)[0]==1;position+=4
        if not food:
            assert data[position:position+16]==resources[recipe['output']];position+=16
        assert struct.unpack_from('<I',data,position)[0]==recipe['amount'];position+=4
        if food:
            assert struct.unpack_from('<I',data,position)[0]==3;position+=4
        assert data[position:position+4]==bytes(4);position+=4
        n,=struct.unpack_from('<I',data,position);position+=4
        actual={data[p:p+16]:struct.unpack_from('<I',data,p+16)[0] for p in range(position,position+n*20,20)}
        assert actual=={resources[k]:v for k,v in recipe['inputs'].items()},(recipe['id'],'input costs differ')
        position+=n*20
        assert abs(struct.unpack_from('<f',data,position)[0]-recipe['hours'])<1e-6;position+=4
        assert data[position:position+11] in (struct.pack('<I',2)+bytes(7),struct.pack('<2I',2,1)+bytes(3),struct.pack('<2I',2,1)+b'\0\1\0')
        for target in recipe['targets']:
            path='gameentities/buildings/'+target+'.binarytemplate'
            template=payload[path]
            p=template.index(PRODUCTION)+len(PRODUCTION)+16;n,=struct.unpack_from('<I',template,p)
            ids=[template[i:i+16] for i in range(p+4,p+4+n*16,16)]
            assert ids.count(recipe_guid)==1,(recipe['id'],'missing or duplicated in production panel',path)
            original=(ROOT/'builder/cache/extracted/templates'/path).read_bytes()
            q=original.index(PRODUCTION)+len(PRODUCTION)+16;old,=struct.unpack_from('<I',original,q)
            assert {original[i:i+16] for i in range(q+4,q+4+old*16,16)}<=set(ids),'Lost a native production recipe'
    print(f"Verified {len(manifest['recipes'])} serialized recipes, replacement requirements and all production-component attachments.")


def validate_choice_effects(manifest,records):
    by_id={t['id']:t for t in manifest['technologies']}
    buildings=building_ids((SOURCE/'frostpunkbuildingsconfig.bin').read_bytes())
    original=modifiers((SOURCE/'frostpunkmodifiersconfig.bin').read_bytes())
    coal=bytes.fromhex('0bcf0b94b94337859c44bcdf67f9bee1')
    for key in ('CondensateHeaters','AutumnCondensateHeaters'):
        expected=original['ccae6fbb0e236596b44ca8189e01248f'][2]
        p=expected.index(coal)+16
        assert expected[p:p+8]==struct.pack('<2f',-1,1)
        expected=expected[:p]+struct.pack('<2f',0,0.5)+expected[p+8:]
        for _,g in by_id[key]['extra_effects']:
            assert records[g][2]==expected,'Heater predicates or unrelated fields changed'
    for key in ('LimbSparingSurgery','AutumnLimbSparingSurgery'):
        assert {p for p,_ in by_id[key]['effects']}=={buildings['Medical Post'].hex()}
        for _,g in by_id[key]['effects']:
            assert struct.unpack_from('<f',normalized(records[g][2]),173)[0]==0
    for key,human,robot,heat in [('WinterArtisanGuilds',2.5,1,2),('AutonomousMaintenance',1,2.5,0)]:
        for _,g in by_id[key]['effects']:
            b=normalized(records[g][2]);p=place_scalar_offset(b,72)
            assert struct.unpack_from('<fIIff',b,p)==(1,0,2,human,robot)
            assert struct.unpack_from('<i',b,place_scalar_offset(b,96))[0]==heat
    print('Verified heater condition preservation, surgery scope and separate human/automaton work roles.')


def parse_entry(data):
    position = len(b'\1FrostpunkTechnologyEntry\0')
    assert data[position] == 1
    end = data.index(0,position+1)
    name = data[position+1:end].decode();guid=data[end+1:end+17].hex()
    position=end+18
    count,=struct.unpack_from('<I',data,position);position+=4
    requires=[]
    for _ in range(count):
        marker=b'\1FrostpunkTechnologyRequirement\0'+bytes(17)
        assert data[position:position+len(marker)]==marker
        position+=len(marker);requires.append(data[position:position+16].hex());position+=16
    assert data[position:position+4]==bytes(4);position+=4
    strings=[]
    for _ in range(3):
        assert data[position]==1
        end=data.index(0,position+1);strings.append(data[position+1:end].decode());position=end+1
    icon=struct.unpack_from('<2i',data,position)
    column,y=struct.unpack_from('<2i',data,position+8)
    category=data[position+16:position+32].hex()
    count,=struct.unpack_from('<I',data,position+32);position+=36
    costs={data[p:p+16].hex():struct.unpack_from('<I',data,p+16)[0] for p in range(position,position+count*20,20)}
    position+=count*20
    hours,version=struct.unpack_from('<fI',data,position);assert version==2;position+=8
    vectors={}
    for key,width in [('global_effects',16),('effects',32),('extra_effects',32)]:
        count,=struct.unpack_from('<I',data,position);position+=4
        vectors[key]=[data[p:p+width].hex() if width==16 else (data[p:p+16].hex(),data[p+16:p+32].hex())
                      for p in range(position,position+count*width,width)]
        position+=count*width
    assert len(data)-position==25 and data[position+4:position+16]==b'\1TECH_ENTRY\0'
    return dict(name=name,guid=guid,requires=requires,icon=list(icon),column=column,tier=y//2,
                category=category,costs=costs,hours=hours,strings=strings,**vectors)


def main():
    native=ROOT/'build/native'
    manifest=json.loads((native/'manifest.json').read_text())
    payload={e['name']:gzip.decompress((native/'payload'/e['payload']).read_bytes())
             for group in manifest['archives'].values() for e in group['entries']}
    tc=payload['configs/frostpunktechnologiesconfig.bin']
    original=(SOURCE/'frostpunktechnologiesconfig.bin').read_bytes()
    info=json.loads((ROOT/'builder/cache/tech.json').read_text())
    mods=modifiers(payload['configs/frostpunkmodifiersconfig.bin'])
    for g,record in modifiers((SOURCE/'frostpunkmodifiersconfig.bin').read_bytes()).items():
        assert mods[g]==record, ('Changed native modifier',g)
    for g,(kind,name,raw) in mods.items():
        body=normalized(raw)
        if name.startswith(b'NI') and kind=='Place' and len(body) in (238,257):
            # Read the vector counts at the actual native position. Comparing
            # byte lengths or regex-delimited records alone misses corrupted
            # nested arrays in modifiers with an optional atlas string.
            place_scalar_offset(body,72)
    starts=[m.start() for m in re.finditer(b'\1FrostpunkTechnologyEntry\0',tc)]
    assert len(starts)==len(info)+len(manifest['technologies'])
    assert struct.unpack_from('<I',tc,starts[0]-4)[0]==len(starts)
    native_end=info[-1]['tail']+40+20*info[-1]['costcount']+41
    native_bytes=original[info[0]['start']:native_end]
    assert tc[starts[0]:starts[len(info)]]==native_bytes, 'Native research entries changed'
    assert struct.unpack_from('<I',tc)[0]==struct.unpack_from('<I',original)[0]+len(manifest['research_tabs'])
    by_guid={t['guid']:t for t in manifest['technologies']}
    for i,tech in enumerate(manifest['technologies'],len(info)):
        if i+1<len(starts):end=starts[i+1]
        else:
            # Serialized trailing vectors have fixed 25-byte metadata after the
            # three counted effect vectors. Native scaling knots follow directly.
            marker=b'\1TECH_ENTRY\0';p=tc.index(marker,starts[i]);end=p+len(marker)+9
        entry=parse_entry(tc[starts[i]:end])
        for key in ('guid','requires','icon','column','tier','category','global_effects','effects','extra_effects'):
            assert json.loads(json.dumps(entry[key]))==json.loads(json.dumps(tech[key])), (tech['id'],key)
        assert entry['hours']==tech['hours']
        for key in ('global_effects','effects','extra_effects'):
            for value in entry[key]:
                g=value if key=='global_effects' else value[1]
                assert g in mods,(tech['id'],'missing modifier',g)
        assert effect_signature(tech,mods)==tech['effect_fingerprint']
        if tech['id'] in REMOVED_TEAMS:
            for _,g in tech['effects']:
                assert struct.unpack_from('<i',normalized(mods[g][2]),177)[0]==0
        for g in tech['requires']:
            if g in by_guid:
                assert by_guid[g]['tier']<=tech['tier'], ('Later mod prerequisite',tech['id'])
            else:
                parent=next(t for t in info if t['guid']==g)
                if 'TierUnlock' not in parent['name']:
                    assert parent['layout'][3]//2<=tech['tier'],('Later native prerequisite',tech['id'],parent['name'])
    for scenario,additions in manifest['scenario_additions'].items():
        def members(data):
            marker=b'\1\1'+scenario.encode()+b'\0';p=data.index(marker)+len(marker)+16
            n,=struct.unpack_from('<I',data,p)
            return [data[i:i+16].hex() for i in range(p+4,p+4+16*n,16)]
        assert members(tc)==members(original)+additions, (scenario,'membership mismatch')
        seen=set(members(original))
        for g in additions:
            tech=by_guid[g]
            assert set(tech['requires'])<=seen,(scenario,tech['id'],'unreachable')
            seen.add(g)
        signatures=[by_guid[g]['effect_fingerprint'] for g in additions]
        assert len(set(signatures))==len(signatures)
        assert not REMOVED_TEAMS & {by_guid[g]['id'] for g in additions}
        for _,category in manifest['research_tabs']:
            assert not geometry_errors([by_guid[g] for g in additions if by_guid[g]['category']==category])
    # The ability-construction hotfix must stay intact. No ability or building
    # configuration entry may accidentally be added to this patch distribution.
    assert not any('abilitiesconfig' in name or 'buildingsconfig' in name for name in payload)
    validate_recipes(manifest,payload)
    validate_choice_effects(manifest,mods)
    print(f"Verified {len(starts)} technology records, {len(mods)} modifiers, {len(manifest['scenario_additions'])} scenario graphs, native-record preservation and team neutralization.")


if __name__=='__main__':
    main()
