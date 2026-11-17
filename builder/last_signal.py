"""The Last Signal: a finite, fail-forward story about routing emergency heat."""
from city_mastery import building_ids
from tools.mission_schema import MissionWriter, completed_event
from tools.native_scenario import (affordable, apply_modifier, change_resource, compare, delayed,
    dilemma, equals, event, guarded, integer, predefined, progress_quest, set_variable,
    start_quest, typed, variable)

PREFIX = "NI/LastSignal/"


def building(text, *names, quantity=1):
    return dict(kind="build", text=text, names=names, quantity=quantity)


def technology(text, key):
    return dict(kind="research", text=text, key=key)


ACTS = [
    dict(title="Someone is still listening", days=7, text=(
        "Edith Vale, the city's night telegrapher, hears three settlements answering an SOS "
        "sent before the last storm. If anyone is to find us, we first need a mast and a place to treat the injured."),
        routes=[dict(title="Raise the mast", roster="opening", bill={}, checks=0, goals=[
            building("Build a Workshop", "Engineers Lab"), building("Build a Beacon", "Beacon"),
            building("Build a Medical Post", "Medical Post")])]),
    dict(title="A voice in the dark", days=6, text=(
        "A schoolteacher at Ember Row transmits a roll call every night. Ivo, the relay mechanic, needs steam for his "
        "transmitter before the wind tears down its aerial. The damaged junction can feed only one circuit."),
        routes=[
            dict(title="Heat the sickrooms", roster="signal_homes", bill={"Coal":35,"Food Rations":10}, checks=4,
                 goals=[building("Build six homes", "Tent", "Bunkhouse", "House", quantity=6),
                        building("Build a Cookhouse", "Food Processing")]),
            dict(title="Give Ivo the steam", roster="signal_relay", bill={"Coal":35,"Wood":12}, checks=4,
                 goals=[technology("Research Steam Hubs", "H 1_SteamHub"), building("Build two Steam Hubs", "Steam Hub", quantity=2)]),
        ]),
    dict(title="Two calls, one boiler", days=7, text=(
        "The crew at Kiln Nine offers a route over the ridge, but their boilers are failing. Meanwhile the clinic "
        "can hear sledges approaching through the snow. Edith asks whose call we will answer first."),
        routes=[
            dict(title="Hold the ward open", roster="signal_ward", bill={"Coal":45,"Food Rations":16}, checks=6,
                 goals=[building("Build two Medical Posts or Infirmaries", "Medical Post", "Ambulatorium", quantity=2),
                        technology("Research Healthcare Insulation", "F 6_Healthcare Buildings - warmer")]),
            dict(title="Keep Kiln Nine running", roster="signal_heat", bill={"Coal":50,"Steel":12}, checks=6,
                 goals=[building("Build two coal mines or Coal Thumpers", "Coal Mine","SteamCoalMine","AdvancedCoalMine",
                                 "CoalThumper","CoalThumperSteam",quantity=2),
                        technology("Research Generator Power Upgrade I", "H 2_Generator Upgrade - power 1")]),
        ]),
    dict(title="The final transmission", days=8, text=(
        "The relay has enough life for one last broadcast. We can send a public route through the storm or give the "
        "frequency to a small crew carrying the regional archive. Edith asks what the city owes to strangers it cannot see."),
        routes=[
            dict(title="Broadcast the route", roster="signal_open", bill={"Coal":60,"Food Rations":20}, checks=8,
                 goals=[building("Build a Hothouse", "Plantation","Steam Plantation"),
                        building("Build two Resource Depots", "Resource Depot","Resource Depot Big",quantity=2)]),
            dict(title="Send the archive", roster="signal_archive", bill={"Coal":60,"Steel":18}, checks=8,
                 goals=[building("Build a Steelworks", "Iron Ore Mine","SteamIronOreMine","AdvancedOreMine"),
                        technology("Research Mechanical Calculators", "03_TierUnlock3")]),
        ]),
]

ROUTING = {
    "signal_homes":"+1 insulation for homes and wards; Workshop efficiency −15%.",
    "signal_relay":"Workshop and extraction efficiency +25%; home insulation −1.",
    "signal_ward":"Wards gain +2 insulation and 50% efficiency; industry efficiency −20%.",
    "signal_heat":"Coal extraction efficiency +40%; ward insulation −1.",
    "signal_open":"Hothouse and Cookhouse efficiency +35%; industry efficiency −20%.",
    "signal_archive":"Workshop and Steelworks efficiency +35%; Cookhouse efficiency −20%.",
}


def build(source, buildings, techinfo, resources, identity, bonuses, localize, dt, qt):
    events, dialogs, quests, metadata = [], [], [], []
    places = {key:value.hex() for key,value in building_ids(buildings).items()}
    techs = {row["name"]:row["guid"] for row in techinfo}
    writer = MissionWriter((source/"configs/frostpunkquestsconfig.bin").read_bytes(), qt)
    scenario = bytes.fromhex(identity("scenario"))
    scoped = typed("FrostpunkCurrentScenarioCheckExpression") + scenario + b"\0"
    native_events = (source/"configs/frostpunkgameeventsconfig.bin").read_bytes()
    from tools.story_schema import DEFAULT
    assert typed("FrostpunkCurrentScenarioCheckExpression")+bytes.fromhex(DEFAULT)+b"\0" in native_events
    native_effects = (source/"configs/frostpunkeffectsconfig.bin").read_bytes()

    def morale(name):
        key = typed("GOLD [Common] "+name)
        at = native_effects.index(b"\1"+key)+1+len(key)
        return predefined(native_effects[at:at+16].hex())

    def state(key, value): return equals(PREFIX+key, value)
    def put(key, value, op=0): return set_variable(PREFIX+key, value, op)
    def timer(key, days, effects): return delayed(identity("timer/"+key), days, effects)
    def guard(phase, route): return [scoped, state("act",phase), state("route",route)]
    def add_event(key, conditions, effects, period=None):
        events.append(event("NI Last Signal "+key,identity("event/"+key),identity("trigger/"+key),conditions,effects,period))

    def dialog(key,title,description,choices):
        options = [dt.choice("NI Signal "+key+"/"+str(i),identity(f"choice/{key}/{i}"),
            label,detail,[],[guarded(checks,actions)],localize,f"LastSignal/{key}/{i}")
            for i,(label,detail,checks,actions) in enumerate(choices)]
        uid = identity("dialog/"+key)
        dialogs.append(dt.build("NI Last Signal "+key,uid,title,description,options,localize,"LastSignal/"+key,False,
            subtitle="The Last Signal"))
        return dilemma(uid)

    for phase, act in enumerate(ACTS, 1):
        choices = []
        for route, path in enumerate(act["routes"], 1):
            key = f"Act{phase}/{route}"
            qid = identity("quest/"+key)
            check = guard(phase, route)
            objectives = []
            for original in path["goals"]:
                goal = dict(original)
                if goal["kind"] == "build":
                    goal["target"] = [places[name] for name in goal.pop("names")]
                else:
                    goal["target"] = techs[goal.pop("key")]
                objectives.append(goal)
            bill = path["bill"]
            bill_text = ", ".join(f"{value} {name.lower()}" for name,value in bill.items())
            bonus = bonuses.get(path["roster"])
            cleanup = [typed("FrostpunkRemoveModifierEffect")+bytes.fromhex(bonus)] if bonus else []
            if path["checks"]:
                objectives.append(dict(kind="checks",text=f"Run {path['checks']} service shifts",
                    description=f"Every twelve hours while the Generator is on, spend {bill_text} above a protected reserve of 120 coal.",
                    quantity=path["checks"]))
                requirements = dict(bill)
                requirements["Coal"] += 120
                add_event("service/"+key, check+[compare(integer(path["checks"]-1),4,variable(PREFIX+"checks")),
                    typed("FrostpunkGeneratorIsActiveExpression")+b"\0"]+
                    [affordable(resources[name].hex(),amount) for name,amount in requirements.items()],
                    [change_resource(resources[name].hex(),-amount) for name,amount in bill.items()]+
                    [put("checks",1,1),progress_quest(qid,"Stability")],0.5)
            quests.append(writer.build("NI Last Signal "+key,qid,act["title"]+" — "+path["title"],objectives,
                identity,localize,"LastSignal/Quest/"+key,deadline=act["days"]))
            advance = cleanup+[put("act",phase+1),put("route",0)]
            if phase == len(ACTS):
                advance += [put("final_route",route)]
            events.append(completed_event("NI Last Signal complete "+key,identity("event/complete/"+key),
                identity("trigger/complete/"+key),qid,check,[put("successes",1,1),morale("Hope rise - moderately")]+advance))
            failure = [morale("Discontent rise - moderately")]+advance
            start = [put("route",route),put("checks",0)]
            if bonus:
                start.append(apply_modifier(bonus))
            start += [start_quest(qid),timer("deadline/"+key,act["days"],[guarded(check,failure)])]
            detail = f"{act['days']} days. " + (" ".join([ROUTING[path["roster"]], f"Each service shift costs {bill_text}."]) if bonus else "Build a Beacon, a Medical Post and a Workshop.")
            choices.append((path["title"],detail,guard(phase,0),start))
            metadata.append(dict(phase=phase,route=route,guid=qid,title=path["title"],deadline=act["days"],bonus=bonus,
                payment=bill,goals=objectives))
        title = act["title"]
        offered = dialog("Act"+str(phase),title,act["text"]+
            f"\n\nChoose a circuit within two days, or Edith will use “{choices[0][0]}”. The {act['days']}-day objective begins once the circuit is chosen. "
            "A missed objective costs goodwill and the story goes on.",choices)
        add_event("offer/"+str(phase),guard(phase,0)+[state("offered",phase-1)],[
            put("offered",phase),offered,timer("autopick/"+str(phase),2,[guarded(guard(phase,0),choices[0][3])])],0.25)
    for count in range(5):
        for route in (1,2):
            ending,story = (
                ("Many voices", "For the first time since the snow, the city hears people making plans instead of listing their dead.") if count>=3 else
                ("A thin connection", "Not everyone answered. A handful of stations keep a watch, each leaving a light in the window for the others.") if count>=1 else
                ("Silence on the ridge", "No one answers the relay. Edith keeps the original roll call pinned beside her desk anyway."))
            final = ("Edith sends the route on an open frequency." if route==1 else "Ivo seals the archive in a steel case for the relay crew.")
            key = f"Ending/{count}/{route}"
            ending_plot = dialog(key,ending,f"{story}\n\n{final}\n\nService promises kept: {count} of 4. The story has ended; you can continue with your city.",
                                 [("Keep the light on","Return to the city.",[scoped],[])])
            add_event("ending/"+key,[scoped,state("act",5),state("successes",count),state("final_route",route)],
                [put("act",99),ending_plot],0.25)
    add_event("start",[scoped,state("act",0),equals("NI/Lifeline/chapter",0),equals("NI/WinterRoad/chapter",0)],[put("act",1)])
    return events,dialogs,quests,dict(scenario=identity("scenario"),event_setup=identity("event-setup"),
        acts=metadata,response_days=2,ending_thresholds=[0,1,3])
