"""Research-gated, repeatable building actions based on native ability records."""
import re
import struct

from automaton_efficiency import split_workplace_efficiency
from last_autumn import AUTUMN_TABS

ABILITIES_PATH = "configs/frostpunkabilitiesconfig.bin"
EDGE_OPERATIONS = {"FieldResearchSprints", "EmergencyHeatPacks"}
WINTERHOME_ONLY = {"CoalPressurePurge"}


def uint(value):
    return struct.pack("<I", value)


def f32(value):
    return struct.pack("<f", value)


def string(value):
    return b"\1" + value.encode() + b"\0"


def build_operations(technology, vanilla, source, guid, localize, costs, requirement, heating, exploration):
    abilities = (source/"common"/ABILITIES_PATH).read_bytes()
    entries = list(re.finditer(rb"\x01Frostpunk[A-Za-z]+Ability\x00\x01([ -~]+)\x00(.{16})", abilities, re.S))
    assert len(entries) == struct.unpack_from("<I", abilities)[0] == 77
    native_action = next(i for i,entry in enumerate(entries) if entry.group(1)==b"[Builders] ProtectiveStructure2")
    sample = abilities[entries[native_action].end():entries[native_action+1].start()]
    icon_atlas = string("UI\\SelectionPanel\\ability\\ability_icons_atlas.dds")
    icon_start = sample.index(icon_atlas)+len(icon_atlas)
    icon_suffix = sample[icon_start+16:]
    assert icon_suffix == bytes(16)
    modifier_effect = string("FrostpunkApplyModifierEffect")
    effect_start = sample.index(modifier_effect)+len(modifier_effect)
    action_flags = sample[effect_start+20:effect_start+28]
    assert action_flags == uint(2)+b"\0\0\1\1"
    instant = string("FrostpunkInstantEffectAbility")

    modifiers = (source/"common/configs/frostpunkmodifiersconfig.bin").read_bytes()
    place_class = string("FrostpunkPlaceModifier")
    records = list(re.finditer(rb"\x01Frostpunk[A-Za-z]+Modifier\x00(.{16})", modifiers, re.S))

    def modifier_source(native_id, expected_name):
        i = next(i for i,record in enumerate(records) if record.group(1).hex()==native_id)
        record = records[i]
        assert record.group().startswith(place_class)
        name = string(expected_name)
        assert modifiers[record.end():].startswith(name)
        return modifiers[record.end()+len(name):records[i+1].start()]

    new_modifiers = []

    def timed_modifier(key, name, original, old_duration, duration):
        assert original[:12] == uint(0)+f32(old_duration)+uint(2)
        effect_id = guid("field-operation/modifier/"+key)
        body = original[:4]+f32(duration)+original[8:]
        display = rb"\x01@Generated/ModifiersConfig/Modifiers/[^\x00]+/Display name\x00"
        body, changed = re.subn(display, lambda _:localize("FieldOperation/Modifier/"+key,name), body)
        assert changed==1
        new_modifiers.append(place_class+effect_id+string("NI "+key)+body)
        return effect_id

    boost = modifier_source("c8bd310dae22b2be794c754b57e56705","[Reconquest] Vault_EfficiencyBoost")
    boost = split_workplace_efficiency(boost)
    sprint = timed_modifier("ResearchSprint","Research Sprint",boost,12.0,6.0)
    overfire = timed_modifier("FurnaceOverfire","Furnace Overfire",boost,12.0,8.0)
    heat = modifier_source("34156f71336543af0e4fed3a6c7d9e95","UPGRADE: Warmer GatheringPost")
    assert heat[25]==1
    heat_offset = heat.index(0,26)-25+96
    assert heat[heat_offset-4:heat_offset+4]==uint(0)+uint(1)
    heat = heat[:heat_offset]+uint(2)+heat[heat_offset+4:]
    heat_packs = timed_modifier("EmergencyHeatPacks","Emergency Heat Packs",heat,-1.0,8.0)

    workshop = ["engineerslab.binarytemplate"]
    steelworks = ["resourceextraction/steelmine.binarytemplate", "resourceextraction/steelmine_steam.binarytemplate",
                  "resourceextraction/advancedoremine.binarytemplate"]
    heat_sites = ["resourceextraction/gatheringpost.binarytemplate","resourceprocessing/prefabfactory.binarytemplate",
                  "resourceprocessing/foodprocessing.binarytemplate"]
    actions = []
    attachments = {}
    metadata = []

    def add_action(key, title, effect_text, tier, column, tab, research_cost, hours, parents, targets,
                   activation_cost, effect, icon, ability_icon, cooldown=24):
        requirements = [["Drawing Boards (I)","Drafting Machines (II)","Mechanical Calculators (III)"][tier-1]]
        requirements.extend(name for _,name in parents)
        description = effect_text+f" Cooldown: {cooldown} hours per building."
        tech = technology(key,title,description+"\n\nRequires: "+", ".join(requirements)+".",tier,column,
                          [parent for parent,_ in parents],research_cost,hours,icon,tab,prerequisite_names=requirements)
        action_id = guid("field-operation/ability/"+key)
        data = instant+string("NI "+key)+action_id+uint(0)+uint(1)+requirement(tech)+bytes(17)
        data += localize("FieldOperation/"+key+"/Name",title)+bytes(6)+costs(activation_cost)+uint(0)+uint(1)
        data += effect+f32(cooldown)+action_flags+localize("FieldOperation/"+key+"/Description",description)
        data += icon_atlas+struct.pack("<4i",*ability_icon,10,10)+icon_suffix
        actions.append(data)
        for target in targets:
            attachments.setdefault("gameentities/buildings/"+target,[]).append(action_id)
        metadata.append({"id":key,"ability_guid":action_id.hex(),"requires":tech.hex(),"targets":targets,
                         "activation_cost":activation_cost,"cooldown_hours":cooldown,"description":description})

    sprint_desc = "Spend 12 coal and 4 food rations to give the selected Workshop +50% workplace efficiency for 6 hours."
    sprint_cost = {"Coal":12,"Food Rations":4}
    add_action("FieldResearchSprints","Research Sprint",sprint_desc,1,10,exploration,
               {"Wood":28,"Steel":12},6,[(guid("tech/WorkshopSpeed3"),"Workshop Test Rigs")],workshop,
               sprint_cost,modifier_effect+sprint,(0,2),(0,2))
    add_action("AutumnFieldResearchSprints","Research Sprint",sprint_desc,1,8,AUTUMN_TABS["heat"],
               {"Wood":28,"Steel":12},6,[(guid("tech/AutumnWorkshopSpeed3"),"Workshop Test Rigs")],workshop,
               sprint_cost,modifier_effect+sprint,(0,2),(0,2))
    add_action("FurnaceOverfire","Furnace Overfire","Spend 22 coal to give the selected Steelworks +50% workplace efficiency for 8 hours.",
               2,16,heating,{"Wood":43,"Steel":25},8,[(vanilla["R 3_Steam Steel Mine"],"Steam Steelworks")],steelworks,
               {"Coal":22},modifier_effect+overfire,(8,0),(3,6))
    add_action("EmergencyHeatPacks","Emergency Heat Packs",
               "Spend 20 coal to give the selected Gathering Post, Cookhouse, or Factory two extra heat levels for 8 hours.",
               1,4,heating,{"Wood":28,"Steel":10},6,[],heat_sites,
               {"Coal":20},modifier_effect+heat_packs,(5,9),(3,4))
    stress_effect = string("FrostpunkModifyGeneratorEffect")+f32(-0.18)+f32(0)
    add_action("CoalPressurePurge","Coal Pressure Purge",
               "Use the Repair Station to spend 45 coal and reduce current Generator stress by 18 percentage points.",
               3,4,exploration,{"Wood":54,"Steel":30},9,[(vanilla["[Winterhome] E 1_RepairStation"],"Repair Station")],
               ["repairstation.binarytemplate"],{"Coal":45},stress_effect,(8,7),(4,4))

    return (uint(len(entries)+len(actions))+abilities[4:]+b"".join(actions),new_modifiers,attachments,metadata)


def attach_actions(template, actions):
    marker = string("FrostpunkAbilitiesComponentTemplate")
    offset = template.index(marker)+len(marker)+16
    count, = struct.unpack_from("<I",template,offset)
    assert 1<=count<=12
    end = offset+4+count*16
    assert template[end:end+10] == b"\1Frostpunk"
    return template[:offset]+uint(count+len(actions))+template[offset+4:end]+b"".join(actions)+template[end:]
