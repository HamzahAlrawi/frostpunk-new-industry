"""Compile an isolated campaign and its overlapping, one-time side projects."""
from city_mastery import building_ids
from tools.convoy_schema import arrive
from tools.housing_schema import ACTIVATE, BEACON, HOME, LIVEABLE, OPEN_MAP, RETURN, validate
from tools.mission_schema import MissionWriter, completed_event
from tools.native_binary import entry, f32, u32
from tools.native_scenario import (affordable, amount, apply_modifier, change_resource, compare, delayed,
    dilemma, equals, event, guarded, integer, predefined, progress_quest, set_variable, start_quest, typed, variable)
from winter_road_story import AFTERMATH, CHAPTERS, PROJECTS
from winter_road_maps import (LEGACY_POINTS, LEGACY_TEMPLATES, REVEAL, SITES, beacon_exists,
    reveal_site, select_name, validate_native_map_effects)

PREFIX="NI/WinterRoad/"
LEGACY=("NI/Lifeline/chapter","NI/LastSignal/act")


def build(source, buildings, techinfo, resources, guid, scenario, switchback, bonuses, localize, dt, qt):
    identity=lambda key:guid("winter-road/"+key).hex()
    quest_data=(source/"configs/frostpunkquestsconfig.bin").read_bytes()
    native_events=(source/"configs/frostpunkgameeventsconfig.bin").read_bytes()
    validate(quest_data,native_events)
    validate_native_map_effects(native_events)
    blueprints=(source/"configs/frostpunkblueprintsconfig.bin").read_bytes()
    native_effects=(source/"configs/frostpunkeffectsconfig.bin").read_bytes()
    writer=MissionWriter(quest_data,qt)
    places={name:value.hex() for name,value in building_ids(buildings).items()}
    techs={row["name"]:row["guid"] for row in techinfo}
    resources={name:value.hex() for name,value in resources.items()}
    def scenario_is(uid):
        return typed("FrostpunkCurrentScenarioCheckExpression")+bytes.fromhex(uid)+b"\0"
    scoped=typed("BooleanOperationExpression")+u32(1)+u32(2)+scenario_is(scenario)+scenario_is(switchback)
    running=typed("FrostpunkGeneratorIsActiveExpression")
    events,dialogs,quests,main_meta,side_meta=[],[],[],[],[]

    def blueprint(name):
        marker=b"\1"+typed(name)
        assert blueprints.count(marker)==1,name
        at=blueprints.index(marker)+len(marker)
        return blueprints[at:at+16].hex()

    recipes={
        "meals":[blueprint("Canteen_FoodRations_"+name) for name in ("standard","better","soup","biowaste","gruel")]+
            [guid("recipe/"+key).hex() for key in ("FuelledStockpots","SlowSimmeredBroth","PressureKitchens")],
        "automatons":[blueprint(name) for name in ("Automatons","CheaperAutomatons","Automatons_upgraded",
            "CheaperAutomatons_upgraded","Automatons_upgraded2","CheaperAutomatons_upgraded2")],
    }

    def eq(key,value):return equals(PREFIX+key,value)
    def put(key,value,op=0):return set_variable(PREFIX+key,value,op)
    def gate(chapter,plan):return [scoped,eq("chapter",chapter),eq("plan",plan)]
    def require(cost):return [affordable(resources[name],n) for name,n in cost.items()]
    def supplies(items,sign=1):return [change_resource(resources[name],n*sign) for name,n in items.items()]
    def budget(cost):return ", ".join(f"{n:,} {name.lower()}" for name,n in cost.items())
    def after(key,days,actions):return delayed(identity("timer/"+key),days,actions)
    def arrive_all(groups):return [arrive(n,role) for role,n in groups.items()]
    def modifier(key):return apply_modifier(bonuses["road/"+key])
    def remove(key):return typed("FrostpunkRemoveModifierEffect")+bytes.fromhex(bonuses["road/"+key])

    def mood(name):
        pattern=b"\1"+typed("GOLD [Common] "+name)
        at=native_effects.index(pattern)+len(pattern)
        return predefined(native_effects[at:at+16].hex())

    def fire(key,conditions,actions,clock=0.25):
        events.append(event("NI Winter Road "+key,identity("event/"+key),identity("trigger/"+key),
            conditions,actions,clock))

    def resolve_objectives(rows):
        result=[]
        for source in rows:
            goal=dict(source);kind=goal["kind"]
            if kind in ("build","operate"):goal["target"]=[places[name] for name in goal.pop("names")]
            if kind=="research":goal["target"]=techs[goal.pop("tech")]
            if kind=="produce":goal["target"]=recipes[goal.pop("recipe")]
            if kind=="warm":goal["target"]=[HOME,LIVEABLE]
            if kind=="scout":goal.update(kind="checks",label="Scout",input="scout")
            result.append(goal)
        return result

    def scene(key,title,story,options,small=False):
        uid=identity("dialog/"+key)
        loc="LastSignal/WinterRoad/"+key
        choices=[dt.choice("NI Road "+key+"/"+str(index),identity(f"choice/{key}/{index}"),label,info,
            visible,[guarded(checks,actions)] if checks else actions,localize,loc+"/"+str(index))
            for index,(label,info,visible,checks,actions) in enumerate(options)]
        dialogs.append(dt.build("NI Winter Road "+key,uid,title,story,choices,localize,loc,small,
                                subtitle="The Last Signal: Winter Road"))
        return dilemma(uid)

    def report(key,title,story,actions=(),checks=()):
        return scene(key,title,story,[("Continue","Return to the city.",[],list(checks),list(actions))],True)

    def scout_event(key,conditions,quest):
        body=entry("NI Winter Road Scout "+key,identity("event/scout/"+key))+b"\0\1"+f32(1)+u32(1)
        body+=typed(RETURN)+bytes.fromhex(identity("trigger/scout/"+key))+b"\0\0"
        actions=[put("scouted",1),progress_quest(quest,"Scout")]
        events.append(body+u32(len(conditions))+b"".join(conditions)+u32(len(actions))+b"".join(actions))

    beacon=entry("NI Winter Road Beacon",identity("event/beacon"))+b"\0\1"+f32(1)+u32(1)
    beacon+=typed(ACTIVATE)+bytes.fromhex(identity("trigger/beacon")+BEACON)+u32(0)
    beacon_checks=[scoped,compare(variable(PREFIX+"chapter"),4,integer(1)),eq("map_open",0)]
    beacon_actions=[put("map_open",1),OPEN_MAP]
    events.append(beacon+u32(len(beacon_checks))+b"".join(beacon_checks)+u32(len(beacon_actions))+b"".join(beacon_actions))
    # A finished Beacon can predate the patch. The periodic fallback observes
    # it directly instead of relying on a construction notification replay.
    discover = [reveal_site(uid) for _,uid,_,_ in SITES]
    legacy = [select_name("DefaultRandomizationPoint_"+point, REVEAL) for point in LEGACY_POINTS]
    legacy.extend(reveal_site(uid) for uid in LEGACY_TEMPLATES)
    fire("chart Frostland",[scoped,beacon_exists(),eq("frostland_charted",0)],[
        put("frostland_charted",1),put("map_open",1),OPEN_MAP,
        guarded([scenario_is(switchback)], discover),
        guarded([scenario_is(scenario)], legacy),
    ])

    def resolution(key,check,quest,days,goals,cost,success,miss,watch=0,slot="main"):
        state=lambda key:eq(slot+"/"+key,0)
        current=lambda key:variable(PREFIX+slot+"/"+key)
        assign=lambda key,n,op=0:put(slot+"/"+key,n,op)
        readiness=require(cost)+([running+b"\0"] if slot!="side" else [])
        label="Watch" if watch else "Supplies"
        if cost or watch:
            description=(f"Pass {watch} inspections in a row. Every six game hours the Generator must be on and the listed reserves must be intact. A missed inspection restarts the count. "
                         if watch else "")
            description+=f"Set aside {budget(cost)}. Payment is charged once, at completion."
            goals.append(dict(kind="checks",label=label,quantity=1,
                text=f"Pass {watch} reserve inspections" if watch else "Ready "+budget(cost),description=description))
            poll=check+[state("ready")]
            if watch:
                fire("watch/"+key,poll+readiness,[assign("streak",1,1),guarded(
                    [eq(slot+"/streak",watch)],[assign("ready",1),progress_quest(quest,label)])])
                reset=[compare(current("streak"),4,integer(1))]
                fire("watch-reset/"+key,poll+reset,[*[
                    guarded([compare(integer(n-1),4,amount(resources[name]))],[assign("streak",0)])
                    for name,n in cost.items()],guarded([running+b"\1"],[assign("streak",0)])])
            else:
                fire("ready/"+key,poll+readiness,[assign("ready",1),progress_quest(quest,label)])
        if any(goal.get("input")=="scout" for goal in goals):
            scout_event(key,check+[eq("scouted",0)],quest)
        events.append(completed_event("NI Winter Road Cleared "+key,identity("event/clear/"+key),
            identity("trigger/clear/"+key),quest,check,[assign("cleared",1)]))
        settle=check+[eq(slot+"/cleared",1)]+readiness
        fire("settle/"+key,settle,success)
        return [assign("cleared",0),assign("ready",0),assign("streak",0),start_quest(quest),
                after("deadline/"+key,days,[guarded(check,[guarded(settle,success),guarded(check,miss)])])]

    side_offers={}
    for index,project in enumerate(PROJECTS,1):
        key="project/"+project["key"];uid=identity("quest/"+key)
        active=[scoped,eq("side",index)]
        gate_offer=[scoped,eq("chapter",project["at"]),eq("side",0),eq(key+"/answered",0)]
        done=report(key+"/complete",project["title"],project["finish"])
        failed=report(key+"/missed",project["title"],"The volunteers return without the promised work. The main campaign continues.")
        goals=resolve_objectives(project["goals"])
        success=[put("side",0),put(project["flag"],1)]+supplies(project["cost"],-1)
        success+=supplies(project["reward"])+arrive_all(project.get("people",{}))
        if project["key"]=="school":success.append(modifier("school"))
        success.append(done)
        start=resolution(key,active,uid,project["days"],goals,project["cost"],success,[put("side",0),failed],slot="side")
        title=project["title"]
        options=[("Accept the project",f"{project['days']} days. Set aside {budget(project['cost'])}.",[],gate_offer,
                  [put(key+"/answered",1),put("side",index)]+start),
                 ("Give it a pass","No cost. Continue the main story.",[],gate_offer,[put(key+"/answered",1)])]
        offer=scene(key,title,project["story"]+"\n\nOptional project. Your main objective stays active.",options,True)
        side_offers[project["at"]]=(gate_offer,offer)
        quests.append(writer.build("NI Road "+key,uid,title,goals,identity,localize,
                                  "LastSignal/WinterRoad/"+key,project["days"]))
        side_meta.append(dict(key=project["key"],chapter=project["at"],quest=uid,deadline=project["days"],
                         goals=goals,cost=project["cost"],reward=project["reward"],index=index))

    for number,chapter in enumerate(CHAPTERS,1):
        options=[]
        for plan,path in enumerate(chapter["plans"],1):
            key=f"chapter/{number}/{plan}";uid=identity("quest/"+key)
            active=gate(number,plan)
            goals=resolve_objectives(path["goals"])
            advance=[put("chapter",number+1),put("plan",0),put("reading",1)]
            read_gate=gate(number+1,0)+[eq("reading",1)]
            leave=[put("reading",0)]
            cleanup=[remove("embargo")] if number==5 else [remove("exposed"),remove("braced")] if number==8 else []
            incoming=path["people"]
            loss=chapter.get("lost",{})
            text=path["report"]
            if incoming:text+=f"\n\n{sum(incoming.values())} people reach the city."
            if path["cargo"]:text+=" They bring "+budget(path["cargo"])+"."
            success=advance+cleanup+supplies(path["cost"],-1)+supplies(path["cargo"])+arrive_all(incoming)
            success+=[put("won/"+chapter["key"],plan),mood("Hope rise - moderately")]
            if path.get("flag"):success.append(put(path["flag"],1))
            if path.get("bonus"):success.append(modifier(path["bonus"]))
            report_title=("At the foot of the pass","The last sled","The keys change hands","A bearing in the dark",
                          "A store of our own","The names on the bell","Room at the table","The joint holds")[number-1]
            success.append(report(key+"/report",report_title,text,leave,read_gate))
            miss=advance+cleanup+arrive_all(loss)+[mood("Discontent rise - moderately"),report(
                key+"/missed","What the frost kept",chapter["failure"],leave,read_gate)]
            start=[put("plan",plan),put("scouted",0)]
            if number==1:start+=arrive_all({"workers":8,"engineers":4})+supplies(path["entry"])
            if path.get("sick"):start.append(arrive(path["sick"],"workers","ill"))
            if path.get("engineers"):start.append(arrive(path["engineers"],"engineers"))
            if number==5:start.append(modifier("embargo"))
            if number==8:
                start += [guarded([eq("repair",1)],[modifier("braced")]),guarded([eq("repair",0)],[modifier("exposed")])]
            if number==6:
                start.append(guarded([eq("reserve",1)],supplies({"Coal":160})))
            start+=resolution(key,active,uid,chapter["days"],goals,path["cost"],success,miss,path.get("watch",0))
            if number in side_offers:
                checks,prompt=side_offers[number]
                start.append(after(key+"/project",0.04,[guarded(checks,[prompt])]))
            visible=[eq(flag,1) for flag in path.get("requires",())]
            text=path["detail"]+" Supplies needed: "+budget(path["cost"])+"."
            options.append((path["title"],text,visible,gate(number,0)+[eq("reading",0)]+visible,start))
            title=chapter["title"]+" — "+path["title"]
            quests.append(writer.build("NI Road "+key,uid,title,goals,identity,localize,
                                      "LastSignal/WinterRoad/Quest/"+key,chapter["days"]))
            main_meta.append(dict(chapter=number,key=chapter["key"],plan=plan,quest=uid,goals=goals,cost=path["cost"],
                deadline=chapter["days"],flag=path.get("flag"),requires=list(path.get("requires",())),
                arrival=incoming,loss=loss,cargo=path["cargo"],watch=path.get("watch",0)))
        explanation=chapter["story"]+f"\n\nDeadline: {chapter['days']} game days from your choice. Keep the Generator on and hold the listed supplies until the work is complete."
        if number==1:explanation+=" Either choice admits eight workers and four engineers."
        if number==6:explanation+=" If you built the dispatch reserve, it releases 160 coal now."
        if number==8:explanation+=" The apprentice’s repair limits the insulation loss to one level."
        offered=scene(f"briefing/{number}",chapter["title"],explanation,options)
        if number==1:
            fire("start",[scoped,eq("chapter",0),*[equals(key,0) for key in LEGACY]],[put("chapter",1),
                after("opening",0.01,[offered])],None)
        else:
            fire(f"briefing/{number}",gate(number,0)+[eq("offered",number-2),eq("reading",0)],
                [put("offered",number-1),offered])

    ending=gate(9,0)+[eq("reading",0)]
    treaty={"Coal":210,"Food Rations":90}
    letters=[]
    for position,days,cargo,crew,title,description in (
        (1,2,{"Wood":130,"Coal":170},{},"The eastern sled","The first charter shipment unloads 130 wood and 170 coal at the old gate."),
        (2,5,{"Steel":100,"Raw Food":150},{},"The school shipment","The new charter brings 100 steel and 150 raw food to the city."),
        (3,8,{"Steam Cores":2,"Coal":200},{"engineers":6},"Room at the bench",
         "The last charter shipment brings two steam cores, 200 coal and six engineers. They ask for a place on the shift board."),
    ):
        key="cargo/"+str(position)
        letters.append(after(key,days,[guarded([scoped,eq("ending",1),eq(key,0)],
            [put(key,1)]+supplies(cargo)+arrive_all(crew)+[report(key,title,description)])]))
    open_gate=[eq("held",1),eq("crossed",1)]+require(treaty)
    signature=scene("treaty","The Road or the Wall?",
        "The settlement is alive. Sledges are waiting for the decision that will outlast this winter. "
        "If the crossing and the Long Night both held, you can reopen the pass, with three promised shipments. "
        "Or invest in the city’s own heating ring. The next three chapters follow the people still living beyond the gate.",
        [("Open the winter road","Spend 210 coal and 90 rations once. Three sledges arrive after two, five and eight days, alongside the next chapter.",open_gate,ending+open_gate,
          [put("chapter",99),put("ending",1)]+supplies(treaty,-1)+letters),
         ("Put the wards first","Spend 140 steel. Homes and medical buildings permanently gain one insulation level.",
          require({"Steel":140}),ending+require({"Steel":140}),[put("chapter",99),put("ending",2)]+supplies({"Steel":140},-1)+[modifier("home")]),
         ("Close the winter road","Decline the treaty and continue with the city’s own crews.",[],ending,
          [put("chapter",99),put("ending",3)])])
    # Only the scenario that signed the treaty can execute its cargo callbacks.
    fire("treaty",ending+[eq("offered",7)],[put("offered",8),signature])

    # Chapter 99 is the existing treaty save state. Use a separate phase
    # variable so an updated city can continue with its choice and cargo intact.
    aftermath=gate(99,0)+[compare(variable(PREFIX+"ending"),4,integer(1))]
    fire("aftermath/start",aftermath+[eq("aftermath",0)],[put("aftermath",1)])
    aftermath_meta=[]
    for number,chapter in enumerate(AFTERMATH,1):
        phase=aftermath+[eq("aftermath",number)]
        ready=phase+[eq("aftermath/plan",0)]
        advance=[put("aftermath",number+1),put("aftermath/plan",0)]
        options=[]
        for choice,path in enumerate(chapter["plans"],1):
            key=f"aftermath/{number}/{choice}"
            uid=identity("quest/"+key)
            active=phase+[eq("aftermath/plan",choice)]
            goals=resolve_objectives(path["goals"])
            success=advance+supplies(path["cost"],-1)+supplies(path["cargo"])+arrive_all(path["people"])
            success += [put("aftermath/kept",1,1),mood("Hope rise - moderately"),
                        report(key+"/report",chapter["title"],path["report"])]
            missed=advance+[mood("Discontent rise - moderately"),
                            report(key+"/missed",chapter["title"],chapter["failure"])]
            start=[put("aftermath/plan",choice)]+resolution(key,active,uid,chapter["days"],goals,
                        path["cost"],success,missed,path["watch"],slot="aftermath")
            options.append((path["title"],f"{path['detail']} Set aside {budget(path['cost'])}.",[],ready,start))
            quests.append(writer.build("NI Road "+key,uid,chapter["title"]+" — "+path["title"],goals,identity,localize,
                                      "LastSignal/WinterRoad/Quest/"+key,chapter["days"]))
            aftermath_meta.append(dict(chapter=number,plan=choice,quest=uid,goals=goals,cost=path["cost"],
                                       deadline=chapter["days"],watch=path["watch"],cargo=path["cargo"]))
        briefing=scene(f"aftermath/briefing/{number}",chapter["title"],chapter["story"]+
            f"\n\nThe job takes up to {chapter['days']} days. Choose a plan within two days, or the city will use “{options[0][0]}”.",
            options)
        fire(f"aftermath/briefing/{number}",ready+[eq("aftermath/offered",number-1)],
            [put("aftermath/offered",number),briefing,
             after(f"aftermath/default/{number}",2,[guarded(ready,options[0][4])])])

    outcomes=(
        "The winter road is marked as closed. The city has survived and can still change what happens in the basin.",
        "The lists show which promises held. Until the thaw, those shelters are the places people can still count on.",
        "The surveyors copied most of our names. Twice now, people on the other side of the ridge have answered the bell.",
        "The register that came down on the first sled now has a map folded inside it. Every shelter on that map answered its call.",
    )
    for kept,story in enumerate(outcomes):
        completed=report(f"aftermath/end/{kept}","Winter Road Complete",
            f"{story}\n\nPromises kept in the final three chapters: {kept} of {len(AFTERMATH)}. "
            "The campaign is complete. You can continue playing your city.")
        fire(f"aftermath/end/{kept}",aftermath+[eq("aftermath",len(AFTERMATH)+1),eq("aftermath/kept",kept)],
            [put("aftermath",99),completed])
    return events,dialogs,quests,dict(scenario=switchback,chapters=len(CHAPTERS),missions=main_meta,projects=side_meta,
        aftermath=aftermath_meta,
        finale=identity("dialog/treaty"),forecast=identity("forecast"),treaty=treaty,
        recipes=recipes,bonuses={key.removeprefix("road/"):value for key,value in bonuses.items() if key.startswith("road/")})
