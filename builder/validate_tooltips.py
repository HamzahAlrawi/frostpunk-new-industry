"""Independently check serialized source text, native predicates and heat totals."""
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import struct

from research_curation import modifiers,normalized,place_scalar_offset


ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'builder/cache/extracted'
PREDICATE=b'\1FrostpunkTechnologyIsResearchedExpression\0'


def language_table(data):
    assert struct.unpack_from('<I',data)[0]==len(data)-4
    count=struct.unpack_from('<I',data,4)[0];p=8;result={}
    for _ in range(count):
        n=struct.unpack_from('<H',data,p)[0];p+=2;key=data[p:p+n];p+=n
        n=struct.unpack_from('<H',data,p)[0];p+=2;value=data[p:p+n*2];p+=n*2
        assert key not in result
        result[key]=value
    assert p==len(data)
    return result


def decode_presentation(body):
    count=struct.unpack_from('<I',body)[0];p=4;predicate=None
    assert count in (0,1)
    if count:
        assert body[p:p+len(PREDICATE)]==PREDICATE;p+=len(PREDICATE)
        predicate=(body[p:p+16].hex(),body[p+16]);p+=17
        assert predicate[1]==1,'Cumulative source must require next stage NOT researched'
    # The remaining common header is 21 bytes before its two optional texts.
    p+=21;fields=[]
    for _ in range(2):
        assert body[p]==1,'Empty modifier tooltip field'
        end=body.index(0,p+1);fields.append(body[p+1:end].decode());p=end+1
    return predicate,fields


def main():
    manifest=json.loads((ROOT/'build/native/manifest.json').read_text())
    payload={e['name']:gzip.decompress((ROOT/'build/native/payload'/e['payload']).read_bytes())
             for group in manifest['archives'].values() for e in group['entries']}
    native=modifiers((SOURCE/'common/configs/frostpunkmodifiersconfig.bin').read_bytes())
    current=modifiers(payload['configs/frostpunkmodifiersconfig.bin'])
    assert all(current[g]==row for g,row in native.items())
    meta=manifest['modifier_tooltips'];by={row['guid']:row for row in meta['records']}
    assert set(by)==current.keys()-native.keys()
    changed={info['guid']:info for family in meta['cumulative_families'] for stage in family['stages'] for info in stage['modifiers']}
    expected_conditions={}
    # Pin both native inversion states to actual shipped game-event records.
    events=(SOURCE/'common/configs/frostpunkgameeventsconfig.bin').read_bytes()
    sample=bytes.fromhex('95327a7d0e3600b3a84234cfe9f8da49')
    assert PREDICATE+sample+b'\0' in events and PREDICATE+sample+b'\1' in events
    for g,row in by.items():
        kind,_,body=current[g];predicate,fields=decode_presentation(body)
        assert fields==['@'+row['name_key'],'@'+row['description_key']]
        assert row['title'].strip() and row['description'].strip() and row['source_ids']
        scalars=bytearray(normalized(body))
        if g in changed:
            info=changed[g];offset=place_scalar_offset(scalars,96)
            assert struct.unpack_from('<i',scalars,offset)[0]==info['total']
            expected_conditions[g]=(info['superseded_by'],1) if info['superseded_by'] else None
            struct.pack_into('<i',scalars,offset,info['increment'])
        assert predicate==expected_conditions.get(g),(g,'unexpected source condition')
        assert hashlib.sha256(scalars).hexdigest()==row['effects_before_sha256'],(g,'non-presentation effects changed')
    languages=0
    for name,data in payload.items():
        if not name.endswith('.lang'):continue
        table=language_table(data);languages+=1
        for row in by.values():
            assert table[row['name_key'].encode()]==row['title'].encode('utf-16-le') and table[row['description_key'].encode()]==row['description'].encode('utf-16-le'),(name,row['guid'])
    assert languages==13
    techs={t['guid']:t for t in manifest['technologies']}
    cases=0
    for family in meta['cumulative_families']:
        stages=family['stages'];all_targets={target for stage in stages for info in stage['modifiers'] for target in info['targets']}
        for scenario,members in manifest['scenario_additions'].items():
            members=set(members)
            available=[stage for stage in stages if stage['technology'] in members]
            if not available:continue
            assert available==stages,(family['id'],scenario,'partial family membership')
            for i,stage in enumerate(stages):
                if i:assert stages[i-1]['technology'] in techs[stage['technology']]['requires']
                bindings=set(map(tuple,techs[stage['technology']]['effects']+techs[stage['technology']]['extra_effects']))
                for info in stage['modifiers']:
                    assert all((target,info['guid']) in bindings for target in info['targets'])
            for level in range(len(stages)+1):
                researched={stage['technology'] for stage in stages[:level]}
                old=defaultdict(int);new=defaultdict(int);rows=defaultdict(int)
                for stage in stages[:level]:
                    for info in stage['modifiers']:
                        predicate,_=decode_presentation(current[info['guid']][2])
                        enabled=predicate is None or predicate[0] not in researched
                        actual=struct.unpack_from('<i',normalized(current[info['guid']][2]),place_scalar_offset(normalized(current[info['guid']][2]),96))[0]
                        for target in info['targets']:
                            old[target]+=info['increment']
                            if enabled:new[target]+=actual;rows[target]+=1
                assert all(old[target]==new[target] for target in all_targets),(family['id'],scenario,level,'heat balance changed')
                assert all(rows[target]<=1 for target in all_targets),(family['id'],scenario,level,'duplicate heat rows')
                cases+=1
    print(f'Verified {len(by)} complete modifier tooltips in {languages} languages, six cumulative families across {cases} scenario/research states, preserved effect fields and every native modifier.')


if __name__=='__main__':main()
