"""Write Faultline's timed pressure jobs, district routing and consequences."""
from city_mastery import building_ids
from faultline_story import ACTS
from tools.housing_schema import OPEN_MAP, RETURN
from tools.mission_schema import MissionWriter, completed_event
from tools.native_binary import SchemaError, entry, f32, u32
from tools.native_scenario import (apply_modifier, change_resource, compact, compare, delayed, dilemma, equals,
    event, floating, guarded, integer, predefined, progress_quest, set_variable, start_quest, typed, variable)
from tools.convoy_schema import arrive
from winter_road_maps import SITES, beacon_exists, constructed, reveal_site, validate_native_map_effects


PREFIX = "NI/Faultline/"
SCAN = 1/24
STRESS = compact("FrostpunkGeneratorStressExpression")
CHANGE_STRESS = typed("FrostpunkModifyGeneratorEffect")
SELECT_GENERATOR = typed("FrostpunkSelectEffect")+compact("FrostpunkGeneratorSelector",bytes(7)+u32(1))
PROFILES = {
    "ward": "Homes and medical buildings gain +1 insulation. Coal works, Steelworks and Factories lose 25% efficiency.",
    "works": "Coal works, Steelworks and Factories gain 40% efficiency. Homes lose one insulation level.",
    "bypass": "Cookhouses and medical buildings gain +1 insulation. Workshops lose 30% efficiency.",
}
REFITS = {"accumulator": "the pressure accumulator", "bypass": "the isolated bypass",
          "surveyed": "the returned shelf survey"}
REWARDS = {
    "ward_crew": "The station medics improve healing by 25% if you finish.",
    "works_crew": "The station fitters improve Steelworks and Factory efficiency by 25% if you finish.",
    "accumulator": "A completed accumulator improves stress recovery by 35% and opens a final route.",
    "isolation": "A completed bypass adds +1 insulation to clinics and can open a final route after a scout survey.",
    "shelters": "Completing the route gives Cookhouses 30% more efficiency.",
}


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

    def identity(key):
        return guid("faultline/"+key).hex()

    def eq(key, number):
        return equals(PREFIX+key, number)

    def put(key, value, operation=0):
        return set_variable(PREFIX+key, value, operation)

    def at_least(key, value):
        return compare(variable(PREFIX+key), 4, integer(value))

    def add(key, checks, actions, clock=SCAN):
        events.append(event("NI Faultline "+key, identity("event/"+key), identity("trigger/"+key),
                            [scope]+checks, actions, clock))

    def after(key, days, actions):
        return delayed(identity("timer/"+key), days, actions)

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

    # Every mode-specific global is initialized in the new scenario only.
    # This also keeps the native diagnostic log free of missing-variable spam.
    flags = sorted({p["flag"] for act in ACTS for p in act["plans"] if "flag" in p})
    fields = ("plan", "stroke", "tripped", "trips", "kept", "offered", "scout_returned", "map_open", "ending")
    add("open",[eq("phase",0)],[put("phase",1)]+[put(key,0) for key in (*fields, *flags)], None)

    add("open Frostland", [at_least("phase",1), eq("map_open",0), beacon_exists()],
        [put("map_open",1), OPEN_MAP, *(reveal_site(uid) for _,uid,_,_ in SITES)], 0.25)
    trip_notice = report("trip", "The main circuit tripped",
        "The valve has closed and all insulated buildings lose two heat levels. Switch off Overdrive and let the Generator "
        "stress drop to 15%. Keep the Generator itself running. Once it cools, the circuit reconnects and the current job resumes.")
    for welded,limit in ((0,76),(1,84)):
        add("trip/"+str(limit), [at_least("plan",1), eq("tripped",0), eq("welded",welded), stress_check(4,limit)],
            [put("tripped",1), put("trips",1,1), change("trip"), trip_notice])
    add("reconnect", [eq("tripped",1), stress_check(5,15)], [put("tripped",0), change("trip",True)])

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
            quests.append(writer.build("NI Faultline "+key,uid,act["title"]+" — "+plan["title"],goals,
                                       identity,localize,"Faultline/Quest/"+key,act["days"]))
            advance = [put("phase",phase+1), put("plan",0), change(plan["profile"],True),
                       guarded([eq("tripped",1)],[put("tripped",0),change("trip",True)])]
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
            # Both impact and timing are visible before any circuit is selected.
            detail = PROFILES[plan["profile"]]+" Sequence: "+" → ".join(sequence)+"."
            if plan.get("persistent"):
                detail += " "+REWARDS[plan["persistent"]]
            if plan.get("requires"):
                detail += " Requires "+" and ".join(REFITS[flag] for flag in plan["requires"])+"."
            if phase == 4 and plan.get("flag") == "welded":
                detail += " The finished weld raises the trip threshold from 76% to 84%."
            choose = [scope]+phase_at(phase,0)
            options.append((plan["title"],detail,visible,[guarded(choose+visible,start)]))
            missions.append(dict(phase=phase,plan=number,quest=uid,deadline=act["days"],goals=goals,
                                 title=plan["title"],profile=plan["profile"],strokes=plan["strokes"],
                                 requires=plan.get("requires",()),flag=plan.get("flag")))

        intro = ("\n\nRead the Generator's stress gauge. Turn Overdrive on to raise it and off to cool it. The valve checks "
                 "hourly. Enter each band in order while the Generator is running. A pulse vents part of the stress. "
                 "At 76% the circuit trips and the city loses two heat levels until stress cools to 15%."
                 if phase == 1 else "")
        offer = scene(f"briefing/{phase}",act["title"],act["story"]+intro+
                      f"\n\n{act['days']} days after you choose. If you leave this unanswered for one day, "
                      f"the dispatcher uses “{options[0][0]}”.",options)
        add(f"briefing/{phase}",phase_at(phase,0)+[eq("offered",phase-1)],
            [put("offered",phase),offer,after(f"default/{phase}",1,options[0][3])],0.25)

    finish = phase_at(len(ACTS)+1,0)+[eq("ending",0)]
    for kept in (4,5):
        title = "The Basin Accord"
        text = ("The shelters have voted to share the heating main. Households and wards gain +1 insulation as the new "
                "fittings go in. You completed the last signal and brought the line through the winter with at most one trip."
                f"\n\nSignals and refits completed: {kept} of {len(ACTS)}. The campaign is complete. You can continue playing your city.")
        add(f"accord/{kept}",finish+[eq("final",1),eq("kept",kept),
            compare(integer(1),4,variable(PREFIX+"trips"))],
            [put("ending",3),change("accord"),report(f"accord/{kept}",title,text)],0.25)
    outcomes = (
        (0, "A Light in the Basin", "The local shelters have a place to come home to. The distant line never answered."),
        (1, "The Signal Holds", "Edith reads the answers into the record. There is a winter line now, and people on both ends intend to keep it."),
    )
    for final,title,story in outcomes:
        for kept in range(6):
            text = f"{story}\n\nSignals and refits completed: {kept} of {len(ACTS)}. Faultline is complete. You can continue playing your city."
            add(f"end/{final}/{kept}",finish+[eq("final",final),eq("kept",kept)],
                [put("ending",1+final),report(f"end/{final}/{kept}",title,text)],0.25)
    return events, dialogs, quests, dict(scenario=scenario,missions=missions,scan_hours=1,trip=76,welded_trip=84,
                                        reset=15,modifiers={key:value for key,value in modifiers.items() if key.startswith("faultline/")})
