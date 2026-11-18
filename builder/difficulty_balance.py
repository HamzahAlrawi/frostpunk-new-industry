"""Locate supported balance fields in the final serialized game records."""
import struct

from research_curation import modifiers, normalized
from tools.native_binary import Cursor, SchemaError, f32, string, u32
from tools.native_scenario import compact, typed


ATTITUDES = {
    "GOLD [Common] Hope rise - slightly": (82,0.02),
    "GOLD [Common] Hope rise - moderately": (82,0.04),
    "GOLD [Common] Hope rise - greatly": (82,0.08),
    "GOLD [Common] Discontent fall - slightly": (114,-0.02),
    "GOLD [Common] Discontent fall - moderately": (114,-0.05),
    "GOLD [Common] Discontent fall - greatly": (114,-0.1),
    "[Builders] Motivation System - Workers Council": (82,0.05),
}


def clone_attitudes(native, guid):
    # The native scripted attitude effects are shared by other scenarios.
    # Give new laws their own copies so changing a preset leaves them intact.
    count = Cursor(native).count(256)
    prefix = u32(1)+typed("FrostpunkModifySocialAttitudesEffect")+compact("FrostpunkAllAgentsSelector")
    prefix += bytes.fromhex("00000000020000000000000001")
    records, ids, fields = [], {}, []
    position = 4
    for name,(offset,value) in ATTITUDES.items():
        marker = b"\1"+string(name)
        start = native.index(marker)+len(marker)+16
        body = native[start:start+142]
        if len(prefix)!=82 or not body.startswith(prefix) or body[offset:offset+4]!=f32(value):
            raise SchemaError("Unsupported law attitude effect: "+name)
        if native[start+142:start+144]!=b"\1\1":
            raise SchemaError("Unsupported law attitude effect boundary")
        uid = guid("difficulty/law/"+name)
        ids[name] = uid
        header = b"\1"+string("NI Law "+name)+uid
        records.append(header+body)
        fields.append((position+len(header)+offset,"f","law",0,-1,1))
        position += len(header)+len(body)
    return u32(count+len(records))+b"".join(records)+native[4:],ids,fields


def field_locations(data, pristine, techs, members, laws, sources, resources, texts):
    records = modifiers(data)
    native = modifiers(pristine)
    active = set().union(*map(set, members.values()))
    root = {
        "upgrade": {t["id"]: t["global_effects"]+[g for k in ("effects","extra_effects") for _,g in t[k]]
                    for t in techs if t["guid"] in active},
        "law": {row["id"]: [row["modifier"]] for row in laws},
    }
    views = {uid: normalized(raw) for uid,(_,_,raw) in records.items() if uid not in native}

    def descendants(roots):
        result = set(roots)&views.keys()
        for uid in sorted(result):
            if records[uid][0] == "Global":
                body = views[uid]
                size = struct.unpack_from("<I",body,77)[0]
                if size>120 or len(body)<81+size*32:
                    raise SchemaError("Unsupported global modifier binding")
                result.update(body[start+16:start+32].hex() for start in range(81,81+size*32,32)
                              if body[start+16:start+32].hex() in views)
        return result

    by_source = {group:{key:descendants(ids) for key,ids in members.items()} for group,members in root.items()}
    by_group = {group:set().union(*ids.values()) for group,ids in by_source.items()}
    if by_group["upgrade"] & by_group["law"]:
        raise SchemaError("A modifier is shared between laws and technology")

    fields, scaled = [], set()
    for group,ids in by_group.items():
        for uid in sorted(ids):
            kind, name, raw = records[uid]
            view = views[uid]
            header = typed("Frostpunk"+kind+"Modifier")+bytes.fromhex(uid)+b"\1"+name+b"\0"
            start = data.index(header) + len(header)
            assert data[start:start+len(raw)]==raw
            shift = len(raw)-len(view)
            for offset,code,neutral,lower,upper in passive_fields(view,kind,group,resources):
                fields.append((start+shift+offset,code,group,neutral,lower,upper))
                scaled.add(uid)
    assert len({field[0] for field in fields})==len(fields)
    assert all(by_group[group]&scaled for group in by_group)
    keys = {
        "upgrade": {key for source,ids in by_source["upgrade"].items() if ids&scaled
                    for key in ("Mods/NewIndustry/Tech/"+source+"/Description","Mods/NewIndustry/Tech/"+source+"/Short")
                    if key in texts},
        "law": {key for source in by_source["law"] for key in texts
                if key=="Mods/NewIndustry/Laws/"+source+"/Description"},
    }
    for row in sources:
        uid = row["guid"]
        if uid in scaled:
            group = "law" if uid in by_group["law"] else "upgrade"
            keys[group].add(row["description_key"])
    return sorted(fields),{group:sorted(entries) for group,entries in keys.items()}


def passive_fields(body, kind, group, resources):
    def ratio(offset, low=1, high=6, neutral=1):
        value = struct.unpack_from("<f",body,offset)[0]
        if low<=value<=high and value!=neutral:
            yield offset,"f",neutral,0.05,12

    if kind == "Global":
        size = struct.unpack_from("<I",body,77)[0]
        if len(body)==186+size*32:
            for offset in (65,69,126+size*32):
                yield from ratio(offset)
            yield from ratio(150+size*32,0.0,1.0,0)
            yield from ratio(166+size*32,0.05,1)
        return
    if kind!="Place" or body[25:27]!=b"\0\0":
        return
    atlas = b"\1UI\\Tiles\\Icons.dds\0"
    shift = len(atlas)-1 if body.startswith(atlas,32) else 0
    if body[32] and not shift:
        return
    if len(body)<238+shift or struct.unpack_from("<II",body,76+shift)!=(0,2):
        return
    for offset in (72,84,88):
        yield from ratio(offset+shift)
    if len(body)==238+shift:
        for offset in (149,157):
            yield from ratio(offset+shift)
        if group=="law":
            insulation=struct.unpack_from("<i",body,96+shift)[0]
            if insulation>=2:
                yield 96+shift,"i",0,1,3
    fuel = u32(1)+resources["Coal"]+u32(0)
    if len(body)==262+shift and body[136+shift:160+shift]==fuel:
        yield from ratio(160+shift,0.05,1)
    storage = u32(8)+resources["Augmentation parts"]
    if body.count(storage)==1:
        start = body.index(storage)+4
        for offset in range(start,start+8*24,24):
            if body[offset+16:offset+20]!=bytes(4):
                raise SchemaError("Unsupported storage multiplier")
            yield from ratio(offset+20)
