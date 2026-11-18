"""Exercise the decoded Winter Road records, not the authoring catalogue."""
from tools.scenario_model import World
from tools.housing_schema import BEACON
from tools.story_schema import DEFAULT

PREFIX="NI/WinterRoad/"


def audit(records,metadata,ids):
    story=metadata["story"];road=story["winter_road"]
    events=records["gameevents"]
    dialogs={d["guid"]:d for d in records["dilemmas"]}
    names={d["name"]:d["guid"] for d in records["dilemmas"]}
    quests={q["guid"]:q for q in records["quests"]}
    missions={(q["chapter"],q["plan"]):q for q in road["missions"]}
    projects={q["chapter"]:q for q in road["projects"]}
    count=road["chapters"]
    assert count==8 and len(missions)==17 and len(projects)==6
    stock={value:10000 for value in ids.values()}
    def new(scenario=road["scenario"],selected=()):
        return World(selected,events,dialogs,quests,stock,scenario)
    def get(w,key,default=0):return w.variables.get(PREFIX+key,default)
    def name(key):return names["NI Winter Road "+key]
    def amount_of_people(w):return sum(w.arrivals.values())

    def complete(w,row):
        key=row["quest"]
        for goal in quests[key]["objectives"]:
            quantity=goal["quantity"]
            kind=goal["kind"]
            if kind=="build":
                target=goal["target"][0]
                w.buildings[target]=quantity
                w.activate_building(target)
            if kind=="operate":w.operating[goal["target"][0]]=quantity
            if kind=="research":w.researched.add(goal["target"])
            if kind=="warm":w.warm_homes=quantity
            if kind=="produce":
                assert not w.goal_met(key,goal),"Stored production counted for a new job"
                target=goal["target"][0]
                w.produced[target]=w.produced.get(target,0)+quantity
            if goal.get("label")=="Scout":
                assert w.world_map
                assert w.progress[key].get("Scout",0)==0
                w.return_scouts()
                w.return_scouts()
                assert w.progress[key].get("Scout")==1
        w.update_quests()

    def start_chapter(w,chapter,plan):
        key=name(f"briefing/{chapter}")
        w.run(0.5,False)
        assert key in w.open,(chapter,"No prompt")
        assert w.click(key,plan-1)
        row=missions[chapter,plan]
        assert row["quest"] in w.active and quests[row["quest"]]["deadline"]==row["deadline"]
        assert [g["kind"] for g in row["goals"]]==[g["kind"] for g in quests[row["quest"]]["objectives"]]
        previous=w.checkpoint()
        w.execute(dialogs[key]["choices"][plan-1]["effects"])
        assert previous.__dict__==w.__dict__,"Stale plan replayed"
        return row

    def close_chapter(w,chapter,plan,won=True):
        assert get(w,"chapter")==chapter+1
        assert w.click(name(f"chapter/{chapter}/{plan}/"+("report" if won else "missed")))
        assert get(w,"reading")==0

    branches=[
        (1,)*8,(2,)*8,(1,2,1,1,2,3,2,1),(2,1,2,2,1,3,1,2),
        (2,1,1,2,1,1,2,2),(1,2,2,1,2,2,1,1),
    ]
    side_runs=set()
    for run,plans in enumerate(branches):
        w=new();w.start();w.run(0.25,False)
        assert get(w,"chapter")==1 and not w.active and not w.arrivals
        for chapter,plan in enumerate(plans,1):
            row=start_chapter(w,chapter,plan)
            if chapter==1:assert amount_of_people(w)==12
            if chapter in projects:
                project=projects[chapter];key=name("project/"+project["key"])
                w.run(0.25,False)
                assert key in w.open
                assert w.click(key,0)
                side=project["quest"]
                assert set(w.active)=={side,row["quest"]},"Side project replaced the main objective"
                complete(w,project)
                w.run(0.5,False)
                assert side not in w.active
                assert w.click(name("project/"+project["key"]+"/complete"))
                side_runs.add(project["key"])
            if chapter==8:
                assert road["bonuses"]["braced"] in w.modifiers and road["bonuses"]["exposed"] not in w.modifiers
                w.generator=False;w.run(0.25,False)
                assert get(w,"main/streak")==0
            previous=dict(w.stock)
            previous_people=amount_of_people(w)
            complete(w,row)
            w.generator=True
            if row["watch"]:
                w.run(0.75,False)
                assert get(w,"main/streak")==3
                w.generator=False;w.run(0.25,False)
                assert get(w,"main/streak")==0
                w.generator=True;w.run(1.25,False)
                assert get(w,"chapter")==8 and get(w,"main/streak")==5
                w.run(0.25,False)
                assert not {road["bonuses"]["exposed"],road["bonuses"]["braced"]}&w.modifiers
            else:
                w.run(0.5,False)
            assert amount_of_people(w)-previous_people==sum(row["arrival"].values())
            for resource,uid in ids.items():
                assert w.stock[uid]==previous[uid]+row["cargo"].get(resource,0)-row["cost"].get(resource,0),(chapter,resource)
            close_chapter(w,chapter,plan)
            w=w.checkpoint();w.start()
        w.run(0.5,False)
        ending=road["finale"]
        assert ending in w.open
        end=run%3
        assert w.click(ending,end)
        before=w.checkpoint()
        w.execute(dialogs[ending]["choices"][end]["effects"])
        assert before.__dict__==w.__dict__
        if end==0:
            w.run(8.25,False)
            assert all(get(w,"cargo/"+str(index))==1 for index in (1,2,3))
            assert amount_of_people(w)==amount_of_people(before)+6
        if end==1:assert road["bonuses"]["home"] in w.modifiers
        assert get(w,"chapter")==99
    assert len(side_runs)==6

    missed=new();missed.start()
    for chapter in range(1,count+1):
        missed.generator=False
        row=start_chapter(missed,chapter,1)
        if chapter in projects:
            project=projects[chapter]
            missed.run(0.25,False)
            assert missed.click(name("project/"+project["key"]),0)
        if chapter==8:assert road["bonuses"]["exposed"] in missed.modifiers
        # All promises expire without any irreversible charge.
        balance=dict(missed.stock)
        missed.run(6.25,False)
        assert not missed.active and missed.stock==balance
        close_chapter(missed,chapter,1,False)
    missed.run(0.5,False)
    assert not missed.click(road["finale"]) and missed.click(road["finale"],2)
    assert get(missed,"chapter")==99
    assert not {road["bonuses"]["embargo"],road["bonuses"]["exposed"],road["bonuses"]["braced"]}&missed.modifiers
    for stage,plan in ((6,3),(2,1)):
        probe=new()
        probe.variables.update({PREFIX+"chapter":stage,PREFIX+"offered":stage-2})
        if stage==6:
            probe.variables[PREFIX+"mapped"]=1
            probe.run(0.5,False)
            assert not probe.click(name("briefing/6"),plan-1)
        else:
            row=start_chapter(probe,stage,plan)
            complete(probe,row)
            probe.stock[ids["Food Rations"]]=0
            probe.run(0.5,False)
            assert get(probe,"chapter")==stage and row["quest"] in probe.active
    for legacy in ("NI/Lifeline/chapter","NI/LastSignal/act"):
        old=new(story["scenario"]);old.variables[legacy]=1;old.start();old.run(2,False)
        assert get(old,"chapter")==0
    for scenario in (DEFAULT,None):
        w=new(scenario);w.start();w.run(4,False)
        w.activate_building(BEACON)
        assert not any(key.startswith(PREFIX) for key in w.variables)
        assert not w.world_map
    chart = new()
    chart.start()
    chart.run(1,False)
    assert not chart.world_map and not chart.revealed_sites
    chart.buildings[BEACON] = 1
    chart.run(0.5,False)
    assert chart.world_map
    assert chart.placed_sites == {s["point"]:s["template"] for s in road["map"]["sites"]}
    assert chart.revealed_sites == {("site",s["template"]) for s in road["map"]["sites"]}
    saved = chart.checkpoint()
    saved.start();saved.run(1,False)
    assert saved.placed_sites == chart.placed_sites
    assert saved.revealed_sites == chart.revealed_sites
    existing = new(story["scenario"])
    existing.variables.update({PREFIX+"chapter":4, PREFIX+"map_open":1})
    existing.buildings[BEACON] = 1
    existing.run(0.5,False)
    assert existing.world_map and existing.revealed_sites
    aftermath={(row["chapter"],row["plan"]):row for row in road["aftermath"]}
    assert len(aftermath)==6
    for treaty in (1,2,3):
        # Reproduce a previously negotiated treaty, including testgame's
        # already-delivered first shipment. The new work begins on load.
        resumed=new()
        resumed.time=16.5
        resumed.variables={PREFIX+"chapter":99,PREFIX+"ending":treaty,PREFIX+"offered":8}
        if treaty==1:
            resumed.variables[PREFIX+"cargo/1"]=1
        resumed.start()
        for phase in (1,2,3):
            resumed.run(0.5,False)
            decision=name(f"aftermath/briefing/{phase}")
            assert decision in resumed.open and not resumed.active
            plan=1 if treaty!=2 else 2
            row=aftermath[phase,plan]
            if treaty==3:
                resumed.generator=False
                resumed.run(2,False)
                assert get(resumed,"aftermath/plan")==1
                balance=dict(resumed.stock)
                resumed.run(row["deadline"]+0.25,False)
                assert resumed.stock==balance
            else:
                assert resumed.click(decision,plan-1)
                complete(resumed,row)
                assert row["quest"] in resumed.active
                resumed=resumed.checkpoint()
                resumed.start()
                resumed.run(row["watch"]*0.25+0.25,False)
                assert get(resumed,"aftermath/kept")==phase
            expected_phase = (phase+1,) if phase<3 else (4,99)
            assert not resumed.active and get(resumed,"aftermath") in expected_phase, (treaty,phase,get(resumed,"aftermath"))
        resumed.run(0.5,False)
        assert name(f"aftermath/end/{0 if treaty==3 else 3}") in resumed.open
        assert get(resumed,"aftermath")==99 and get(resumed,"ending")==treaty
        if treaty==1:
            assert get(resumed,"cargo/1")==1, "A delivered shipment was replayed"
    return dict(full_paths=len(branches),mission_variants=len(missions),side_projects=len(side_runs),
        missed_chapters=count,ending_paths=3,heating_watch_resets=True,legacy_isolation=True,
        revealed_scout_sites=len(chart.revealed_sites),legacy_beacon_repaired=True,aftermath_plans=len(aftermath),
        legacy_treaties_resumed=3)
