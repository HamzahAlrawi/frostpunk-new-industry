"""Replay the serialized evacuation state machine and verify ledgers."""
from itertools import product

from tools.convoy_schema import APPEARANCE, ROLES
from tools.scenario_model import World
from tools.story_schema import DEFAULT

PREFIX="NI/Lifeline/"


def audit(records,meta,ids):
    story=meta["story"];content=story["lifeline"]
    events=records["gameevents"];dialogs={d["guid"]:d for d in records["dilemmas"]}
    quests={q["guid"]:q for q in records["quests"]};names={d["name"]:guid for guid,d in dialogs.items()}
    missions={(row["chapter"],row["plan"]):row for row in content["missions"]}
    stock={gid:600 for gid in ids.values()}

    def test_world(scenario=story["scenario"]):
        return World(set(),events,dialogs,quests,stock,scenario)

    def total(world):
        return sum(world.arrivals.values())

    def briefing(world,chapter):
        world.run(1,False)
        guid=names[f"NI Lifeline Briefing/{chapter}"]
        assert guid in world.open
        return guid

    def fulfill(world,row):
        for goal in quests[row["quest"]]["objectives"]:
            if goal["kind"]=="build":
                world.buildings[goal["target"][0]]=goal["quantity"]
            if goal["kind"]=="operate":
                world.operating[goal["target"][0]]=goal["quantity"]
        world.update_quests()

    def launch(world,chapter,plan):
        guid=briefing(world,chapter)
        row=missions[chapter,plan]
        assert world.click(guid,plan-1)
        assert list(world.active)==[row["quest"]]
        assert quests[row["quest"]]["deadline"]==row["deadline"]
        before=world.checkpoint()
        world.execute(dialogs[guid]["choices"][plan-1]["effects"])
        assert world.__dict__==before.__dict__,"Repeated choice changed the city"
        return row

    def settle(world,row):
        n=total(world);previous=dict(world.stock);prior_arrivals=dict(world.arrivals)
        world.generator=False
        fulfill(world,row);world.run(0.5,False)
        assert total(world)==n and world.stock==previous and row["quest"] in world.active
        world.generator=True
        prior=world.checkpoint()
        world.run(0.5,False);prior.run(0.5,False)
        assert world.__dict__==prior.__dict__
        assert total(world)-n==sum(row["arrival"].values())
        for role,amount in row["arrival"].items():
            assert world.arrivals[APPEARANCE["well"],ROLES[role]]-prior_arrivals.get(
                (APPEARANCE["well"],ROLES[role]),0)==amount
        assert world.variables[PREFIX+"people"]==total(world)
        assert row["quest"] not in world.active
        for name,guid in ids.items():
            assert world.stock[guid]==previous[guid]-row["price"].get(name,0)+row["salvage"].get(name,0)

    for scenario in (None,DEFAULT):
        w=test_world(scenario);w.start();w.run(10)
        assert not w.arrivals and not any(k.startswith(PREFIX) for k in w.variables)
    paths=0
    for first,second,last in product((1,2),(1,2),(1,2,3)):
        w=test_world();w.start()
        w.run(8,False)
        assert not w.arrivals and not w.active and len(w.open)==1,"Opening waits for the player"
        row=launch(w,1,first)
        assert w.arrivals=={(APPEARANCE["well"],ROLES[role]):n for role,n in content["first_outriders"].items()}
        for name,guid in ids.items():assert w.stock[guid]==stock[guid]+row["entry_supplies"].get(name,0)
        settle(w,row)
        rope=names[f"NI Lifeline Rope/{first}"]
        assert rope in w.open
        if last!=3:
            preview=w.checkpoint()
            preview.variables.update({PREFIX+"chapter":3,PREFIX+"plan":0,PREFIX+"rescues":2})
            assert not preview.click(names["NI Lifeline Briefing/3"],2)
        assert w.click(rope,0 if last==3 else 1)
        row=launch(w,2,second)
        if second==1:
            assert w.arrivals[APPEARANCE["ill"],ROLES["workers"]]==6
        settle(w,row)
        row=launch(w,3,last)
        settle(w,row)
        final_count=total(w);w.run(18,False)
        assert w.variables[PREFIX+"chapter"]==4 and total(w)==final_count
        assert names[f"NI Lifeline Report/3/{last}"] in w.open
        paths+=1
    missed=test_world();missed.start()
    for chapter in range(1,4):
        row=launch(missed,chapter,1);start=total(missed)
        missed.generator=False;missed.run(row["deadline"]+0.5,False)
        assert total(missed)-start==sum(row["fallback"].values())
        assert names[f"NI Lifeline Missed/{chapter}/1"] in missed.open
        assert not missed.active
    old=test_world();old.variables["NI/LastSignal/act"]=1
    old.start();old.run(1,False)
    assert not old.arrivals and names["NI Last Signal Act1"] in old.open
    assert not any(k.startswith(PREFIX) for k in old.variables)
    return dict(paths=paths,missed_rescues=3,legacy_save_isolation=True,mobilizes_12_on_first_choice=True)
