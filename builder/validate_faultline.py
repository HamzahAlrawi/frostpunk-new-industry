"""Drive decoded Faultline events through each refit and ending."""
from math import isclose
from tools.native_binary import Cursor
from tools.scenario_model import World
from tools.housing_schema import BEACON
from tools.story_schema import DEFAULT


PREFIX = "NI/Faultline/"
HOUR = 1/24


def audit_films(native, revised, city, campaign):
    tracks = ("Fade", "StoreCameraLocation", "RestoreCameraLocation", "SetCameraPosition",
              "EaseCameraPosition", "SetCameraLookAt", "SetVisibleGameHUD", "PlaySound", "EmitSignal")
    sizes = dict(zip(tracks,(12,0,2,43,38,21,2,34,16)))
    native_count=Cursor(native).u32()
    reader=Cursor(revised)
    films={f["shot"]:f["signal"] for f in campaign["films"].values()}
    assert reader.u32()==native_count+len(films)
    for shot in films:
        assert reader.u8()==1 and reader.string()=="NI_Faultline_"+shot
        actions={}
        for _ in range(reader.count(16)):
            assert reader.u32()==1
            for _ in range(reader.count(8)):
                name=reader.string().removeprefix("SequenceAction")
                duration,start,extent=(reader.f32() for _ in range(3))
                assert duration>=0 and 0<=start<=extent<=10
                if name not in ("StoreCameraLocation","EmitSignal","SetCameraPosition","SetCameraLookAt"):
                    assert isclose(start+duration,extent,abs_tol=1e-5)
                assert reader.take(5)==bytes(5)
                actions.setdefault(name,[]).append((start,extent,reader.take(sizes[name])))
        assert set(actions)==set(tracks)
        assert reader.u8()==1 and reader.string()=="GENRAL"
        assert reader.u32()==0 and reader.boolean() and not reader.boolean()
        assert (reader.f32(),reader.f32())==(5,45000)
        assert [row[2][0] for row in actions["Fade"]]==[0,1,0,1]
        assert [row[2] for row in actions["SetVisibleGameHUD"]]==[b"\1\0",b"\0\1"]
        target=actions["SetCameraPosition"][0][2][-16:]
        assert city.count(target)==2 and actions["SetCameraLookAt"][0][2][1:17]==target
        assert actions["EaseCameraPosition"][0][2][-16:]==target
        assert actions["EaseCameraPosition"][0][2][4:16]!=actions["SetCameraPosition"][0][2][4:16]
        callback=actions["EmitSignal"][0]
        assert actions["StoreCameraLocation"][0][0]<actions["SetCameraPosition"][0][0]
        assert actions["RestoreCameraLocation"][0][1]<callback[0] and actions["Fade"][-1][1]<callback[0]
        assert callback[2].hex()==films[shot]
    assert revised[reader.position:]==native[4:],'A native sequence changed'
    return len(films)


def audit(decoded, metadata, resource_ids):
    story = metadata["story"]
    campaign = story["faultline"]
    events = decoded["gameevents"]
    dialogs = {d["guid"]:d for d in decoded["dilemmas"]}
    names = {d["name"].removeprefix("NI Faultline "): d["guid"] for d in dialogs.values()
             if d["name"].startswith("NI Faultline ")}
    quests = {q["guid"]:q for q in decoded["quests"]}
    missions = {(q["phase"],q["plan"]):q for q in campaign["missions"]}
    effects = campaign["modifiers"]
    trip = effects["faultline/trip"]
    leak = effects["faultline/leak"]
    coal = resource_ids["Coal"]
    assert len(missions)==15

    def world(scenario=None):
        return World(None,events,dialogs,quests,{guid:20000 for guid in resource_ids.values()},
                     campaign["scenario"] if scenario is None else scenario)

    def state(w, name):
        return w.variables.get(PREFIX+name,0)

    def tick(w, hours):
        for _ in range(hours):
            w.step(HOUR)

    def shot_callback(w, key):
        filmed=campaign["films"][key]
        assert w.sequences.count("NI_Faultline_"+filmed["shot"])==1
        w.sequence_signal(filmed["signal"])
        w.sequence_signal(filmed["signal"])

    def fulfill_city(w, row):
        for goal in quests[row["quest"]]["objectives"]:
            kind, count = goal["kind"], goal["quantity"]
            if kind == "build":
                w.buildings[goal["target"][0]] = count
            elif kind == "operate":
                w.operating[goal["target"][0]] = count
            elif kind == "research":
                w.researched.add(goal["target"])
            elif kind == "warm":
                w.warm_homes = count
            elif kind == "produce":
                target = goal["target"][0]
                w.produced[target] = w.produced.get(target,0)+count
            elif goal["label"] == "Scout":
                tick(w,6)
                assert w.world_map and len(w.revealed_sites)==3
                w.return_scouts()
                w.return_scouts()
                assert w.progress[row["quest"]]["Scout"]==1

    played=set()
    for route in ((1,1,1,1,2,1,1), (2,2,2,2,3,2,2), (1,2,1,2,1,1,2)):
        w=world()
        w.start()
        for phase, plan in enumerate(route,1):
            w.stress=0.18
            tick(w,6)
            key=f"briefing/{phase}"
            briefing=names[key]
            if key in campaign["films"]:
                assert briefing not in w.open
                if phase==6:
                    # Reload partway through a presentation; the timer still
                    # opens the briefing if the native callback is lost.
                    w=w.checkpoint()
                    w.start()
                    tick(w,10)
                shot_callback(w,key)
                assert w.open.count(briefing)==1
            assert briefing in w.open, (phase, state(w,"phase"))
            if phase==5:
                selected=dialogs[briefing]["choices"]
                assert w.all(selected[1]["conditions"])==(route[1]==1)
                assert w.all(selected[2]["conditions"])==(route[1:3]==(2,2))
            assert w.click(briefing, plan-1)
            row=missions[phase,plan]
            profile=effects["faultline/"+row["profile"]]
            assert profile in w.modifiers and row["quest"] in w.active
            # Structural readiness alone cannot supply an opening pulse.
            if phase==1:
                w.stress=0.35
                w.step(HOUR)
                assert state(w,"stroke")==0
            # Pre-existing stock and completed city goals still cannot skip
            # the pressure sequence, and a shut-off Generator cannot pulse.
            w.generator=False
            fulfill_city(w,row)
            pledge=row["pledge"]
            if pledge:
                short=resource_ids[next(iter(pledge))]
                stored=w.stock[short]
                w.stock[short]=0
            w.step(HOUR)
            assert state(w,"stroke")==0 and row["quest"] in w.active
            w.generator=True
            if phase in (1,5):
                limit=campaign["welded_trip"] if state(w,"welded") else campaign["trip"]
                w.stress=(limit+1)/100
                w.step(HOUR)
                assert trip in w.modifiers and state(w,"tripped")==1 and state(w,"stroke")==0
                w.stress=0.19
                w.step(HOUR)
                assert trip in w.modifiers
                w=w.checkpoint()
                w.start()
                w.stress=(campaign["reset"]-0.4)/100
                w.step(HOUR)
                assert trip not in w.modifiers and state(w,"tripped")==0
            for index,stroke in enumerate(row["strokes"],1):
                # Outside the current step's band, time alone has no effect.
                w.stress=(stroke["low"]-3)/100 if stroke["draw"] else (stroke["high"]+8)/100
                w.step(HOUR)
                assert state(w,"stroke")==index-1
                w.stress=(stroke["low"]+stroke["high"])/200
                expected=w.stress-stroke["draw"]/100
                w.step(HOUR)
                assert state(w,"stroke")==index and isclose(w.stress,expected,abs_tol=1e-6)
            if watch:=row["watch"]:
                w.stress=(watch["low"]+watch["high"])/200
                supply=w.stock[coal]
                tick(w,watch["hours"]-1)
                assert state(w,"hours")==watch["hours"]-1 and state(w,"leg")==0
                w.stock[coal]=watch["reserve"]+watch["coal"]-1
                tick(w,1)
                assert state(w,"hours")==0 and state(w,"leg")==0
                w.stock[coal]=supply
                tick(w,watch["hours"])
                assert state(w,"leg")==1 and state(w,"leak")==1 and leak in w.modifiers
                assert w.stock[coal]==supply-watch["coal"]
                outage=names[f"act/{phase}/{plan}/leak"]
                assert outage in w.open
                if route[0]==2:
                    tick(w,18)
                    assert state(w,"leak")==2 and not w.click(outage,1)
                else:
                    material=resource_ids["Steel"]
                    before=w.stock[material]
                    assert w.click(outage,0) and not w.click(outage,0)
                    assert w.stock[material]==before-campaign["leak_repair"]["Steel"]
                    supply-=campaign["leak_repair"]["Coal"]
                tick(w,2*(watch["hours"]+1)+13)
                assert state(w,"leg")==campaign["watch_legs"] and leak not in w.modifiers
                assert w.stock[coal]==supply-campaign["watch_legs"]*watch["coal"]
            if pledge:
                assert row["quest"] in w.active, "Charter completed without supplies"
                w.stock[short]=stored
                before={name:w.stock[resource_ids[name]] for name in pledge}
                tick(w,2)
                assert all(w.stock[resource_ids[name]]==before[name]-quantity for name,quantity in pledge.items())
            assert state(w,"phase")==phase+1 and profile not in w.modifiers
            assert row["quest"] in w.completed
            played.add((phase,plan))
        tick(w,6)
        shot_callback(w,"dawn")
        tick(w,12)
        assert state(w,"ending")==2 and state(w,"kept")==7
        assert w.open.count(names["end/1/7"])==1
    assert played==set(missions)

    # A city that misses every deadline can still finish, including when the
    # player leaves the briefing alone. Unsettled plans cannot replay rewards.
    failed=world()
    failed.start()
    failed.generator=False
    failed.run(60,False)
    assert state(failed,"ending")==1 and state(failed,"kept")==0
    assert not failed.active and not failed.modifiers
    assert names["end/0/0"] in failed.open
    accord=world()
    accord.start()
    accord.variables.update({PREFIX+"phase":8,PREFIX+"offered":7,PREFIX+"kept":5,PREFIX+"final":1,PREFIX+"charter":1})
    accord.run(1,False)
    assert state(accord,"ending")==3 and names["accord/5"] in accord.open
    assert accord.modifiers=={effects["faultline/accord"]}
    settled=world()
    settled.variables.update({PREFIX+"phase":6,PREFIX+"offered":5,PREFIX+"ending":3})
    settled.start()
    settled.run(5,False)
    assert not settled.active and not settled.open and not settled.sequences
    for scenario in (DEFAULT,story["scenario"],story["winter_road"]["scenario"]):
        other=world(scenario)
        other.start()
        other.buildings[BEACON]=1
        other.run(2,False)
        assert not any(key.startswith(PREFIX) for key in other.variables)
        assert not any(uid in other.open for uid in names.values())
    return dict(plans=len(played),endings=3,trip_recovery=True,stress_is_spent=True,deadlines_continue=True,
                route_unlocks_verified=True,old_saves_isolated=True,watch_resets=True,leak_repairs=True,
                pledge_paid_once=True,cinematic_signal_and_fallback=True)
