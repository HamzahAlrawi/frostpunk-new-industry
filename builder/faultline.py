"""Write Faultline's timed pressure jobs, district routing and consequences."""
from city_mastery import building_ids
from faultline_cinematics import RECORDING, STOCK_REPLAY, VICTORY
from faultline_story import (ACTS, ADVANCE_CREWS, LEAK_REPAIR, LINE_INSPECTIONS, OPENING_HOURS,
    RELIEF_LINES, WATCH_LEGS, WHITEOUT_HOURS)
from faultline_buildings import MAGAZINE, MAGAZINE_SAVING, RELAY, RELAY_RESET
from faultline_tutorial import LESSONS, lesson_id, show as teach
from tools.housing_schema import OPEN_MAP, RETURN
from tools.mission_schema import MissionWriter, completed_event
from tools.native_binary import SchemaError, entry, f32, u32
from tools.native_scenario import (affordable, apply_modifier, change_resource, compact, compare, delayed,
    dilemma, equals, event, first_match, floating, guarded, integer, predefined, progress_quest, set_variable, start_quest,
    typed, variable)
from tools.convoy_schema import arrive
from tools.thermal_schema import liveable, verify_native_thermal_checks
from winter_road_maps import beacon_exists, constructed, survey_routes, validate_native_map_effects


PREFIX = "NI/Faultline/"
SCAN = 1/24
TRIP = 72
WELDED_TRIP = 82
RESET = 14
STRESS = compact("FrostpunkGeneratorStressExpression")
CHANGE_STRESS = typed("FrostpunkModifyGeneratorEffect")
SELECT_GENERATOR = typed("FrostpunkSelectEffect")+compact("FrostpunkGeneratorSelector",bytes(7)+u32(1))
RECORD_CITY = typed("FrostpunkTimelapseSegmentStartEffect")+bytes.fromhex(RECORDING)
END_CITY = typed("FrostpunkEndGameEffect")+bytes.fromhex(VICTORY)


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
    if RECORD_CITY+typed("FrostpunkConsolePrintEffect") not in events or END_CITY+bytes.fromhex(STOCK_REPLAY) not in events:
        raise SchemaError("Unsupported native city recording or victory action")


def build(source, buildings, techinfo, resources, guid, scenario, modifiers, localize, dt, qt, recipes, structures):
    events, dialogs, quests, missions = [], [], [], []
    configs = source/"configs"
    native = (configs/"frostpunkgameeventsconfig.bin").read_bytes()
    verify_native_stress(native, (configs/"frostpunkdilemmasconfig.bin").read_bytes())
    validate_native_map_effects(native)
    verify_native_thermal_checks(native)
    values = (configs/"frostpunkeffectsconfig.bin").read_bytes()
    writer = MissionWriter((configs/"frostpunkquestsconfig.bin").read_bytes(), qt)
    places = {key: value.hex() for key,value in building_ids(buildings).items()}
    places.update({row["name"]:row["guid"] for row in structures})
    techs = {row["name"]: row["guid"] for row in techinfo}
    scope = typed("FrostpunkCurrentScenarioCheckExpression")+bytes.fromhex(scenario)+b"\0"
    running = typed("FrostpunkGeneratorIsActiveExpression")+b"\0"
    coal = resources["Coal"].hex()
    rescue_quests = {}
    opening_quests = {}

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
                                subtitle="Faultline"))
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

    def warm_station(place):
        return [running,eq("tripped",0),liveable(places[place])]

    def district_ready(line):
        return [running,eq("tripped",0)]+[
            either([liveable(places[name]) for name in group])
            for group in RELIEF_LINES[line]["groups"]]

    def shipment(key, active, checks, title, cost, hours, arrival, *, reserve=0, go="Depart"):
        ready = active+[eq("shipment",0)]+checks
        choice = [scope]+active+[eq("shipment",1)]
        stock = dict(cost)
        if reserve:
            stock["Coal"] += reserve
        available = can_pay(stock)
        arrived = [put("shipment",0)]+arrival
        order = [put("shipment",2)]+pay(cost)+[
            after(key+"/transit",hours*SCAN,[guarded([scope]+active+[eq("shipment",2)],arrived)])]
        defer = [put("shipment",3),after(key+"/defer",6*SCAN,
            [guarded([scope]+active+[eq("shipment",3)],[put("shipment",0)])])]
        terms = f"Load: {budget(cost)}. Arrival in {hours} hours."
        if reserve:
            terms += f" Keep {reserve} coal in the city."
        dialog = scene(key+"/dispatch",title,terms,
            [(go,"Commit this load and track its arrival.",choice+available,
              [guarded(choice+available,order)]),
             ("Wait six hours","Hold the load. No supplies are spent.",choice,[guarded(choice,defer)])],True)
        return ready+available,[put("shipment",1),dialog,
            after(key+"/dismissed",12*SCAN,[guarded(choice,[put("shipment",0)])])]

    # Every mode-specific global is initialized in the new scenario only.
    # This also keeps the native diagnostic log free of missing-variable spam.
    flags = sorted({p["flag"] for act in ACTS for p in act["plans"] if "flag" in p}
                   | {spec["pact"] for spec in RELIEF_LINES.values()})
    fields = ("plan", "stroke", "tripped", "trips", "kept", "offered", "scout_returned", "map_open",
              "ending", "hold_hours", "shipment", "replay_started", "inspections",
              "whiteout", "reserve_used", "clinic_saved", "lift_saved", "clinic_hours", "lift_hours",
              "clinic_open", "lift_open", "advance_crew")
    add("open",[eq("phase",0)],[put("phase",1),RECORD_CITY]+[put(key,0) for key in (*fields, *flags)], None)

    add("open Frostland", [at_least("phase",1), eq("map_open",0), beacon_exists()],
        [put("map_open",1), OPEN_MAP, *survey_routes()], 0.25)
    trip_notice = report("trip", "The main circuit tripped",
        "The valve has closed and all insulated buildings lose two heat levels. Switch off Overdrive and let stress "
        f"drop to {RESET}%, or {RELAY_RESET}% if you have built a Signal Relay. Keep the Generator running. "
        "Once it cools, the circuit reconnects and your current job resumes.")
    for welded,limit in ((0,TRIP),(1,WELDED_TRIP)):
        add("trip/"+str(limit), [at_least("plan",1), eq("tripped",0), eq("welded",welded), stress_check(4,limit)],
            [put("tripped",1), put("trips",1,1), change("trip"), trip_notice])
    restore = [put("tripped",0), change("trip",True)]
    add("reconnect", [eq("tripped",1)],
        [first_match(("Signal Relay", [constructed(places[RELAY]),stress_check(5,RELAY_RESET)], restore),
                     ("Main Valve", [stress_check(5,RESET)], restore))])

    def receive_crew(spec):
        return ([change(spec["reward"])] + [arrive(n,role) for role,n in spec["people"].items()]
                + [change_resource(resources[name].hex(),n) for name,n in spec["cargo"].items()])

    def second_party(crew, number):
        other, = (name for name in ADVANCE_CREWS if name!=crew)
        spec = ADVANCE_CREWS[other]
        key = "advance/"+other
        uid = identity("quest/"+key)
        opening_quests[crew] = dict(quest=uid, crew=other, building=places[spec["warm"]])
        available = [eq("advance_crew",number)]
        requirements = [constructed(places[RELAY])]+warm_station(spec["warm"])
        goal = dict(kind="checks",label="Reception",text=f"Receive {spec['label']}",
            description=f"Keep the Relay built and make {spec['description']} Liveable or warmer. "
                        "The Generator must be running. The crew comes in automatically.")
        quests.append(writer.build("NI Faultline "+key,uid,"The other advance party",[goal],identity,localize,
                                   "Faultline/Quest/"+key,OPENING_HOURS*SCAN))
        add(key,available+requirements,[progress_quest(uid,"Reception")])
        arrived = [put("advance_crew",0),*receive_crew(spec),
                   report(key+"/arrive","The second party is home",
                          f"The relay lights brought {spec['label']} into the city.")]
        events.append(completed_event("NI Faultline Received "+other,identity("event/receive/"+other),
            identity("trigger/receive/"+other),uid,[scope]+available,arrived))
        return [put("advance_crew",number),start_quest(uid),
                after(key+"/timeout",OPENING_HOURS*SCAN,[guarded([scope]+available,[put("advance_crew",0)])])]

    def whiteout(key, active, lead, advance):
        live = active+[eq("whiteout",1)]
        launch = [put("whiteout",1),change("whiteout")]
        rescue_quests[lead] = {}
        for line,spec in RELIEF_LINES.items():
            route = key+"/rescue/"+line
            uid = identity("quest/"+route)
            hours = 6 if line==lead else 8
            delay = 0 if line==lead else 2
            eligible = [eq("ridge_lift",1)] if line=="lift" else []
            gate = line+"_open"
            counter = line+"_hours"
            condition = live+[eq(gate,1),eq(line+"_saved",0)]+eligible
            rescue_quests[lead][line] = dict(quest=uid,hours=hours,delay=delay)
            goal = dict(kind="checks",label="WarmHours",quantity=hours,
                text=f"Keep the {spec['name'].lower()} route heated for {hours} hours",
                description=f"Liveable or warmer: {spec['services']}. Keep the Generator on. "
                            "Cold hours pause the counter. The front lasts eighteen hours in total.")
            quests.append(writer.build("NI Faultline "+route,uid,spec["name"]+" rescue", [goal],
                                       identity,localize,"Faultline/Quest/"+route,WHITEOUT_HOURS*SCAN-delay*SCAN))
            starting = guarded([scope]+live+eligible+[eq(gate,0)],[put(gate,1),start_quest(uid)])
            launch.append(after(route+"/open",delay*SCAN,[starting]) if delay else starting)
            add(route+"/heat",condition+[at_most(counter,hours-1)]+district_ready(line),
                [put(counter,1,1),progress_quest(uid,"WarmHours")])
            arrivals = [arrive(n,role) for role,n in spec["households"].items()]
            arrivals += [change_resource(resources[name].hex(),n) for name,n in spec.get("cargo",{}).items()]
            events.append(completed_event("NI Faultline "+route,identity("event/"+route),identity("trigger/"+route),
                uid,[scope]+live+[eq(line+"_saved",0)],
                [put(line+"_saved",1),put("convoy_returned",1),change(spec["reward"])]+arrivals))

        choice = [scope]+live+[eq("reserve_used",0)]
        options=[]
        for option,(line,spec) in enumerate(RELIEF_LINES.items(),1):
            checks = choice+can_pay(spec["relief"])
            if line=="lift":
                checks += [eq("ridge_lift",1)]
            options.append((f"Fire the {spec['name'].lower()} boilers",
                f"{budget(spec['relief'])}. One extra heat level for this route’s buildings until the front clears.",
                checks,[guarded(checks,[put("reserve_used",option)]+pay(spec["relief"])+[change("boost_"+line)])]))
        options.append(("Keep the reserve","Rely on the city’s heating network.",choice,[guarded(choice,[put("reserve_used",3)])]))
        orders = scene(key+"/reserve","Reserve steam", "Only one emergency boiler can take the spare fuel. Use the temperature overlay to see which district needs it.",options,True)
        launch.append(after(key+"/reserve/prompt",2*SCAN,[guarded(choice,[orders])]))

        accounts = (
            ("Both crews made it", "The clinic sledges came in under the lift bell. Both crews have a place in the Basin.", [eq("clinic_saved",1),eq("lift_saved",1)]),
            ("The clinic came through", "The medics and families are warm. The lift crew did not reach the city.", [eq("clinic_saved",1)]),
            ("The lift crew came through", "The engineers reached shelter. The clinic sledges did not make it down.", [eq("lift_saved",1)]),
            ("The roads are closed", "Neither crew made it through before the front closed the pass.", []),
        )
        outcome = first_match(*[(title,checks,[report(key+"/rescue/outcome/"+str(i),title,body)])
                                for i,(title,body,checks) in enumerate(accounts)])
        finish = [put("whiteout",2),change("whiteout",True),
                  guarded([eq("reserve_used",1)],[change("boost_clinic",True)]),
                  guarded([eq("reserve_used",2)],[change("boost_lift",True)]),outcome]
        finish += [guarded([eq("convoy_returned",1)],[put("kept",1,1),mood("Hope rise - moderately")])]+advance
        add(key+"/rescue/clear",live+[eq("clinic_saved",1),
            either([eq("ridge_lift",0),eq("lift_saved",1)])],finish)
        return launch+[after(key+"/whiteout/end",WHITEOUT_HOURS*SCAN,[guarded([scope]+live,finish)])]

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
            first_crew = plan.get("first_crew")
            if first_crew:
                crew = ADVANCE_CREWS[first_crew]
                goals.append(dict(kind="checks",label="Reception",text=f"Receive {crew['label']}",
                    description=f"Make {crew['description']} Liveable or warmer and finish the Signal Relay. "
                                "Keep the Generator running. The relay guides the party in automatically."))
                add(key+"/receive",active+[eq("stroke",0)]+hardware+warm_station(crew["warm"]),
                    [put("stroke",1),progress_quest(uid,"Reception")])
            calibration=plan.get("signal")
            if calibration:
                low,high=calibration
                goals.append(dict(kind="checks",label="Stroke1",text=f"Send a signal at {low}â€“{high}% stress",
                    description="Complete construction. Select the Generator, leave it running and use Overdrive to raise "
                                f"the stress gauge to {low}â€“{high}%. The relay sends the signal within 15 game minutes. "
                                "Switch off Overdrive when the objective ticks."))
                add(key+"/calibrate",active+[eq("tripped",0),eq("stroke",0),running]+hardware+
                    [stress_check(4,low),stress_check(5,high)],
                    [put("stroke",1),progress_quest(uid,"Stroke1")],SCAN/4)
            district = plan.get("district")
            if district:
                spec = RELIEF_LINES[district]
                goals.append(dict(kind="checks",label="Inspections",quantity=LINE_INSPECTIONS,
                    text=f"Pass {LINE_INSPECTIONS} hourly heat inspections",
                    description=f"Liveable or warmer: {spec['services']}. Keep the Generator running. "
                                "Use Heat view and add Steam Hubs, Heaters or insulation. Cold readings don't count."))
                add(key+"/inspect",active+[at_most("inspections",LINE_INSPECTIONS-1)]+district_ready(district),
                    [put("inspections",1,1),progress_quest(uid,"Inspections")])
            watch = plan.get("watch")
            if watch:
                spec = RELIEF_LINES[watch["district"]]
                ready = district_ready(watch["district"])
                saving = 4 if watch["district"]=="clinic" else 3
                goals.append(dict(kind="checks",label="Watch",quantity=WATCH_LEGS,
                    text="Deliver three coal loads to Broken Mile",
                    description=f"Liveable or warmer: {spec['services']}. Keep {watch['reserve']+watch['coal']} coal "
                                "available. Convoys leave and arrive automatically when the stops are heated. "
                                f"A Coal Magazine saves {MAGAZINE_SAVING} coal per load. "
                                f"The district pact cuts the {watch['travel']}-hour journey by {saving} hours."))
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
                arrived = [put("leg",1,1),guarded([eq("leg",1)],outage),progress_quest(uid,"Watch")]
                departures = []
                for has_pact in (1,0):
                    for covered in (1,0):
                        cost = watch["coal"]-covered*MAGAZINE_SAVING
                        trip = watch["travel"]-has_pact*saving
                        checks = [eq(spec["pact"],has_pact),affordable(coal,cost+watch["reserve"])]
                        if covered:
                            checks.append(constructed(places[MAGAZINE]))
                        actions = [put("shipment",2)]+pay({"Coal":cost})+[
                            after(f"{key}/travel/{has_pact}/{covered}",trip*SCAN,
                                [guarded([scope]+active+[eq("shipment",2)],[put("shipment",4)])])]
                        departures.append((f"Convoy {has_pact}/{covered}",checks,actions))
                add(key+"/watch",waiting+[clear,eq("shipment",0)]+ready,[first_match(*departures)])
                add(key+"/arrival",waiting+[clear,eq("shipment",4)]+ready,[put("shipment",0)]+arrived)
            hold=plan.get("hold")
            if hold:
                hours,low,high,reserve=(hold[field] for field in ("hours","low","high","reserve"))
                goals.append(dict(kind="checks",label="PressureTest",quantity=hours,
                    text=f"Record {hours} test hours at {low}â€“{high}% stress",
                    description=f"Build the Valve Works first. Keep the Generator running at {low}â€“{high}% stress and "
                                f"hold {reserve} coal in stock. Check the counter each game hour. Build parts while the test runs. "
                                "Recorded hours carry forward if stress leaves the band."))
                readiness=[running,eq("tripped",0),stress_check(4,low),stress_check(5,high),affordable(coal,reserve)]+hardware
                add(key+"/pressure-test",active+[at_most("hold_hours",hours-1)]+readiness,
                    [put("hold_hours",1,1),progress_quest(uid,"PressureTest")])
            pledge = plan.get("pledge")
            if pledge:
                goals.append(dict(kind="checks",label="Pledge",text="Commission the parts" if hold else "Complete the dispatch",
                    description="Set aside "+budget(pledge)+". Confirm the dispatch order when it opens."+
                                (" It opens after the pressure test." if hold else " The tracker updates when the load arrives.")))
                checks = [eq("pledged",0)] + hardware
                if hold:
                    checks.append(eq("hold_hours",hours))
                checks, actions = shipment(key,active,checks,"Works commissioning" if hold else "Dispatch order",pledge,
                    2 if hold else 4 if plan.get("lead") else 8,
                    [put("pledged",1),progress_quest(uid,"Pledge")],go="Install parts" if hold else "Send supplies")
                add(key+"/pledge",checks,actions)
            quests.append(writer.build("NI Faultline "+key,uid,act["title"]+" â€” "+plan["title"],goals,
                                       identity,localize,"Faultline/Quest/"+key,act["days"]))
            advance = [put("phase",phase+1), put("plan",0), change(plan["profile"],True),
                       guarded([eq("tripped",1)],[put("tripped",0),change("trip",True)])]
            if watch:
                advance.append(guarded([at_least("leak",1),at_most("leak",2)],[change("leak",True),put("leak",3)]))
            success = advance+[put("kept",1,1),mood("Hope rise - moderately")]
            if flag:=plan.get("flag"):
                success.append(put(flag,1))
            if district:
                success.append(put(RELIEF_LINES[district]["pact"],1))
            if profile:=plan.get("persistent"):
                success.append(change(profile))
            if first_crew:
                success.extend(receive_crew(crew)+second_party(first_crew,number))
            success += [change_resource(resources[k].hex(),n) for k,n in plan.get("cargo",{}).items()]
            success += [arrive(n,role) for role,n in plan.get("people",{}).items()]
            success.append(report(key+"/success",act["title"],plan["report"]))
            failure = advance+[mood("Discontent rise - moderately"),report(key+"/miss","The line went quiet",act["failure"])]
            timeout = active
            if lead:=plan.get("lead"):
                success = [teach(guid,"whiteout"),*whiteout(key,active,lead,advance)]
                timeout = active+[eq("whiteout",0)]
            events.append(completed_event("NI Faultline Cleared "+key,identity("event/clear/"+key),
                          identity("trigger/clear/"+key),uid,[scope]+active,success))
            start = [put("plan",number), put("stroke",0), put("shipment",0), put("scout_returned",0), change(plan["profile"]),
                     start_quest(uid), after(key+"/deadline",act["days"],[guarded([scope]+timeout,failure)])]
            lesson = {(1,1):"first_relief", (1,2):"first_relief", (2,1):"refit", (2,2):"refit", (3,2):"survey",
                      (6,1):"watch", (6,2):"watch", (7,1):"charter", (7,2):"charter"}.get((phase,number))
            lesson=act.get("lesson",lesson)
            if lesson:
                start.append(teach(guid,lesson))
            start[:0]=[put(flag,0) for flag in act.get("clears",())]
            if hold:
                start[:0]=[put("hold_hours",0)]
            if watch:
                start[:0]=[put("leg",0),put("hours",0),put("leak",0),put("watch_kept",0)]
            if pledge:
                start[:0]=[put("pledged",0)]
            if district:
                start[:0]=[put("inspections",0)]
            choose = [scope]+phase_at(phase,0)+[eq("ending",0)]
            options.append((plan["title"],plan["preview"],choose+visible,[guarded(choose+visible,start)]))
            missions.append(dict(phase=phase,plan=number,quest=uid,deadline=act["days"],goals=goals,
                                 title=plan["title"],profile=plan["profile"],signal=calibration,
                                 requires=plan.get("requires",()),flag=plan.get("flag"),watch=watch,pledge=pledge,
                                 hold=hold,district=district,lead=lead,first_crew=first_crew))

        fallback=next(option for option,plan in zip(options,act["plans"]) if not plan.get("requires"))
        offer = scene(f"briefing/{phase}",act["title"],act["story"]+
                      f"\n\n{act['days']} days to complete the job. Default after one day: {fallback[0]}.",options)
        delivery = [offer,after(f"default/{phase}",1,fallback[3])]
        add(f"briefing/{phase}",phase_at(phase,0)+[eq("offered",phase-1),eq("ending",0)],
            [put("offered",phase)]+delivery,0.25)

    finish = phase_at(len(ACTS)+1,0)+[eq("ending",0)]
    replay_id = identity("cinematic/city-replay")
    replay_ready = [scope,at_least("ending",1),eq("replay_started",0)]
    replay = guarded(replay_ready,[put("replay_started",1),END_CITY+bytes.fromhex(replay_id)])

    def epilogue(key, title, text):
        return scene(key,title,text,[("See how the city grew","Finish Faultline and play the city replay.",
                                     replay_ready,[replay])],True)

    endings=[]
    accord_ready = [eq("final",1),eq("charter",1),eq("clinic_saved",1),eq("lift_saved",1),at_most("trips",1)]
    ordinary_ending = either([eq("final",0),eq("charter",0),eq("clinic_saved",0),eq("lift_saved",0),
                              at_most("kept",len(ACTS)-3),at_least("trips",2)])
    for kept in range(len(ACTS)-2,len(ACTS)+1):
        title = "The Basin Accord"
        text = ("The shelter crews signed their names to the charter. Households and wards gain one insulation level as "
                "the new fittings go in. You brought both crews home and saw the main through the winter with at most one trip."
                f"\n\nJobs completed: {kept} of {len(ACTS)}.")
        add(f"accord/{kept}",finish+accord_ready+[eq("kept",kept)],
            [put("ending",3),put("ending/kept",kept),change("accord")],0.25)
        endings.append(([eq("ending",3),eq("ending/kept",kept)],epilogue(f"accord/{kept}",title,text)))
    outcomes = (
        (0, "A Light in the Basin", "The local shelters have a place to come home to. The distant line never answered."),
        (1, "The Signal Holds", "Edith reads the answers into the record. There is a winter line now, and people on both ends intend to keep it."),
    )
    for final,title,story in outcomes:
        for kept in range(len(ACTS)+1):
            text = f"{story}\n\nJobs completed: {kept} of {len(ACTS)}."
            add(f"end/{final}/{kept}",finish+[ordinary_ending,eq("final",final),eq("kept",kept)],
                [put("ending",1+final),put("ending/kept",kept)],0.25)
            endings.append(([eq("ending",1+final),eq("ending/kept",kept)],epilogue(f"end/{final}/{kept}",title,text)))
    done=phase_at(len(ACTS)+1,0)+[at_least("ending",1)]
    final_report = [guarded(checks,[dialog]) for checks,dialog in endings]+[after("end-replay",1,[replay])]
    for ending in (1,2,3):
        key=f"dawn/{ending}"
        ready=done+[eq("ending",ending)]
        add(key,ready+[eq("offered",len(ACTS))],
            [put("offered",len(ACTS)+1)]+final_report,0.25)
    return events, dialogs, quests, dict(scenario=scenario,missions=missions,scan_hours=1,trip=TRIP,
        welded_trip=WELDED_TRIP,reset=RESET,watch_legs=WATCH_LEGS,leak_repair=LEAK_REPAIR,
        buildings=structures,relay_reset=RELAY_RESET,magazine_saving=MAGAZINE_SAVING,
        rescue_quests=rescue_quests,whiteout_hours=WHITEOUT_HOURS,line_inspections=LINE_INSPECTIONS,
        opening_quests=opening_quests,opening_hours=OPENING_HOURS,
        replay=replay_id,
        lessons={key:lesson_id(guid,key).hex() for key in LESSONS},
        modifiers={key:value for key,value in modifiers.items() if key.startswith("faultline/")})
