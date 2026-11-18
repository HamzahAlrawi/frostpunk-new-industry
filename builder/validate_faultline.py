"""Drive decoded Faultline events through each refit and ending."""
from math import isclose
from tools.scenario_model import World
from tools.housing_schema import BEACON
from tools.story_schema import DEFAULT


PREFIX = "NI/Faultline/"
HOUR = 1/24


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
    assert len(missions)==11

    def world(scenario=None):
        return World(None,events,dialogs,quests,{guid:20000 for guid in resource_ids.values()},
                     campaign["scenario"] if scenario is None else scenario)

    def state(w, name):
        return w.variables.get(PREFIX+name,0)

    def tick(w, hours):
        for _ in range(hours):
            w.step(HOUR)

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
    for route in ((1,1,1,1,2), (2,2,2,2,3), (1,2,1,2,1)):
        w=world()
        w.start()
        for phase, plan in enumerate(route,1):
            w.stress=0.18
            tick(w,6)
            briefing=names[f"briefing/{phase}"]
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
                w.stress=0.145
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
            assert state(w,"phase")==phase+1 and profile not in w.modifiers
            assert row["quest"] in w.completed
            played.add((phase,plan))
        tick(w,12)
        assert state(w,"ending")==2 and state(w,"kept")==5
        assert names["end/1/5"] in w.open
    assert played==set(missions)

    # A city that misses every deadline can still finish, including when the
    # player leaves the briefing alone. Unsettled plans cannot replay rewards.
    failed=world()
    failed.start()
    failed.generator=False
    failed.run(40,False)
    assert state(failed,"ending")==1 and state(failed,"kept")==0
    assert not failed.active and not failed.modifiers
    assert names["end/0/0"] in failed.open
    accord=world()
    accord.start()
    accord.variables.update({PREFIX+"phase":6,PREFIX+"kept":4,PREFIX+"final":1})
    accord.run(0.5,False)
    assert state(accord,"ending")==3 and names["accord/4"] in accord.open
    assert accord.modifiers=={effects["faultline/accord"]}
    for scenario in (DEFAULT,story["scenario"],story["winter_road"]["scenario"]):
        other=world(scenario)
        other.start()
        other.buildings[BEACON]=1
        other.run(2,False)
        assert not any(key.startswith(PREFIX) for key in other.variables)
        assert not any(uid in other.open for uid in names.values())
    return dict(plans=len(played),endings=3,trip_recovery=True,stress_is_spent=True,deadlines_continue=True,
                route_unlocks_verified=True,old_saves_isolated=True)
