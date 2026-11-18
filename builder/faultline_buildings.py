"""Faultline's registered construction templates, built from owned prefabs."""
import re

from tools.native_binary import Cursor, SchemaError, Span, entry, f32, replace_spans, string, u32


BUILDINGS_PATH = "configs/frostpunkbuildingsconfig.bin"
RELAY = "Signal Relay"
MAGAZINE = "Coal Magazine"
RELAY_RESET = 20
MAGAZINE_SAVING = 20
EXCLUSIONS = "4d5455165b7e149569489bd856c02b84"
TEMPLATE_FOLDER = "gameentities/buildings/"
DEFINITIONS = {
    RELAY: dict(path=TEMPLATE_FOLDER+"faultline_signal_relay.binarytemplate",
                donor=TEMPLATE_FOLDER+"steamhub.binarytemplate", native="Steam Hub", tab="Tech",
                price={"Steel":16,"Wood":12}, radius=18, coal_per_hour=2),
    MAGAZINE: dict(path=TEMPLATE_FOLDER+"faultline_coal_magazine.binarytemplate",
                   donor=TEMPLATE_FOLDER+"resourcedepot.binarytemplate", native="Resource Depot", tab="Resources",
                   price={"Wood":30,"Steel":25}, coal_capacity=1500),
}


def building_guid(guid, name):
    return guid("faultline/building/"+name)


def component(data, name):
    signature=string("Frostpunk"+name+"ComponentTemplate")
    return data.index(signature)+len(signature)+16


def building_table(data):
    # The seven preceding mappings contain two GUIDs and a vector of GUIDs.
    c=Cursor(data)
    for _ in range(c.count(16)):
        c.entry()
        c.string()
    if c.count(8)!=7:
        raise SchemaError("Unsupported building-tab mapping")
    for _ in range(7):
        c.take(32)
        c.take(c.count(16)*16)
    count_at=c.position
    count=c.count(160)
    rows={}
    for _ in range(count):
        name=c.string()
        rows[name]=(c.guid(),c.guid(),c.boolean())
    if count not in (118,120) or len(rows)!=count or c.count(32)!=25:
        raise SchemaError("Unsupported construction directory")
    return count_at,count,c.position-4,rows


def exclusion_table(data):
    token=entry("Default", EXCLUSIONS)
    start=data.index(token)
    c=Cursor(data,start-4)
    count=c.count(8)
    if count not in (7,8):
        raise SchemaError("Unsupported excluded-buildings directory")
    rows=[]
    for _ in range(count):
        name,uid=c.entry()
        end_header=c.position
        excluded=c.take(c.count(96)*16)
        rows.append((name,uid,end_header,c.position,excluded))
    if c.u32() not in (30,31):
        raise SchemaError("Unsupported city setup boundary")
    return start-4,c.position-4,rows


def restrict_scenarios(data, identity, notes):
    table_start,end,rows=exclusion_table(data)
    if len(rows)!=7:
        raise SchemaError("Unexpected installed construction exclusions")
    amendments=[(Span(table_start,table_start+4),u32(len(rows)+1))]
    new_ids=b"".join(bytes.fromhex(row["guid"]) for row in notes)
    for _,_,begin,stop,excluded in rows:
        updated=excluded+new_ids
        amendments.append((Span(begin,stop),u32(len(updated)//16)+updated))
    default=rows[0][4]
    variant=entry("NI Faultline Construction",identity("faultline-construction"))+u32(len(default)//16)+default
    amendments.append((Span(end,end),variant))
    return replace_spans(data,amendments)


def build(buildings, source, guid, scenario, resources, loc):
    count_at,count,end,rows=building_table(buildings)
    registrations=[]
    templates={}
    metadata=[]
    for name,spec in DEFINITIONS.items():
        category,native_id,enabled=rows[spec["native"]]
        if not enabled:
            raise SchemaError(f"Inactive construction donor: {name}")
        native=source(spec["donor"])
        if native[:16].hex()!=native_id:
            raise SchemaError(f"Template identity differs: {name}")
        uid=building_guid(guid,name)
        revised=customize(name,native,spec,uid,scenario,resources,loc)
        components=list(re.finditer(rb"\x01[A-Za-z]+ComponentTemplate\0",revised))
        if len(components)!=Cursor(native,26).count(32):
            raise SchemaError(f"Unsupported template component directory: {name}")
        # Independent component keys leave the source prefab and saved copies
        # of it untouched. Any internal links move with their components.
        for item in components:
            identity=revised[item.end():item.end()+16]
            revised=revised.replace(identity,guid("faultline/component/"+name+"/"+item[0][1:-1].decode()))
        registrations.append(string(name)+bytes.fromhex(category)+uid+b"\1")
        templates[spec["path"]]=(spec["donor"],revised)
        metadata.append(dict(name=name,guid=uid.hex(),**spec))
    result=replace_spans(buildings,[(Span(count_at,count_at+4),u32(count+len(registrations))),
                                   (Span(end,end),b"".join(registrations))])
    return result,templates,metadata


def customize(name, native, spec, uid, scenario, resources, loc):
    building=component(native,"Building")
    economics=component(native,"BuildingEconomics")
    gate=string("FrostpunkScenarioRequirement")+bytes(17)+bytes.fromhex(scenario)+b"\0"
    cost=u32(len(spec["price"]))+b"".join(resources[item]+u32(n) for item,n in spec["price"].items())
    edits=[(Span(0,16),uid)]
    if name==RELAY:
        donation=string("FrostpunkTechnologyRequirement")+bytes(17)+bytes.fromhex("6a330b7d72d2e0a06a454943cf2980a1")
        begin=native.index(donation,building,economics)-4
        if (native[begin:begin+4]!=u32(1) or native[building+39:building+43]!=u32(1)
                or not native[begin+4+len(donation):].startswith(f32(1.5))):
            raise SchemaError("Unsupported Steam Hub construction requirements")
        # Drop the donor's Last Autumn construction restriction. Keep the
        # building available only in Faultline via the native scenario gate.
        edits.append((Span(building+39,begin+4+len(donation)),u32(0)+u32(1)+gate))
        title=string("@Buildings/SteamHub/Name")
        description=string("@Buildings/SteamHub/Description")
        short=string("@Buildings/SteamHub/Tech2")
        text="A small heat zone. One completed Signal Relay lets the main reconnect at 20% stress after a trip."
        pos=native.index(short)
        edits.append((Span(pos,pos+len(short)),loc("Faultline/Buildings/Relay/Short",text)))
        heater=component(native,"Heater")
        base=native.index(string("Level range0"),heater)+len(string("Level range0"))
        second=native.index(string("Level range1"),base)
        if native[base:second]!=bytes(4)+f32(24)+u32(0)+u32(1)+resources["Coal"]+f32(3):
            raise SchemaError("Unsupported Steam Hub heat range or fuel rate")
        # One heat level/range, with no factory tech dependency for range.
        limit=native.index(string("~HeatLight"),second)
        footer=native[limit-8:limit]
        if footer!=f32(100)+u32(2):
            raise SchemaError("Unsupported Steam Hub heater footer")
        edits.append((Span(heater,base),b"\1"+u32(1)+string("Level range0")))
        edits.append((Span(base,limit-8),bytes(4)+f32(spec["radius"])+u32(0)+u32(1)
                      +resources["Coal"]+f32(spec["coal_per_hour"])))
        original=u32(1)+resources["Steel"]+u32(20)
    else:
        at=building+67
        if native[at:at+8]!=u32(0)+f32(1.5):
            raise SchemaError("Unsupported Resource Depot construction requirements")
        edits.append((Span(at,at+4),u32(1)+gate))
        title=string("@Buildings/ResourceDepot/Name")
        description=string("@Buildings/ResourceDepot/Description")
        text="Assign this depot to coal to add 1,500 storage. A completed Coal Magazine saves 20 coal on every Broken Mile shipment."
        original=u32(2)+resources["Wood"]+u32(40)+resources["Steel"]+u32(20)
        depot=component(native,"UndesignatedResourceDepot")
        if native[depot:depot+24]!=u32(5)+resources["Coal"]+u32(900):
            raise SchemaError("Unsupported Resource Depot storage")
        edits.append((Span(depot,depot+4+20*5),u32(1)+resources["Coal"]+u32(spec["coal_capacity"])))
    if native[economics:economics+len(original)]!=original:
        raise SchemaError(f"Unexpected construction price: {name}")
    edits.append((Span(economics,economics+len(original)),cost))
    for field,source,label in (("Name",title,name),("Description",description,text)):
        position=native.index(source)
        edits.append((Span(position,position+len(source)),loc("Faultline/Buildings/"+name+"/"+field,label)))
    return replace_spans(native,edits)
