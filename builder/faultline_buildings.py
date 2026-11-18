"""Faultline's registered construction templates, built from owned prefabs."""
import re

from tools.native_binary import Cursor, SchemaError, Span, entry, f32, replace_spans, string, u32


BUILDINGS_PATH = "configs/frostpunkbuildingsconfig.bin"
RELAY = "Signal Relay"
MAGAZINE = "Coal Magazine"
VALVE_WORKS = "Valve Works"
RELIEF_DISPATCH = "Relief Dispatch"
RELAY_RESET = 25
MAGAZINE_SAVING = 20
EXCLUSIONS = "4d5455165b7e149569489bd856c02b84"
TEMPLATE_FOLDER = "gameentities/buildings/"
FACTORY = TEMPLATE_FOLDER+"resourceprocessing/prefabfactory.binarytemplate"
DEFINITIONS = {
    RELAY: dict(path=TEMPLATE_FOLDER+"faultline_signal_relay.binarytemplate",
                donor=TEMPLATE_FOLDER+"steamhub.binarytemplate", native="Steam Hub", tab="Tech",
                price={"Steel":16,"Wood":12}, reconnect_at=RELAY_RESET),
    MAGAZINE: dict(path=TEMPLATE_FOLDER+"faultline_coal_magazine.binarytemplate",
                   donor=TEMPLATE_FOLDER+"resourcedepot.binarytemplate", native="Resource Depot", tab="Resources",
                   price={"Wood":30,"Steel":25}, coal_capacity=1500),
    VALVE_WORKS: dict(path=TEMPLATE_FOLDER+"faultline_valve_works.binarytemplate", donor=FACTORY,
                     native="Factory", tab="Tech", price={"Wood":65,"Steel":55},
                     interior="UI/BuildingInteriors/EngeneersLab.dds",
                     description="Staff with engineers. Under General, queue Isolation Valve or Bypass Section orders for the buried main.",
                     orders={"FaultlineIsolationValve": dict(title="Machine Isolation Valve", output="Steam Tools",
                         inputs={"Steel":22,"Coal":15}, hours=5,
                         purpose="Machine a shut-off valve for the lake branch. The Works uses Steam Tools as its inventory for finished fittings."),
                             "FaultlineBypassSection": dict(title="Rivet Bypass Section", output="Steel Plates",
                         inputs={"Steel":30,"Wood":12,"Coal":12}, hours=6,
                         purpose="Rivet a pressure-rated branch for the ridge lift. Its Steel Plates are spent when you commission the bypass.")}),
    RELIEF_DISPATCH: dict(path=TEMPLATE_FOLDER+"faultline_relief_dispatch.binarytemplate", donor=FACTORY,
                          native="Factory", tab="Tech", price={"Wood":75,"Steel":40},
                          interior="UI/BuildingInteriors/Expedition/ExpeditionCenter.dds",
                          description="Staff with engineers. Under General, pack Clinic Sledges or Lift Sledges for the final evacuation.",
                          orders={"FaultlineClinicSledge": dict(title="Pack Clinic Sledge", output="Wooden Materials",
                              inputs={"Food Rations":35,"Wood":16}, hours=4,
                              purpose="Pack a clinic sledge with meals, bedding and splints. The manifest reserves its Wooden Materials for the convoy."),
                                  "FaultlineLiftSledge": dict(title="Pack Lift Sledge", output="Steel Plates",
                              inputs={"Coal":55,"Wood":15}, hours=5,
                              purpose="Pack a heavy sledge with fuel and rigging. The lift convoy spends its Steel Plates at departure.")}),
}


def building_guid(guid, name):
    return guid("faultline/building/"+name)


def build_orders(recipe, guid, icons):
    for name, spec in DEFINITIONS.items():
        for key, order in spec.get("orders", {}).items():
            recipe(key,order["title"],order["output"],1,order["inputs"],order["hours"],
                   None,icon=icons[order["output"]],building=name,
                   targets=[spec["path"].removeprefix(TEMPLATE_FOLDER).removesuffix(".binarytemplate")],
                   purpose=order["purpose"])
    return {key:[guid("recipe/"+key).hex()] for spec in DEFINITIONS.values() for key in spec.get("orders", {})}


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
    if count not in (118,118+len(DEFINITIONS)) or len(rows)!=count or c.count(32)!=25:
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
        order_ids=[guid("recipe/"+key) for key in spec.get("orders", {})]
        revised=customize(name,native,spec,uid,scenario,resources,loc,order_ids)
        components=list(re.finditer(rb"\x01[A-Za-z]+ComponentTemplate\0",revised))
        if len(components)!=Cursor(revised,26).count(32):
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


def customize(name, native, spec, uid, scenario, resources, loc, orders):
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
        # Drop the donor restrictions while retaining the three vector headers
        # that precede the availability requirements in the native layout.
        edits.append((Span(building+39,begin+4+len(donation)),u32(0)*3+u32(1)+gate))
        title=string("@Buildings/SteamHub/Name")
        description=string("@Buildings/SteamHub/Description")
        short=string("@Buildings/SteamHub/Tech2")
        text="Sends signals through the buried main. A completed relay lets the line reconnect at 25% stress after a trip."
        pos=native.index(short)
        edits.append((Span(pos,pos+len(short)),loc("Faultline/Buildings/Relay/Short",text)))
        # A relay uses the main to signal, without making a heat zone. Drop the
        # complete heater component and its local controls from the cloned asset.
        components=list(re.finditer(rb"\x01[A-Za-z]+ComponentTemplate\0",native))
        removed=0
        for current, following in zip(components,components[1:]):
            if current[0] in (string("FrostpunkHeaterComponentTemplate"),string("FrostpunkAbilitiesComponentTemplate")):
                if native.count(native[current.end():current.end()+16])!=1:
                    raise SchemaError("Relay would orphan a component link")
                edits.append((Span(current.start(),following.start()),b""))
                removed+=1
        if not removed:
            raise SchemaError("Relay's heater component has no native boundary")
        edits.append((Span(26,30),u32(Cursor(native,26).count(32)-removed)))
        original=u32(1)+resources["Steel"]+u32(20)
    elif name==MAGAZINE:
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
    else:
        donation=string("FrostpunkTechnologyRequirement")+bytes(17)+bytes.fromhex("7f2b6ceb4c5ce9a3f64a718986a73b7d")
        start=native.index(donation,building,economics)-4
        stop=start+4+len(donation)
        if native[start:start+4]!=u32(1) or native[stop:stop+4]!=f32(1.5):
            raise SchemaError("Unsupported Factory construction requirements")
        edits.append((Span(start,stop),u32(1)+gate))
        production=component(native,"Production")
        if native[production:production+4]!=u32(9) or len(orders)!=2:
            raise SchemaError("Unsupported mission production queue")
        edits.append((Span(production,production+4+9*16),u32(len(orders))+b"".join(orders)))
        interior=string("UI/BuildingInteriors/ResourceProcessing/Factory.dds")
        pos=native.index(interior,building,economics)
        edits.append((Span(pos,pos+len(interior)),string(spec["interior"])))
        title=string("@Buildings/PrefabFractory/Name")
        description=string("@Buildings/PrefabFractory/Description")
        text=spec["description"]
        short=string("@Buildings/PrefabFractory/Tech2")
        pos=native.index(short,building,economics)
        edits.append((Span(pos,pos+len(short)),loc("Faultline/Buildings/"+name+"/Short",text)))
        original=u32(3)+resources["Wood"]+u32(30)+resources["Steel"]+u32(15)+resources["Steam Cores"]+u32(1)
    if native[economics:economics+len(original)]!=original:
        raise SchemaError(f"Unexpected construction price: {name}")
    edits.append((Span(economics,economics+len(original)),cost))
    for field,source,label in (("Name",title,name),("Description",description,text)):
        for match in re.finditer(re.escape(source),native[building:economics]):
            position=building+match.start()
            edits.append((Span(position,position+len(source)),loc("Faultline/Buildings/"+name+"/"+field,label)))
    return replace_spans(native,edits)
