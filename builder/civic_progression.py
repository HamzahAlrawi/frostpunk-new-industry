"""Passive civic laws and thermal research using native law/effect schemas."""
import re
import struct

from research_curation import modifiers, normalized, pack_modifiers
from city_mastery import building_ids
from progression_choices import COLD
from law_branches import default_laws
from law_layout import layout_errors

LAW_MARKER = b'\1FrostpunkSociotechEntry\0'
LAW_BOOK = 'Civic Charters'
NATIVE_BOOK_NAMES = ('Purpose', 'Adaptation', 'Labour', 'ADMINISTRATION')
BOOK_GUIDS = {'Adaptation':'aa9e39dee99e599452414bfb60af2960',
              'Administration':'f80dd07aa593789558485d8c0cb8de65'}
CHARTER_POSITIONS = ((-9,-8),(-3,-8),(3,-8),(9,-8))
POLICIES = (
    ('Reassurance', 'Public Reassurance Charter', 'Public Assurance Offices',
     'Hope rises greatly when signed. Public Houses, Fighting Arenas, Care Houses and places of worship gain +1 insulation.',
     ('GOLD [Common] Hope rise - greatly',), 'civic-warmth'),
    ('Grievances', "Workers' Grievance Hearings", 'Independent Grievance Offices',
     'Discontent falls greatly when signed. Medical Posts and Infirmaries gain 75% healing efficiency for human crews and automatons.',
     ('GOLD [Common] Discontent fall - greatly',), 'medical-relief'),
    ('Recovery', 'Rest and Recovery Covenant', 'Public Recovery Standards',
     'Hope rises moderately and discontent falls moderately when signed. Cold-related illness is reduced by 25%.',
     ('GOLD [Common] Hope rise - moderately', 'GOLD [Common] Discontent fall - moderately'), 'cold-health'),
    ('MutualAid', 'Storm Mutual Aid Charter', 'Civic Emergency Planning',
     'Hope rises greatly and discontent falls greatly when signed. Civic and healthcare buildings gain +2 insulation.',
     ('GOLD [Common] Hope rise - greatly', 'GOLD [Common] Discontent fall - greatly'), 'storm-civic'),
)


def law_records(data):
    marks = list(re.finditer(LAW_MARKER, data))
    guard = data.index(b'\1\1Gender_Male\0', marks[-1].start()) - 4
    # The label vector is not adjacent to the laws: 89 native society bytes
    # follow the last native law. Locate its actual, pinned-build footer.
    endings = list(re.finditer(re.escape(bytes.fromhex('00010000000000004040')),
                               data[marks[-1].start():guard]))
    assert len(endings) == 1, 'Ambiguous final law boundary'
    end = marks[-1].start() + endings[0].end()
    assert struct.unpack_from('<I', data, marks[0].start() - 4)[0] == len(marks)
    records = {}
    for i, marker in enumerate(marks):
        stop = marks[i + 1].start() if i + 1 < len(marks) else end
        raw = data[marker.start():stop]
        name_end = raw.index(0, len(LAW_MARKER) + 1)
        name = raw[len(LAW_MARKER) + 1:name_end].decode()
        records[name] = raw
    return marks[0].start() - 4, end, records


def book_records(data):
    law_count, _, _ = law_records(data)
    names = NATIVE_BOOK_NAMES + ((LAW_BOOK,) if b'\1\1Civic Charters\0' in data[:law_count] else ())
    starts = sorted((data.index(b'\1\1'+name.encode()+b'\0'),name) for name in names)
    count_pos = starts[0][0]-4
    assert struct.unpack_from('<I',data,count_pos)[0] == len(starts)
    return count_pos, {name:data[start:starts[i+1][0] if i+1<len(starts) else law_count]
                       for i,(start,name) in enumerate(starts)}


def law_layout(raw):
    loc = raw.index(b'\1@')
    for _ in range(2):loc=raw.index(0,loc+1)+1
    position=loc+1 if raw[loc]==0 else raw.index(0,loc+1)+1
    icon_x,icon_y,x,y=struct.unpack_from('<4i',raw,position)
    return loc,(x,y),raw[position+16:position+32].hex()


def law_layout_errors(new_laws, native):
    points={}
    for name,raw in native.items():
        _,pos,category=law_layout(raw);points[name]=(pos,category)
    return layout_errors(new_laws,points)


def law_exclusion_group(raw):
    loc,_,_=law_layout(raw)
    position=loc+1 if raw[loc]==0 else raw.index(0,loc+1)+1
    group=position+65
    assert raw[group] in (0,1)
    return raw[group+1:raw.index(0,group+1)].decode() if raw[group] else None


def add_civic(technology, specs, techinfo, data, buildings, guid, localize, category, resources):
    records = modifiers(data)
    places = building_ids(buildings)
    trailer = bytes.fromhex(techinfo[0]['rest'])[-25:]
    neutral = bytearray(normalized(records['d87b131d3367ed86d04efc1f7c1f7a5a'][2]))
    assert len(neutral) == 186 and struct.unpack_from('<I', neutral, 77)[0] == 0
    struct.pack_into('<f', neutral, 150, 0)  # Remove source automaton bonus.
    place = bytearray(normalized(records['30aa2c27e02dce83494392ae5c1f2261'][2]))
    assert len(place) == 238
    struct.pack_into('<f', place, 173, 1)  # Remove source treatment side effect.
    # Prove the counted global-to-place vector against an actual native record.
    sample = normalized(records['ca7a0f54c35189a76048d9a666f3211f'][2])
    assert sample[:77] + bytes(4) + sample[113:] == bytes(neutral)
    policy_modifiers = {}
    civic = ['PublicHouse','FightClube','CareHouse','HouseOfPrayer','Temple','FaithKeepers',
             'Shrine','Neighborhood watch tower','Guardpost','Prison','CensusStation','HospitalOfMercy']
    medical = ['Medical Post','Ambulatorium']

    def register(key, kind, body):
        g = guid('civic/' + key).hex()
        assert g not in records
        records[g] = [kind, ('NI civic/' + key).encode(), bytes(body)]
        return g

    for key, _, _, _, _, mechanic in POLICIES:
        body = bytearray(neutral)
        if mechanic == 'cold-health':
            struct.pack_into('<f', body, 166, 0.75)
        else:
            site = bytearray(place)
            if mechanic == 'medical-relief':
                struct.pack_into('<ff', site, 84, 1.75, 1.75)
                names = medical
            else:
                struct.pack_into('<i', site, 96, 2 if mechanic == 'storm-civic' else 1)
                names = civic + medical if mechanic == 'storm-civic' else civic
            g = register('law/' + key + '/places', 'Place', site)
            pairs = b''.join(places[n] + bytes.fromhex(g) for n in names)
            body = body[:77] + struct.pack('<I', len(names)) + pairs + body[81:]
        policy_modifiers[key] = register('law/' + key, 'Global', body)

    laws = []
    for tier, (key, title, research, description, effects, mechanic) in enumerate(POLICIES):
        identity = 'Civic' + key
        text = 'Unlocks the signable ' + title + ' in the upper charter branch of Adaptation (Administration in The Last Autumn). ' + description
        technology(identity, research, text, tier, 20, [], {'Wood': 18 + tier * 14, 'Steel': 6 + tier * 8},
                   4 + tier * 3, (0, 2), category)
        specs[-1].update(scenarios=list(COLD) + ['Builders'], shared_all_scenarios=True,
                         mechanic='signable-civic-law', added_in='3.12.0')
        laws.append(dict(id=identity, title=title, research=specs[-1]['guid'], description=description,
                         effects=list(effects), modifier=policy_modifiers[key], research_title=research,
                         position=list(CHARTER_POSITIONS[tier]), cooldown=18, book='Adaptation',
                         book_guid=BOOK_GUIDS['Adaptation'], scenarios=list(COLD)))

    source = next(t for t in specs if t['id'] == 'CitywideLagging')
    for number, tier, cost in ((4, 3, (420, 320, 3)), (5, 4, (560, 420, 5)), (6, 5, (720, 560, 8))):
        key = 'CitywideLagging' + str(number)
        site = bytearray(place)
        struct.pack_into('<i', site, 96, 2 if number == 6 else 1)
        g = register(key + '/insulation', 'Place', site)
        global_body = bytearray(neutral)
        if number == 4:
            struct.pack_into('<f', global_body, 166, 0.65)
            extra = 'Citizens also suffer 35% less cold-related illness.'
        elif number == 5:
            struct.pack_into('<f', global_body, 69, 1.5)
            extra = 'All heat zones also gain 50% radius.'
        else:
            struct.pack_into('<f', global_body, 166, 0.5)
            extra = 'Citizens also suffer 50% less cold-related illness.'
        global_id = register(key + '/global', 'Global', global_body)
        pairs = [(p.hex(), g) for p in places.values()]
        rest = struct.pack('<II', 2, 1) + bytes.fromhex(global_id) + struct.pack('<I', len(pairs))
        rest += b''.join(bytes.fromhex(p + effect) for p, effect in pairs) + bytes(4) + trailer
        material = dict(Wood=cost[0], Steel=cost[1]);material['Steam Cores'] = cost[2]
        technology(key, 'Citywide Thermal Envelope ' + ('IV','V','VI')[number - 4],
                   ('Every building that uses insulation gains +' + ('2' if number == 6 else '1') + ' insulation. ' + extra),
                   tier, 20, [], material, 32 + number * 3, tuple(source.get('icon', (0, 2))), category, rest=rest)
        specs[-1].update(scenarios=list(COLD), mechanic='citywide-thermal-envelope', added_in='3.12.0')
    laws.extend(default_laws(records,places,neutral,place,techinfo,resources,specs,guid))
    return pack_modifiers(records), laws


def build_laws(data, effects, laws, guid, localize, technology_requirement):
    count_pos, end, native = law_records(data)
    assert len(native) == 112
    source = native['[Adaptation- level 1] Burial Ceremony']
    # This passive donor has no on-sign effects, policy changes or quests. Its
    # illustration vector uses the native treemask illustration template; keep
    # the vector and give each new visual instance a distinct identifier.
    illustration = bytes.fromhex('1fb45ef57ba8a9994640f8a9e0a89eca')
    p = source.index(illustration)
    assert source[p - 4:p] == struct.pack('<I', 1) and source[p + 16:p + 32] == bytes.fromhex('07d55c34068f579108455c96537be769')
    source = re.sub(rb'\x01Oneliners/[^\0]+\0', b'\0', source)
    display = source.index(b'\1@Generated')
    layout = display
    for _ in range(2):layout = source.index(0, layout + 1) + 1
    assert source[layout] == 0
    assert source[layout + 46:layout + 54] == struct.pack('<II', 2, 0)
    # Locate the on-sign vector against a native law with an actual effect.
    # The earlier zero vector at +50 belongs to modifier metadata, not effects.
    probe = native['Builders [LifeConditions - level 0] Pub']
    probe_layout = probe.index(b'\1@Generated')
    for _ in range(2):probe_layout = probe.index(0,probe_layout+1)+1
    assert probe.index(b'\1FrostpunkSwitchEffect\0',probe_layout) == probe_layout+71
    assert struct.unpack_from('<I',probe,probe_layout+67)[0] == 1
    assert source[layout+67:layout+71] == bytes(4)
    # Native exclusive alternatives share an exclusion-group string at +66.
    # Its variable length shifts the following on-sign vector. Use this native
    # mechanism for new forks, rather than NOT(sibling), which can introduce a
    # misleading research-style dependency line between the two alternatives.
    group_probe=native['[Adaptation- level 0] Cemetery']
    group_layout=group_probe.index(b'\1@Generated')
    for _ in range(2):group_layout=group_probe.index(0,group_layout+1)+1
    assert group_probe[group_layout+66:group_layout+75]==b'\1Burials\0'
    assert b'\1FrostpunkSociotechExclusionRequirement\0'+bytes(17)+b'\1Burials\0' in group_probe
    # Retain the old category GUID only for saves. It is appended after all four
    # native books and hidden with P AND NOT(P), so it cannot occupy a book slot.
    start = data.index(b'\1\1Adaptation\0')
    stop = data.index(b'\1\1Labour\0', start)
    category = data[start:stop]
    title_at = category.index(b'\1@Generated')
    gate=technology_requirement(bytes.fromhex(laws[0]['research']))
    negate=b'\1FrostpunkCompositeRequirement\0'+bytes(17)+struct.pack('<II',2,1)+gate
    header = b'\1\1' + LAW_BOOK.encode() + b'\0' + guid('civic-law-book') + struct.pack('<I',2) + gate + negate
    tail = category[title_at:]
    tail = re.sub(rb'\x01@Generated/[^\0]+\0', lambda m: localize('Laws/Book/' + str(m.start()), LAW_BOOK), tail)
    category = header + tail
    first = data.index(b'\1\1Purpose\0')
    assert struct.unpack_from('<I', data, first - 4)[0] == 4
    predefined = {m[1].decode(): m[2] for m in re.finditer(rb'\x01\x01([ -~]+)\0(.{16})', effects, re.S)}
    switch_start = data.index(b'\1FrostpunkSwitchEffect\0')
    branch_start = data.index(b'\1FrostpunkCreateDilemmaEffect\0', switch_start)
    switch_prefix = data[switch_start:branch_start]
    assert b'\1\1Builders\0' in switch_prefix
    other = b'\1\1Other\0' + struct.pack('<II', 0, 1)
    # Distinct scenario entries allow the native book unlock rules to decide
    # which branch is shown. Original four GUIDs retain Arks/other cold saves.
    cold=list(laws);autumn=[]
    for law in cold:
        variant=dict(law,id='Autumn'+law['id'],book='Administration',
                     book_guid=BOOK_GUIDS['Administration'],scenarios=['Builders'])
        if law.get('default_available'):
            variant.update(title=law['autumn_title'],description=law['autumn_description'],
                           modifier=law['autumn_modifier'],benefits=law['autumn_benefits'],
                           requires_laws=['Autumn'+key for key in law['requires_laws']],
                           excludes_laws=['Autumn'+key for key in law['excludes_laws']])
        else:variant['legacy_equivalent']=guid('law/'+law['id']).hex()
        autumn.append(variant)
    # Retain the published order of the eight older entries as well as their IDs.
    laws[:]=([law for law in cold+autumn if not law.get('default_available')]
             +[law for law in cold+autumn if law.get('default_available')])
    assert not law_layout_errors(laws,native), law_layout_errors(laws,native)
    titles={law['id']:law['title'] for law in laws}
    output = []
    for law in laws:
        group=('NI/choices/'+law['book']+'/'+law['family']) if law.get('excludes_laws') else None
        law['exclusion_group']=group
        record = bytearray(source[layout:])
        record = bytearray(bytes(record).replace(illustration,guid('law-illustration/'+law['id'])))
        law_icon = (2, 13)
        struct.pack_into('<4i', record, 1, *law_icon, *law['position'])
        record[17:33] = bytes.fromhex(law['book_guid'])
        struct.pack_into('<f', record, 42, law['cooldown'])
        on_sign = []
        for name in law['effects']:
            # Last Autumn uses Motivation, with its own existing native effect.
            effect = b'\1FrostpunkPredefinedEffect\0' + predefined[name]
            if 'Hope rise' in name:
                motivation = b'\1FrostpunkPredefinedEffect\0' + predefined['[Builders] Motivation System - Workers Council']
                effect = switch_prefix + motivation + other + effect
            on_sign.append(effect)
        on_sign.append(b'\1FrostpunkApplyModifierEffect\0' + bytes.fromhex(law['modifier']))
        assert record[67:71] == bytes(4)
        record[67:71] = struct.pack('<I', len(on_sign)) + b''.join(on_sign)
        if group:
            assert record[66]==0
            record[66:67]=b'\1'+group.encode()+b'\0'
        # Replace all four native locale references, without inheriting its text.
        text = law['description'] + ' In The Last Autumn, the Hope effect is replaced by a native Motivation benefit.'
        if law.get('default_available'):
            text+='\n\nNo research required. '
            parents=law.get('requires_laws',[])
            text+=('First sign: '+', '.join(titles[key] for key in parents)+'. ') if parents else 'This branch starts immediately when the scenario permits law signing. '
            if law.get('excludes_laws'):text+='Alternative to '+', '.join(titles[key] for key in law['excludes_laws'])+'; choose one. '
            text+='Tree: '+law['family_title']+'. Book: '+law['book']+'. Passive benefits remain after signing.'
        else:text += '\n\nFirst research: ' + law['research_title'] + '. Sign in the upper charter branch of ' + law['book'] + '. Passive benefits remain after signing.'
        def law_text(match):
            content = 'Signed: ' + law['title'] + '.' if b'Popup notification text' in match[0] else law['description']
            return localize('Laws/' + law['id'] + '/Text/' + str(match.start()), content)
        record = re.sub(rb'\x01@Generated/[^\0]+\0', law_text, bytes(record))
        prefix = LAW_MARKER + b'\1NI ' + law['id'].encode() + b'\0' + guid('law/' + law['id']) + b'\1'
        required=([technology_requirement(bytes.fromhex(law['research']))] if law.get('research') else [])
        if group:
            required.append(b'\1FrostpunkSociotechExclusionRequirement\0'+bytes(17)+b'\1'+group.encode()+b'\0')
        for parent in law.get('requires_laws',[]):
            required.append(b'\1FrostpunkSociotechRequirement\0'+bytes(17)+guid('law/'+parent))
        if law.get('legacy_equivalent'):
            old=b'\1FrostpunkSociotechRequirement\0'+bytes(17)+bytes.fromhex(law['legacy_equivalent'])
            required.append(b'\1FrostpunkCompositeRequirement\0'+bytes(17)+struct.pack('<II',2,1)+old)
        prefix += struct.pack('<I',len(required)) + b''.join(required) + bytes(4)
        prefix += localize('Laws/' + law['id'] + '/Name', law['title']) + localize('Laws/' + law['id'] + '/Description', text)
        output.append(prefix + record)
        law.update(guid=guid('law/' + law['id']).hex(), icon=list(law_icon), native_effects=[predefined[name].hex() for name in law['effects']])
        law['required_law_guids']=[guid('law/'+key).hex() for key in law.get('requires_laws',[])]
        law['excluded_law_guids']=[guid('law/'+key).hex() for key in law.get('excludes_laws',[])]
    # Native category and law indices stay intact. The last-law boundary above
    # excludes the unlabelled society fields that follow that vector.
    return (data[:first - 4] + struct.pack('<I', 5) + data[first:count_pos] + category
            + struct.pack('<I', len(native) + len(output)) + data[count_pos+4:end]
            + b''.join(output) + data[end:])
