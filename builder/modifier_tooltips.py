"""Label modifier sources and collapse linear insulation source chains.

Research, law and modifier IDs are retained. Older stages use the native
NOT-researched-next-stage condition; a successor carries cumulative insulation.
Non-insulation values and unrelated global bonuses stay intact.
"""
from collections import defaultdict
import hashlib
import struct

from modifier_conditions import split_technology_condition, with_technology_condition
from research_curation import modifiers,normalized,pack_modifiers,place_scalar_offset


CHAINS = (
    ('thermal-envelope','Citywide Thermal Envelope',
     ['CitywideLagging']+['CitywideLagging'+str(i) for i in range(2,7)]),
    ('healthcare-insulation','Healthcare Insulation',['MedicalHeat3','MedicalHeat4']),
    ('hothouse-insulation','Hothouse Insulation',['HothouseHeat3','HothouseHeat4']),
    ('kitchen-insulation','Cookhouse Insulation',['CookhouseSteamShell','CookhouseHeat2']),
    ('housing-insulation','Housing Insulation',['HouseVestibules','HouseInsulatedFloors']),
    ('warehouse-insulation','Army Warehouse Insulation',['EdgeWarehouseBaffles','EdgeWarehouseWinches']),
)


def improve_tooltips(data,original,specs,laws,membership,localize):
    records=modifiers(data);native=modifiers(original)
    custom={g for g in records if g not in native}
    before={g:hashlib.sha256(normalized(records[g][2])).hexdigest() for g in custom}
    by_id={t['id']:t for t in specs}
    active=set().union(*map(set,membership.values()))
    owners=defaultdict(dict)

    def own(g,source,priority,seen=None):
        seen=set() if seen is None else seen
        if g in seen:return
        seen.add(g)
        if g in custom:owners[g][source['id']]=(priority,source)
        kind,_,raw=records[g]
        if kind=='Global':
            body=normalized(raw)
            n=struct.unpack_from('<I',body,77)[0]
            assert n<=112 and len(body)>=81+n*32
            for p in range(81,81+n*32,32):
                child=body[p+16:p+32].hex()
                assert child in records and records[child][0]=='Place'
                own(child,source,priority,seen)

    for tech in specs:
        for g in tech['global_effects']+[g for k in ('effects','extra_effects') for _,g in tech[k]]:
            own(g,tech,0 if tech['guid'] in active else 2)
    for law in laws:own(law['modifier'],law,1)
    # Retired clones can be unreferenced by the final effect vectors. Their
    # registration name still identifies the original authored research.
    for g in custom-owners.keys():
        name=records[g][1].decode()
        root=name.removeprefix('NI ').split('/')[0]
        root={'ResearchSprint':'FieldResearchSprints'}.get(root,root)
        matches=[t for t in specs if t['id']==root or t['id'] in name.split('/') or name.startswith('NI '+t['id']+'/')]
        if matches:
            source=max(matches,key=lambda t:len(t['id']))
            owners[g][source['id']]=(3,source)
    assert custom<=owners.keys(),('Unlabelled modifier owners',[records[g][1] for g in custom-owners.keys()])

    families=[];grouped={}
    for family,title,keys in CHAINS:
        stages=[];running=defaultdict(int)
        for index,key in enumerate(keys):
            tech=by_id[key];bindings=defaultdict(set)
            for field in ('effects','extra_effects'):
                for target,g in tech[field]:
                    kind,_,raw=records[g];body=normalized(raw)
                    if kind=='Place' and len(body) in (238,257) and struct.unpack_from('<i',body,place_scalar_offset(body,96))[0]:
                        bindings[g].add(target)
            assert bindings,(family,key)
            stage=dict(technology=tech['guid'],id=key,modifiers=[])
            next_tech=by_id[keys[index+1]] if index+1<len(keys) else None
            if index:
                assert by_id[keys[index-1]]['guid'] in tech['requires'],(family,key,'not a linear chain')
            for g,targets in bindings.items():
                assert g in custom and g not in grouped
                body=bytearray(normalized(records[g][2]));offset=place_scalar_offset(body,96)
                increment=struct.unpack_from('<i',body,offset)[0]
                previous={running[target] for target in targets}
                assert len(previous)==1,(family,key,'mixed cumulative totals in one modifier')
                total=increment+previous.pop()
                if next_tech:
                    # Disabling an earlier record must never remove another
                    # effect. Only a pure insulation record can be superseded.
                    neutral=bytearray(normalized(native['34156f71336543af0e4fed3a6c7d9e95'][2]))
                    test=bytearray(body);struct.pack_into('<i',test,offset,1)
                    assert test[69:]==neutral[69:],(family,key,'earlier record has other effects')
                    following={target for field in ('effects','extra_effects') for target,_ in next_tech[field]}
                    assert targets<=following,(family,key,'a later stage loses targets')
                struct.pack_into('<i',body,offset,total)
                if next_tech:body=with_technology_condition(bytes(body),next_tech['guid'])
                records[g][2]=bytes(body)
                info=dict(guid=g,targets=sorted(targets),increment=increment,total=total,
                          superseded_by=next_tech['guid'] if next_tech else None)
                stage['modifiers'].append(info)
                grouped[g]=dict(family=family,title=title,total=total,source=tech)
            for info in stage['modifiers']:
                for target in info['targets']:running[target]+=info['increment']
            stages.append(stage)
        families.append(dict(id=family,title=title,stages=stages))

    presentations=[]
    for g in sorted(custom):
        _,source=min(owners[g].values(),key=lambda item:(item[0],item[1]['id']))
        title=source['title'];description=source['description'].split('\n\nRequires:')[0]
        name_key='Modifier/'+g+'/Name'
        if g in grouped:
            group=grouped[g];title=group['title'];name_key='Modifier/Family/'+group['family']+'/Name'
            description=f"Researched stages of {title} provide +{group['total']} insulation at this building."
            # A final-stage record can also carry its existing efficiency perk.
            body=normalized(records[g][2]);offset=place_scalar_offset(body,84)
            if struct.unpack_from('<ff',body,offset)!=(1.0,1.0):
                description+=' '+group['source']['description'].split('\n\nRequires:')[0]
        assert title.strip() and description.strip()
        condition,view=split_technology_condition(records[g][2])
        view=normalized(view)
        assert view[:4]==bytes(4) and view[25:27]==bytes(2),(g,records[g][1],'unexpected presentation fields')
        name=localize(name_key,title);desc=localize('Modifier/'+g+'/Description',description)
        body=view[:25]+name+desc+view[27:]
        if condition:body=with_technology_condition(body,condition['technology'],condition['inverted'])
        records[g][2]=body
        presentations.append(dict(guid=g,title=title,description=description,
                                  name_key=name[2:-1].decode(),description_key=desc[2:-1].decode(),
                                  source_ids=sorted(owners[g]),effects_before_sha256=before[g]))
    assert all(records[g]==row for g,row in native.items()),'Native modifier changed'
    return pack_modifiers(records),dict(records=presentations,cumulative_families=families)
