"""Check story registration and exercise all paths from serialized records."""
from itertools import product

from tools.native_binary import Cursor, entry, string, u32
from tools.scenario_model import World
from tools.story_schema import DEFAULT, DEFAULT_EVENTS, NAME, ROAD_NAME, FAULTLINE_NAME, NATIVE_INTRO, WEATHER_DONOR, forecast_record
from winter_road_maps import CITY, NATIVE_CITY, NATIVE_WORLD, WORLD


def validate_registration(before, after, story):
    assert after[:20]==before[:16]+u32(17)
    assert after[20:].startswith(before[20:before.index(entry("Default",DEFAULT_EVENTS))-4])
    start=after.index(entry(NAME,story["scenario"]))
    cursor=Cursor(after,start)
    cursor.entry()
    assert cursor.take(18)==b"\0\0"+u32(0)*4
    setup=entry(NAME,story["event_setup"])+u32(1)+bytes.fromhex("09e8fe41e1464e8d284bec7c9373e8f5")
    offset=after.index(entry("Default",DEFAULT_EVENTS))
    mapped=after.index(entry(ROAD_NAME,story["winter_road"]["scenario"]))
    legacy=after[start:mapped]
    faultline_entry=entry(FAULTLINE_NAME,story["faultline"]["scenario"])
    modern=after.index(faultline_entry)
    clone=after[mapped:modern]
    faultline=after[modern:offset-4]
    for row in (legacy,clone,faultline):
        assert NATIVE_INTRO not in row and bytes.fromhex(DEFAULT_EVENTS) not in row
        assert row.count(bytes.fromhex(story["event_setup"]))==1
    assert clone.startswith(entry(ROAD_NAME,story["winter_road"]["scenario"])+b"\0\0")
    assert faultline.startswith(faultline_entry+b"\1\0")
    assert string("@Mods/NewIndustry/Faultline/Menu/DisplayName") in faultline
    for native in (NATIVE_CITY,NATIVE_WORLD):
        assert bytes.fromhex(native) in legacy and bytes.fromhex(native) not in clone
    forecast=story["winter_road"]["forecast"]
    assert clone.count(bytes.fromhex(forecast))==1
    old=before.index(entry("Default",DEFAULT_EVENTS))
    assert after[offset-4:offset]==u32(9) and before[old-4:old]==u32(8)
    assert faultline.count(bytes.fromhex(story["faultline"]["forecast"]))==1
    record=(forecast_record(story["lifeline"]["forecast"])+forecast_record(forecast,"Winter Road")+
            forecast_record(story["faultline"]["forecast"],"Faultline"))
    for prefix,path,old_next,count in (
        ("NI Switchback Basin",CITY,entry("Default",NATIVE_CITY),30),
        ("NI Switchback Frostland",WORLD,entry("Refugees","e56253859755dc8b364092403628c7ef"),19),
    ):
        cursor=Cursor(after,after.index(b"\1"+string(prefix)))
        at=cursor.position
        _,uid=cursor.entry()
        assert bytes.fromhex(uid) in clone and bytes.fromhex(uid) in faultline
        assert cursor.string()==path and cursor.count(8)==1
        if path==CITY:
            assert cursor.string()=="Var1"
            cursor.guid()
            assert cursor.f32()==1 and cursor.take(3)==bytes(3)
        else:
            assert cursor.string()=="Random A"
            cursor.guid()
            assert cursor.count()==0 and cursor.count()==0
            assert cursor.string() and cursor.string() is None
        assert cursor.string() and cursor.string()
        if path==WORLD:assert cursor.take(1)==b"\0"
        assert after[cursor.position:].startswith(old_next)
        assert after[at-4:at]==u32(count+1)
        after=after[:at-4]+u32(count)+after[cursor.position:]
    assert after[offset:].replace(setup,b"",1).replace(u32(69)+record+WEATHER_DONOR,u32(66)+WEATHER_DONOR,1)==before[old:]


def audit(records,meta,resource_ids):
    events=[e for e in records["gameevents"] if not e["name"].startswith(("NI Lifeline ","NI Winter Road "))]
    dialogs={item["guid"]:item for item in records["dilemmas"]}
    quests={item["guid"]:item for item in records["quests"]}
    story=meta["story"];identity=story["scenario"];prefix="NI/LastSignal/"
    names={item["name"]:uid for uid,item in dialogs.items()}
    stock={guid:4000 for guid in resource_ids.values()}
    modes={i["value"] for i in meta["modes"]}
    for selected,scenario in [(set(),None),(set(),DEFAULT),
                              *[({meta["enabled"],mode},None) for mode in modes]]:
        world=World(selected,events,dialogs,quests,stock,scenario)
        world.start();world.run(3,False)
        assert not any(key.startswith(prefix) for key in world.variables)
    for routes in product((1,2),repeat=3):
        world=World(set(),events,dialogs,quests,stock,identity)
        world.start()
        for phase,route in enumerate((1,)+routes,1):
            world.step()
            choice=names["NI Last Signal Act"+str(phase)]
            assert world.click(choice,route-1)
            row=next(row for row in story["acts"] if (row["phase"],row["route"])==(phase,route))
            quest=quests[row["guid"]]
            assert quest["deadline"]==row["deadline"] and set(world.active)=={row["guid"]}
            world.execute(dialogs[choice]["choices"][route-1]["effects"])
            assert not any(key.startswith("NI/Frontiers/") for key in world.variables)
            if row["payment"]:
                have=dict(world.stock)
                world.generator=False;world.run(0.5,False)
                assert world.stock==have and world.variables[prefix+"checks"]==0
                world.generator=True;coal=resource_ids["Coal"];world.stock[coal]=120
                world.run(0.5,False);assert world.stock[coal]==120 and world.variables[prefix+"checks"]==0
                world.stock=have
            for goal in quest["objectives"]:
                if goal["kind"]=="build":world.buildings[goal["target"][0]]=goal["quantity"]
                elif goal["kind"]=="research":world.researched.add(goal["target"])
            shifts=next((g["quantity"] for g in quest["objectives"] if g["kind"]=="checks"),0)
            world.update_quests()
            prev=dict(world.stock)
            for _ in range(shifts*2):
                world.step()
            for resource,amount in row["payment"].items():
                assert prev[resource_ids[resource]]-world.stock[resource_ids[resource]]==shifts*amount
            assert not world.modifiers
            assert world.variables[prefix+"act"] in ((5,99) if phase==4 else (phase+1,))
            world=world.checkpoint()
        world.step()
        assert world.variables[prefix+"act"]==99
        assert world.variables[prefix+"successes"]==4
        assert names[f"NI Last Signal Ending/4/{routes[-1]}"] in world.open
    abandoned=World(set(),events,dialogs,quests,stock,identity)
    abandoned.start();abandoned.run(45,False)
    assert abandoned.variables[prefix+"act"]==99 and abandoned.variables.get(prefix+"successes",0)==0
    assert names["NI Last Signal Ending/0/1"] in abandoned.open
    assert not abandoned.active and not abandoned.modifiers
    return dict(branch_paths=8,all_ignored_reaches_ending=True,no_free_shifts=True,unique_scenario=True)
