"""Validate the owned native build independently of its public installer.

Run after build_mod.py. This examines emitted binary records, not just catalog
metadata. Game inputs remain local and are never needed by the public CI tests.
"""
import gzip
import json
from pathlib import Path
import re
import struct

from research_curation import effect_signature, modifiers, normalized, place_scalar_offset, REMOVED_TEAMS
from research_layout import geometry_errors


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'builder/cache/extracted/common/configs'


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
    print(f"Verified {len(starts)} technology records, {len(mods)} modifiers, {len(manifest['scenario_additions'])} scenario graphs, native-record preservation and team neutralization.")


if __name__=='__main__':
    main()
