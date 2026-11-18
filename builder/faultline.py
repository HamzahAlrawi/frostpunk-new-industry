"""Write Faultline's timed pressure jobs, district routing and consequences."""
from city_mastery import building_ids
from faultline_story import ACTS, LEAK_REPAIR, WATCH_LEGS
from faultline_cinematics import SIGNAL, SHOTS, play, signal
from tools.housing_schema import OPEN_MAP, RETURN
from tools.mission_schema import MissionWriter, completed_event
from tools.native_binary import SchemaError, entry, f32, u32
from tools.native_scenario import (affordable, apply_modifier, change_resource, compact, compare, delayed,
    dilemma, equals, event, first_match, floating, guarded, integer, predefined, progress_quest, set_variable, start_quest,
    typed, variable)
from tools.convoy_schema import arrive
from winter_road_maps import SITES, beacon_exists, constructed, reveal_site, validate_native_map_effects


PREFIX = "NI/Faultline/"
SCAN = 1/24
TRIP = 72
WELDED_TRIP = 82
RESET = 14
STRESS = compact("FrostpunkGeneratorStressExpression")
CHANGE_STRESS = typed("FrostpunkModifyGeneratorEffect")
SELECT_GENERATOR = typed("FrostpunkSelectEffect")+compact("FrostpunkGeneratorSelector",bytes(7)+u32(1))
PROFILES = {
    "ward": "Homes and medical buildings gain +1 insulation. Coal works, Steelworks and Factories lose 25% efficiency.",
    "works": "Coal works, Steelworks and Factories gain 40% efficiency. Homes lose one insulation level.",
    "bypass": "Cookhouses and medical buildings gain +1 insulation. Workshops lose 30% efficiency.",
}
REFITS = {"accumulator": "the pressure accumulator", "bypass": "the isolated bypass",
          "surveyed": "the returned shelf survey", "watch_kept": "the three completed watches at Broken Mile"}
REWARDS = {
    "ward_crew": "The station medics improve healing by 25% if you finish.",
    "works_crew": "The station fitters improve Steelworks and Factory efficiency by 25% if you finish.",
    "accumulator": "A completed accumulator improves stress recovery by 35% and opens a final route.",
    "isolation": "A completed bypass adds +1 insulation to clinics and can open a final route after a scout survey.",
    "shelters": "Completing the route gives Cookhouses 30% more efficiency.",
    "resettled": "Reclaimed pipe adds one insulation level to Steelworks and Factories.",
}


def either(conditions):
    return typed("BooleanOperationExpression")+u32(1)+u32(len(conditions))+b"".join(conditions)


def stress_check(operator, percent):
    return typed("FloatComparisonExpression") + STRESS + u32(operator) + floating(percent/100)


def vent(percent):
    return CHANGE_STRESS + f32(-percent/100) + u32(0)


def verify_native_stress(events, dilemmas):
    # Winterhome checks 60% stress; the Endless Winter test checks 25% on
    # both sides of the threshold. The native core sacrifice vents 35 points.
    if (stress_check(4,60) not in events or stress_check(5,25) not in events
            or vent(35) + typed("FrostpunkChangeResourcesEffect") not in dilemmas):
        raise SchemaError("Unsupported native Generator stress read or adjustment")
    if SELECT_GENERATOR + typed("FrostpunkApplyModifierEffect") not in events:
        raise SchemaError("Unsupported Generator selection")


def build(source, buildings, techinfo, resources, guid, scenario, modifiers, localize, dt, qt, recipes):
    events, dialogs, quests, missions = [], [], [], []
    configs = source/"configs"
    native = (configs/"frostpunkgameeventsconfig.bin").read_bytes()
    verify_native_stress(native, (configs/"frostpunkdilemmasconfig.bin").read_bytes())
    validate_native_map_effects(native)
    values = (configs/"frostpunkeffectsconfig.bin").read_bytes()
    writer = MissionWriter((configs/"frostpunkquestsconfig.bin").read_bytes(), qt)
    places = {key: value.hex() for key,value in building_ids(buildings).items()}
    techs = {row["name"]: row["guid"] for row in techinfo}
    scope = typed("FrostpunkCurrentScenarioCheckExpression")+bytes.fromhex(scenario)+b"\0"
    running = typed("FrostpunkGeneratorIsActiveExpression")+b"\0"
    coal = resources["Coal"].hex()
    filmed = {}

    def identity(key):
        return guid("faultline/"+key).hex()

    def eq(key, number):
        return equals(PREFIX+key, number)

    def put(key, value, operation=0):
        return set_variable(PREFIX+key, value, operation)

    def at_least(key, value):
        return compare(variable(PREFIX+key), 4, integer(value))

    def at_most(key, value):
        return compare(integer(value), 4, variable(PREFIX+key))

    def add(key, checks, actions, clock=SCAN):
        events.append(event("NI Faultline "+key, identity("event/"+key), identity("trigger/"+key),
                            [scope]+checks, actions, clock))

    def after(key, days, actions):
        return delayed(identity("timer/"+key), days, actions)

    def with_shot(key, shot, checks, actions):
        # The native signal opens the dialogue after camera restoration. A
        # timed, idempotent delivery covers skipped clips and mid-shot reloads.
        callback = signal(shot,guid)
        pending = "shot/"+key
        ready = [scope,eq(pending,1)]+checks
        finish = [put(pending,2)]+actions
        events.append(entry("NI Faultline film "+key,identity("event/film/"+key))+b"\0\1"+f32(1)+u32(1)
                      +typed(SIGNAL)+bytes.fromhex(identity("trigger/film/"+key)+callback)
                      +u32(len(ready))+b"".join(ready)+u32(len(finish))+b"".join(finish))
        filmed[key]=dict(shot=shot,signal=callback)
        return [put(pending,1),play(shot),after("film/"+key,0.375,[guarded(ready,finish)])]

    def change(profile, remove=False):
        name = modifiers["faultline/"+profile]
        return typed("FrostpunkRemoveModifierEffect")+bytes.fromhex(name) if remove else apply_modifier(name)

    def mood(name):
        donor = b"\1"+typed("GOLD [Common] "+name)
        at = values.index(donor)+len(donor)
        return predefined(values[at:at+16].hex())

    def scene(key, title, text, options, small=False):
        uid = identity("dialog/"+key)
        loc = "Faultline/"+key
        choices = [dt.choice("NI Faultline "+key+"/"+str(i), identity(f"choice/{key}/{i}"),
                   name, detail, visible, actions, localize, loc+"/"+str(i))
                   for i,(name,detail,visible,actions) in enumerate(options)]
        dialogs.append(dt.build("NI Faultline "+key, uid, title, text, choices, localize, loc, small,
                                subtitle="The Last Signal: Faultline"))
        return dilemma(uid)

    def report(key, title, text):
        return scene(key, title, text, [("Return to the city", "Check the Generator and your objectives.", [], [])], True)

    def phase_at(phase, plan):
        return [eq("phase",phase), eq("plan",plan)]

    def budget(cost):
        return ", ".join(f"{quantity} {name.lower()}" for name,quantity in cost.items())

    def pay(cost):
        return [change_resource(resources[name].hex(),-quantity) for name,quantity in cost.items()]

    def can_pay(cost):
        return [affordable(resources[name].hex(),quantity) for name,quantity in cost.items()]

    # Every mode-specific global is initialized in the new scenario only.
    # This also keeps the native diagnostic log free of missing-variable spam.
    flags = sorted({p["flag"] for act in ACTS for p in act["plans"] if "flag" in p})
    fields = ("plan", "stroke", "tripped", "trips", "kept", "offered", "scout_returned", "map_open", "ending")
    add("open",[eq("phase",0)],[put("phase",1)]+[put(key,0) for key in (*fields, *flags)], None)

    add("open Frostland", [at_least("phase",1), eq("map_open",0), beacon_exists()],
        [put("map_open",1), OPEN_MAP, *(reveal_site(uid) for _,uid,_,_ in SITES)], 0.25)
    trip_notice = report("trip", "The main circuit tripped",
        "The valve has closed and all insulated buildings lose two heat levels. Switch off Overdrive and let the Generator "
        f"stress drop to {RESET}%. Keep the Generator itself running. Once it cools, the circuit reconnects and the current job resumes.")
    for welded,limit in ((0,TRIP),(1,WELDED_TRIP)):
        add("trip/"+str(limit), [at_least("plan",1), eq("tripped",0), eq("welded",welded), stress_check(4,limit)],
            [put("tripped",1), put("trips",1,1), change("trip"), trip_notice])
    add("reconnect", [eq("tripped",1), stress_check(5,RESET)], [put("tripped",0), change("trip",True)])

    for phase, act in enumerate(ACTS,1):
        options=[]
        for number, plan in enumerate(act["plans"],1):
            key=f"act/{phase}/{number}"
            uid = identity("quest/"+key)
            active = phase_at(phase,number)
            visible = [eq(flag,1) for flag in plan.get("requires",())]
            goals = []
            for authored in plan["goals"]:
                goal=dict(authored)
                if goal["kind"] in ("build","operate"):
                    goal["target"] = [places[name] for name in goal.pop("names")]
                elif goal["kind"] == "research":
                    goal["target"] = techs[goal.pop("tech")]
                elif goal["kind"] == "produce":
                    goal["target"] = recipes[goal.pop("recipe")]
                elif goal["kind"] == "scout":
                    goal.update(kind="checks",label="Scout")
                    checks = [scope]+active+[eq("scout_returned",0)]
                    effects = [put("scout_returned",1),progress_quest(uid,"Scout")]
                    events.append(entry("NI Faultline Scouts return",identity("event/scouts/"+key))+b"\0\1"+f32(1)+u32(1)
                                  +typed(RETURN)+bytes.fromhex(identity("trigger/scouts/"+key))+b"\0\0"
                                  +u32(len(checks))+b"".join(checks)+u32(len(effects))+b"".join(effects))
                goals.append(goal)
            hardware = [constructed(goal["target"][0],goal.get("quantity",1))
                        for goal in goals if goal["kind"] == "build" and len(goal["target"])==1]
            sequence = []
            for step, stroke in enumerate(plan["strokes"],1):
                low, high, draw = (stroke[name] for name in ("low","high","draw"))
                label = f"Stroke{step}"
                if draw:
                    title=f"{step}. Pulse at {low}–{high}% Generator stress"
                    detail=f"Turn on Overdrive. The next hourly check inside this band sends the pulse automatically and vents {draw} stress points."
                    if hardware:
                        detail+=" Complete the listed construction first."
                    checks=[stress_check(4,low),stress_check(5,high)]
                    actions=[SELECT_GENERATOR+vent(draw)]
                    sequence.append(f"pulse at {low}–{high}%")
                else:
                    title=f"{step}. Cool to {high}% Generator stress"
                    detail="Turn off Overdrive. Keep the Generator running while stress drops."
                    checks=[stress_check(5,high)]
                    actions=[]
                    sequence.append(f"cool to {high}%")
                goals.append(dict(kind="checks",label=label,text=title,description=detail))
                add(key+f"/stroke/{step}", active+[eq("tripped",0), eq("stroke",step-1), running]+hardware+checks,
                    [put("stroke",step)]+actions+[progress_quest(uid,label)])
            watch = plan.get("watch")
            if watch:
                low, high, hours = (watch[name] for name in ("low","high","hours"))
                threshold = watch["reserve"]+watch["coal"]
                goals.append(dict(kind="checks",label="Watch",quantity=WATCH_LEGS,
                    text=f"Complete {WATCH_LEGS} watches and send fuel to Broken Mile",
                    description=f"Each watch takes {hours} consecutive hourly checks at {low}–{high}% stress with the "
                                f"Generator running. Keep {threshold} coal ready. Each completed watch sends {watch['coal']} "
                                f"coal and leaves a reserve of at least {watch['reserve']}. A lapse restarts only the current watch."))
                waiting = active+[at_most("leg",WATCH_LEGS-1)]
                clear = either([eq("leak",0),eq("leak",3)])
                response = active+[eq("leak",1)]

                def repair(route, days):
                    return [put("leak",2),after(key+"/repair/"+route,days,[guarded(active+[eq("leak",2)],
                            [put("leak",3),change("leak",True)])])]

                seal = repair("isolate",0.5)
                patch_checks = can_pay(LEAK_REPAIR)+[running,stress_check(5,38),eq("tripped",0)]
                leak = scene(key+"/leak","The lamp goes out at Broken Mile",
                    "A seam opened as the first coal sledge crossed. The supply watch is suspended. Until the repair "
                    "is complete, insulated buildings lose one heat level. The crew can isolate the spur after eighteen hours "
                    "if you leave the order unanswered.",
                    [("Clamp the seam under pressure","Two-hour repair. Requires "+budget(LEAK_REPAIR)+
                     ", a running Generator and at most 38% stress.",
                      response+patch_checks,[guarded([scope]+response+patch_checks,pay(LEAK_REPAIR)+repair("clamp",2*SCAN))]),
                     ("Isolate the bend","No materials. The repair takes twelve hours.",response,
                      [guarded([scope]+response,seal)])])
                outage = [put("leak",1),change("leak"),leak,
                          after(key+"/auto-isolate",0.75,[guarded([scope]+response,seal)])]
                readiness = [running,eq("tripped",0),stress_check(4,low),stress_check(5,high),
                             affordable(coal,threshold)]
                watch_tick = [put("hours",1,1),guarded([eq("hours",hours)],
                    [put("hours",0),put("leg",1,1),change_resource(coal,-watch["coal"]),
                     guarded([eq("leg",1)],outage),progress_quest(uid,"Watch")])]
                add(key+"/watch", waiting+[clear], [first_match(("Fuel watch",readiness,watch_tick),
                    ("Interrupted watch",[at_least("hours",1)],[put("hours",0)]))])
            pledge = plan.get("pledge")
            if pledge:
                goals.append(dict(kind="checks",label="Pledge",text="Dispatch the charter supplies",
                    description="The supplies depart automatically once the stock is ready and the signal sequence is complete. "
                                "Set aside "+budget(pledge)+". This shipment is paid once."))
                add(key+"/pledge", active+[eq("pledged",0),eq("stroke",len(plan["strokes"]))]+can_pay(pledge),
                    [put("pledged",1)]+pay(pledge)+[progress_quest(uid,"Pledge")])
            quests.append(writer.build("NI Faultline "+key,uid,act["title"]+" — "+plan["title"],goals,
                                       identity,localize,"Faultline/Quest/"+key,act["days"]))
            advance = [put("phase",phase+1), put("plan",0), change(plan["profile"],True),
                       guarded([eq("tripped",1)],[put("tripped",0),change("trip",True)])]
            if watch:
                advance.append(guarded([at_least("leak",1),at_most("leak",2)],[change("leak",True),put("leak",3)]))
            success = advance+[put("kept",1,1),mood("Hope rise - moderately")]
            if flag:=plan.get("flag"):
                success.append(put(flag,1))
            if profile:=plan.get("persistent"):
                success.append(change(profile))
            success += [change_resource(resources[k].hex(),n) for k,n in plan.get("cargo",{}).items()]
            success += [arrive(n,role) for role,n in plan.get("people",{}).items()]
            success.append(report(key+"/success",act["title"],plan["report"]))
            failure = advance+[mood("Discontent rise - moderately"),report(key+"/miss","The line went quiet",act["failure"])]
            events.append(completed_event("NI Faultline Cleared "+key,identity("event/clear/"+key),
                          identity("trigger/clear/"+key),uid,[scope]+active,success))
            start = [put("plan",number), put("stroke",0), put("scout_returned",0), change(plan["profile"]),
                     start_quest(uid), after(key+"/deadline",act["days"],[guarded([scope]+active,failure)])]
            if watch:
                start[:0]=[put("leg",0),put("hours",0),put("leak",0),put("watch_kept",0)]
            if pledge:
                start[:0]=[put("pledged",0),put("charter",0)]
            # Both impact and timing are visible before any circuit is selected.
            detail = PROFILES[plan["profile"]]
            if sequence:
                detail += " Sequence: "+" → ".join(sequence)+"."
            if watch:
                detail += (f" Hold {WATCH_LEGS} × {watch['hours']} hours at {watch['low']}–{watch['high']}% stress. "
                           f"Send {watch['coal']} coal each watch and keep {watch['reserve']} in reserve.")
            if pledge:
                detail += " Dispatch "+budget(pledge)+"."
            if plan.get("persistent"):
                detail += " "+REWARDS[plan["persistent"]]
            if plan.get("requires"):
                detail += " Requires "+" and ".join(REFITS[flag] for flag in plan["requires"])+"."
            if phase == 4 and plan.get("flag") == "welded":
                detail += f" The finished weld raises the trip threshold from {TRIP}% to {WELDED_TRIP}%."
            choose = [scope]+phase_at(phase,0)+[eq("ending",0)]
            options.append((plan["title"],detail,choose+visible,[guarded(choose+visible,start)]))
            missions.append(dict(phase=phase,plan=number,quest=uid,deadline=act["days"],goals=goals,
                                 title=plan["title"],profile=plan["profile"],strokes=plan["strokes"],
                                 requires=plan.get("requires",()),flag=plan.get("flag"),watch=watch,pledge=pledge))

        intro = ("\n\nRead the Generator's stress gauge. Turn Overdrive on to raise it and off to cool it. The valve checks "
                 "hourly. Enter each band in order while the Generator is running. A pulse vents part of the stress. "
                 f"At {TRIP}% the circuit trips and the city loses two heat levels until stress cools to {RESET}%."
                 if phase == 1 else "")
        fallback=next(option for option,plan in zip(options,act["plans"]) if not plan.get("requires"))
        offer = scene(f"briefing/{phase}",act["title"],act["story"]+intro+
                      f"\n\n{act['days']} days after you choose. If you leave this unanswered for one day, "
                      f"the dispatcher uses “{fallback[0]}”.",options)
        delivery = [offer,after(f"default/{phase}",1,fallback[3])]
        if shot:=("FirstCall" if phase==1 else act.get("shot")):
            delivery = with_shot(f"briefing/{phase}",shot,phase_at(phase,0)+[eq("ending",0)],delivery)
        add(f"briefing/{phase}",phase_at(phase,0)+[eq("offered",phase-1),eq("ending",0)],
            [put("offered",phase)]+delivery,0.25)

    finish = phase_at(len(ACTS)+1,0)+[eq("ending",0)]
    endings=[]
    for kept in range(5,8):
        title = "The Basin Accord"
        text = ("The shelter crews signed their names to the charter. Households and wards gain one insulation level as "
                "the new fittings go in. You kept the shelters on the line and brought the main through the winter with at most one trip."
                f"\n\nJobs completed: {kept} of {len(ACTS)}. The campaign is complete. You can continue playing your city.")
        add(f"accord/{kept}",finish+[eq("final",1),eq("charter",1),eq("kept",kept),
            compare(integer(1),4,variable(PREFIX+"trips"))],
            [put("ending",3),put("ending/kept",kept),change("accord")],0.25)
        endings.append(([eq("ending",3),eq("ending/kept",kept)],report(f"accord/{kept}",title,text)))
    outcomes = (
        (0, "A Light in the Basin", "The local shelters have a place to come home to. The distant line never answered."),
        (1, "The Signal Holds", "Edith reads the answers into the record. There is a winter line now, and people on both ends intend to keep it."),
    )
    for final,title,story in outcomes:
        for kept in range(8):
            text = f"{story}\n\nJobs completed: {kept} of {len(ACTS)}. Faultline is complete. You can continue playing your city."
            add(f"end/{final}/{kept}",finish+[eq("final",final),eq("kept",kept)],
                [put("ending",1+final),put("ending/kept",kept)],0.25)
            endings.append(([eq("ending",1+final),eq("ending/kept",kept)],report(f"end/{final}/{kept}",title,text)))
    done=phase_at(len(ACTS)+1,0)+[at_least("ending",1)]
    final_report = [guarded(checks,[dialog]) for checks,dialog in endings]
    add("dawn",done+[eq("offered",len(ACTS))],
        [put("offered",len(ACTS)+1)]+with_shot("dawn","Dawn",done,final_report),0.25)
    assert {v["shot"] for v in filmed.values()}==SHOTS.keys()
    return events, dialogs, quests, dict(scenario=scenario,missions=missions,scan_hours=1,trip=TRIP,
        welded_trip=WELDED_TRIP,reset=RESET,films=filmed,watch_legs=WATCH_LEGS,leak_repair=LEAK_REPAIR,
        modifiers={key:value for key,value in modifiers.items() if key.startswith("faultline/")})
