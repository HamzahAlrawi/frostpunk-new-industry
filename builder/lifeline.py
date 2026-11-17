"""Lifeline campaign: build a reception city and run two competing rescues."""
from city_mastery import building_ids
from tools.convoy_schema import arrive, validate_arrivals
from tools.mission_schema import MissionWriter, completed_event
from tools.native_scenario import (affordable, change_resource, compare, delayed, dilemma, equals,
    event, guarded, integer, predefined, progress_quest, set_variable, start_quest, typed, variable)

PREFIX = "NI/Lifeline/"
OLD = "NI/LastSignal/"


def facility(text, *names, count=1, operate=False):
    return dict(kind="operate" if operate else "build", text=text, names=names, quantity=count)


HOMES = ("Tent", "Bunkhouse", "House")
WARD = ("Medical Post", "Ambulatorium", "HospitalOfMercy")
STEEL = ("Iron Ore Mine", "SteamIronOreMine", "AdvancedOreMine")


def row(title, label, description, goals, price, convoy, salvage):
    return dict(title=title,label=label,description=description,goals=goals,price=price,convoy=convoy,salvage=salvage)


CHAPTERS = (
    dict(title="The First Sled", days=3, plot=(
        "At dawn a sled comes skidding into the crater. Edith Vale unpicks a list sewn into the runner’s coat. "
        "Mara’s school group and Ivo’s pump crew are on opposite ledges. Both have been told to follow the same guide rope. "
        "We can lower a sled to one first. Twelve outriders are already at the gate. Put them to work."),
        plans=(
            row("A ward for the school", "Bring Mara down first", "The outriders bring 40 wood and 20 coal. "
                "Build a Medical Post. Set aside 20 rations for the crossing.",
                [facility("Build a Medical Post","Medical Post")], {"Food Rations":20},
                {"workers":10,"children":10}, {"Raw Food":35}),
            row("A landing for the pump crew", "Bring Ivo down first", "The outriders bring 25 steel and a steam core. "
                "Build a Gathering Post. Set aside 85 coal for the winch.",
                [facility("Build a Gathering Post","GatheringPost")], {"Coal":85},
                {"workers":10,"engineers":8}, {"Coal":140}),
        ), failure="Four people made it down alone. Behind them, the sled trail ends at a torn rope."),
    dict(title="The Second Sled", days=5, plot=(
        "The next signal is five short knocks. A sled hit the switchback wall: the injured are on the lower track "
        "and the spare winch is stranded higher up. Mara says to bring the wounded in now. Ivo shows you the split "
        "pulley. If it goes, there may be no third trip. What does the city build first?"),
        plans=(
            row("A ward under steam", "Bring the injured inside", "Six gravely ill workers arrive when you decide. "
                "Put two medical buildings into operation and set aside 45 rations and 80 coal.",
                [facility("Operate two medical buildings",*WARD,count=2,operate=True)],
                {"Food Rations":45,"Coal":80},{"workers":12,"engineers":4,"children":8},{"Food Rations":45}),
            row("The broken winch", "Rebuild the winch", "Six engineers arrive now. Build a Steelworks and a Steam Hub, "
                "then set aside 70 steel and 100 coal for the recovery.",
                [facility("Build a Steelworks",*STEEL),facility("Build a Steam Hub","Steam Hub")],
                {"Steel":70,"Coal":100},{"workers":12,"engineers":6},{"Steam Cores":2}),
        ), failure="The spare sled went down empty. Five people reached the south gate on foot. Their supplies stayed on the ridge."),
    dict(title="The False Clearance", days=6, plot=(
        "Edith plays back the clearance tape. It was her hand that erased the children from the second manifest: "
        "the old relay would only clear a crew that could work. She thought there would be time to send the rest "
        "afterward. There wasn’t. Tonight the ledge is giving way. You can read out every name and open the road, "
        "keep the crossing narrow enough for the winch to carry the heaviest sleds, or use both lines if we have the crews."),
        plans=(
            row("Crossing Night: The open road", "Read every name", "Make room for families. Complete ten homes and "
                "operate two medical buildings. The rescue takes 100 rations and 250 coal.",
                [facility("Build ten homes",*HOMES,count=10),facility("Operate two medical buildings",*WARD,count=2,operate=True)],
                {"Food Rations":100,"Coal":250},{"workers":18,"engineers":6,"children":22},{"Food Rations":80}),
            row("Crossing Night: The rope ferry", "Keep the ferry running", "Bring the repair crews and the relay itself. "
                "Build two Steam Hubs and operate a Steelworks. Spend 100 steel and 250 coal at the crossing.",
                [facility("Build two Steam Hubs","Steam Hub",count=2),facility("Operate a Steelworks",*STEEL,operate=True)],
                {"Steel":100,"Coal":250},{"workers":18,"engineers":16,"children":2},{"Steam Cores":3,"Steel":80}),
            row("Crossing Night: Both lines", "Open both crossings", "Requires the marked rope and two successful rescues. "
                "Build twelve homes and two Steam Hubs; operate three medical buildings. The twin rescue takes "
                "140 rations, 110 steel and 320 coal.",
                [facility("Build twelve homes",*HOMES,count=12),facility("Build two Steam Hubs","Steam Hub",count=2),
                 facility("Operate three medical buildings",*WARD,count=3,operate=True)],
                {"Food Rations":140,"Steel":110,"Coal":320},{"workers":24,"engineers":16,"children":24},
                {"Steam Cores":3,"Food Rations":100}),
        ), failure="Eight people made it through on the last rope. The clearing on the far side went dark before the next bell."),
)

EPILOGUES = (
    ("The roll call", "Mara props the school slate against the Generator. She reads out every name, including the ones "
     "with no answer. The children who made it take turns chalking in the names of people they never knew."),
    ("The bell at shift change", "Ivo gets the relay ticking before dawn. He uses the first call to ask for the missing "
     "sled, not to report how much gear survived. The pump crew hang its bell over the works. It rings at every shift change."),
    ("Two lines of light", "The crews on both ropes meet at the bottom of the crater. Someone has hung white flags "
     "over the whole street. Edith puts both manifests on the wall, no names erased."),
)
STRAGGLERS = ({"workers":3,"children":1},{"workers":4,"engineers":1},{"workers":5,"engineers":2,"children":1})
START_SUPPLIES = ({"Wood":40,"Coal":20},{"Steel":25,"Steam Cores":1})


def build(source, buildings, resources, identity, scenario, localize, dt, qt):
    native_events=(source/"configs/frostpunkgameeventsconfig.bin").read_bytes()
    validate_arrivals(native_events)
    effects=(source/"configs/frostpunkeffectsconfig.bin").read_bytes()
    writer=MissionWriter((source/"configs/frostpunkquestsconfig.bin").read_bytes(),qt)
    places={key:value.hex() for key,value in building_ids(buildings).items()}
    resources={key:value.hex() for key,value in resources.items()}
    scoped=typed("FrostpunkCurrentScenarioCheckExpression")+bytes.fromhex(scenario)+b"\0"
    events,dialogs,quests,missions=[],[],[],[]

    def state(key,value):return equals(PREFIX+key,value)
    def put(key,value,op=0):return set_variable(PREFIX+key,value,op)
    def gate(chapter,plan):return [scoped,state("chapter",chapter),state("plan",plan)]
    def timer(key,days,actions):return delayed(identity("timer/"+key),days,actions)
    def condition(price):return [affordable(resources[name],value) for name,value in price.items()]
    def supplies(items,sign=1):return [change_resource(resources[name],sign*quantity) for name,quantity in items.items()]
    def people(groups):return [arrive(quantity,role) for role,quantity in groups.items()]
    def morale(name):
        marker=b"\1"+typed("GOLD [Common] "+name)
        at=effects.index(marker)+len(marker)
        return predefined(effects[at:at+16].hex())
    def poll(key,checks,actions,days=0.25):
        events.append(event("NI Lifeline "+key,identity("event/"+key),identity("trigger/"+key),checks,actions,days))
    def scene(key,title,plot,options,small=False):
        qkey="LastSignal/Lifeline/"+key
        uid=identity("dialog/"+key)
        choices=[dt.choice("NI Lifeline "+key+"/"+str(i),identity("choice/"+key+"/"+str(i)),
            label,detail,visible,[guarded(checks,actions)] if checks else actions,localize,qkey+"/"+str(i))
            for i,(label,detail,visible,checks,actions) in enumerate(options)]
        dialogs.append(dt.build("NI Lifeline "+key,uid,title,plot,choices,localize,qkey,small,subtitle="The Last Signal: Lifeline"))
        return dilemma(uid)
    def note(key,title,text,actions=()):
        return scene(key,title,text,[("Continue","Return to the city.",[],[],list(actions))],True)
    def next_chapter(number):
        return [put("chapter",number+1),put("plan",0)]

    def rope(path,report):
        check=gate(2,0)+[state("rescued/1",1),state("rope_decided",0)]
        return scene("Rope/"+str(path),"The sled reaches the gate", report+
            "\n\nThe returning crew can mark a second crossing with timber stakes. If the next rescue also succeeds, "
            "marking the rope lets you attempt both crossings in the finale.",
            [("Mark the second crossing","Spend 20 wood. Keep the second line open.",condition({"Wood":20}),check+condition({"Wood":20}),
              [put("rope_decided",1),put("rope",1)]+supplies({"Wood":20},-1)),
             ("Keep our timber","The marked twin rescue will be unavailable.",[],check,[put("rope_decided",1)])],True)

    for chapter,act in enumerate(CHAPTERS,1):
        options=[]
        for plan,path in enumerate(act["plans"],1):
            key=f"{chapter}/{plan}"
            qid=identity("quest/"+key)
            check=gate(chapter,plan)
            advance=next_chapter(chapter)
            arrival_groups=path["convoy"]
            total=sum(arrival_groups.values())
            breakdown=", ".join(f"{n} {role}" for role,n in arrival_groups.items())
            arrival_report=f"{total} people entered the city: {breakdown}. They need real beds and meals."
            if chapter==3:
                title,plot=EPILOGUES[plan-1]
                arrival=note("Report/"+key,title,plot+"\n\n"+arrival_report+" The campaign is complete; the city remains playable.")
            else:
                report=arrival_report+(" Mara presses the damp school register into Edith’s hand." if plan==1 else
                     " Ivo’s crew lays the recovered equipment on the square. They wait for a new shift roster.")
                arrival=rope(plan,report) if chapter==1 else note("Report/"+key,"The sled reaches the gate",report)
            fail=note("Missed/"+key,"Only the stragglers",
                act["failure"]+(" You can continue building the city." if chapter==3 else " The next rescue will go ahead."))
            goals=[dict(goal,target=[places[name] for name in goal["names"]]) for goal in path["goals"]]
            goals.append(dict(kind="checks",label="Ready",quantity=1,text="Keep the Generator on and ready supplies",
                description="Keep the Generator on and set aside "+", ".join(f"{n} {name.lower()}" for name,n in path["price"].items())+
                ". The rescue spends these supplies once, after all objectives are complete."))
            quests.append(writer.build("NI Lifeline "+key,qid,path["title"],goals,identity,localize,"LastSignal/Lifeline/Quest/"+key,
                deadline=act["days"]))
            generator=typed("FrostpunkGeneratorIsActiveExpression")+b"\0"
            ready=condition(path["price"])+[generator]
            poll("Ready/"+key,check+[state("ready",0)]+ready,[put("ready",1),progress_quest(qid,"Ready")],0.25)
            # A completed construction goal does not authorize overdrawing a stockpile.
            # After completion, resupply or restart the Generator before the original deadline.
            events.append(completed_event("NI Lifeline Cleared "+key,identity("event/cleared/"+key),
                identity("trigger/cleared/"+key),qid,check,[put("cleared",1)]))
            settle=check+[state("cleared",1)]+ready
            success=advance+[put("rescues",1,1),put("rescued/"+str(chapter),1),
                put("people",total,1)]+supplies(path["price"],-1)+people(arrival_groups)+supplies(path["salvage"])+[
                morale("Hope rise - moderately"),arrival]
            poll("Crossing/"+key,settle,success)
            miss=advance+[put("people",sum(STRAGGLERS[chapter-1].values()),1)]+people(STRAGGLERS[chapter-1])+[
                morale("Discontent rise - moderately"),fail]
            start=[put("plan",plan),put("ready",0),put("cleared",0)]
            if chapter==1:
                start+=people({"workers":8,"engineers":4})+[put("people",12,1)]+supplies(START_SUPPLIES[plan-1])
            if chapter==2:
                start+=[arrive(6,"workers","ill") if plan==1 else arrive(6,"engineers"),put("people",6,1)]
            start+=[start_quest(qid),timer("deadline/"+key,act["days"],[guarded(check,[
                guarded(settle,success),guarded(check,miss)])])]
            select=gate(chapter,0)
            requirements=[state("rope",1),state("rescues",2)] if plan==3 else []
            options.append((path["label"],path["description"],requirements,select+requirements,start))
            missions.append(dict(chapter=chapter,plan=plan,title=path["title"],deadline=act["days"],quest=qid,
                arrival=arrival_groups,fallback=STRAGGLERS[chapter-1],price=path["price"],goals=goals,
                entry_supplies=START_SUPPLIES[plan-1] if chapter==1 else {},salvage=path["salvage"]))
        details=act["plot"]+f"\n\nAfter you choose, the rescue has {act['days']} game days. Keep the Generator on when the sled is ready."
        briefing=scene("Briefing/"+str(chapter),act["title"],details,options)
        if chapter==1:
            events.append(event("NI Lifeline start",identity("event/start"),identity("trigger/start"),
                [scoped,state("chapter",0),equals(OLD+"act",0)],
                [put("chapter",1),timer("opening",0.01,[guarded(gate(1,0),[briefing])])]))
        else:
            poll("Briefing/"+str(chapter),gate(chapter,0)+[state("offered",chapter-2)],
                 [put("offered",chapter-1),timer("briefing/"+str(chapter),0.02,[guarded(gate(chapter,0),[briefing])])])
    return events,dialogs,quests,dict(missions=missions,chapters=len(CHAPTERS),forecast=identity("forecast"),
        first_outriders={"workers":8,"engineers":4},start_scene=identity("dialog/Briefing/1"),
        rope_price={"Wood":20})
