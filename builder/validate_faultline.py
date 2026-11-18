"""Drive decoded Faultline events through each refit and ending."""
from math import isclose
from faultline_buildings import DEFINITIONS, RELIEF_DISPATCH, VALVE_WORKS
from tools.native_binary import Cursor, string
from tools.scenario_model import World
from tools.housing_schema import BEACON
from tools.story_schema import DEFAULT
from winter_road_maps import SITES


PREFIX = "NI/Faultline/"
HOUR = 1/24


def audit_construction_gate(prefab, scenario):
    from faultline_buildings import component
    cursor=Cursor(prefab,component(prefab,"Building"))
    cursor.take(16*cursor.count(8))
    # The Building component has a placement vector, 35 fixed bytes, three
    # preceding vectors and the availability vector. Reading the latter at
    # its actual boundary catches shifts even when its bytes occur intact.
    cursor.take(35)
    assert cursor.take(12)==bytes(12), 'Missing empty vectors before construction availability'
    assert cursor.u32()==1 and cursor.string()=="FrostpunkScenarioRequirement"
    assert cursor.take(17)==bytes(17) and cursor.guid()==scenario and not cursor.boolean()
    assert cursor.f32()==1.5, 'Construction requirements overrun the native footer'


def audit_assets(stock_catalog, catalog, stock_messages, messages, templates, campaign, resources):
    from faultline_buildings import building_table, component
    from faultline_tutorial import MESSAGE, donor
    old_begin,old_count,old_end,old_rows=building_table(stock_catalog)
    begin,count,end,rows=building_table(catalog)
    assert count-old_count==len(templates)==len(campaign["buildings"])==len(DEFINITIONS)
    assert begin==old_begin and catalog[:begin]==stock_catalog[:begin]
    assert catalog[begin+4:old_end]==stock_catalog[begin+4:old_end]
    assert catalog[end:]==stock_catalog[old_end:]
    assert {name:rows[name] for name in old_rows}==old_rows
    for spec in campaign["buildings"]:
        prefab=templates[spec["path"]]
        category=old_rows[spec["native"]][0]
        assert rows[spec["name"]]==(category,spec["guid"],True)
        assert prefab[:16].hex()==spec["guid"]
        audit_construction_gate(prefab,campaign["scenario"])
        price=Cursor(prefab,component(prefab,"BuildingEconomics"))
        actual={price.guid():price.u32() for _ in range(price.count(4))}
        assert actual=={resources[key]:n for key,n in spec["price"].items()}
        if "radius" in spec:
            heat=Cursor(prefab,component(prefab,"Heater"))
            assert heat.boolean() and heat.count(2)==1 and heat.string()=="Level range0"
            assert heat.take(4)==bytes(4) and heat.f32()==spec["radius"] and heat.u32()==0
            assert heat.count(2)==1 and heat.guid()==resources["Coal"] and heat.f32()==spec["coal_per_hour"]
        elif "coal_capacity" in spec:
            depot=Cursor(prefab,component(prefab,"UndesignatedResourceDepot"))
            assert depot.count(5)==1 and depot.guid()==resources["Coal"] and depot.u32()==spec["coal_capacity"]
        else:
            panel=Cursor(prefab,component(prefab,"Production"))
            assert panel.count(2)==2 and panel.guid()!=panel.guid()
            assert prefab.count(string(spec["interior"]))==1
            name=spec["name"]
            assert prefab.count(string(f"@Mods/NewIndustry/Faultline/Buildings/{name}/Name"))==1
            assert "PrefabFractory".encode() not in prefab
    from validate_endless import appended
    cards=campaign["lessons"]
    reader=Cursor(appended(stock_messages,messages,"Tutorial","Main Narrative Line",len(cards)))
    prefix,description=donor(stock_messages)
    for key,uid in cards.items():
        assert reader.string()==MESSAGE and reader.string()=="NI Faultline "+key and reader.guid()==uid
        assert reader.take(len(prefix))==prefix and reader.string()==f"@Mods/NewIndustry/Faultline/Lessons/{key}/Title"
        assert reader.take(len(description))==description and reader.string()==f"@Mods/NewIndustry/Faultline/Lessons/{key}/Body"
    assert reader.position==len(reader.data)
    return dict(buildings=len(templates),tutorial_cards=len(cards))


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
    structures={row["name"]:row["guid"] for row in campaign["buildings"]}
    lessons=campaign["lessons"]
    assert len(missions)==19

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
                tick(w,9)
                assert w.world_map and w.placed_sites=={marker:uid for marker,uid,_,_ in SITES}
                assert w.revealed_sites=={("site",uid) for _,uid,_,_ in SITES}
                w=w.checkpoint()
                tick(w,6)
                w.return_scouts()
                w.return_scouts()
                assert w.progress[row["quest"]]["Scout"]==1
        return w

    played=set()
    for route in ((1,1,1,1,2,1,1,1,1), (2,2,2,2,3,2,2,2,2), (1,2,1,2,1,1,2,2,1)):
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
            elif phase==9:
                assert w.all(dialogs[briefing]["choices"][1]["conditions"])==(route[7]==2)
            if phase>=8:
                order,= (goal for goal in missions[phase,plan]["goals"] if goal["kind"]=="produce")
                w.produced[order["target"][0]]=order["quantity"]*5
            assert w.click(briefing, plan-1)
            lesson = {1:"gauge",2:"refit",6:"watch",7:"charter",8:"valve_orders",9:"dispatch_orders"}.get(phase)
            if lesson:
                assert w.lessons.count(lessons[lesson])==1
            if phase==3:
                assert w.lessons.count(lessons["survey"])==(plan==2)
            row=missions[phase,plan]
            profile=effects["faultline/"+row["profile"]]
            assert profile in w.modifiers and row["quest"] in w.active
            if phase>=8:
                order_id=order["target"][0]
                station=VALVE_WORKS if phase==8 else RELIEF_DISPATCH
                assert any(goal["kind"]=="build" and goal["target"]==[structures[station]] for goal in row["goals"])
                assert order["station"]==station
                wrong_order,= (goal["target"][0] for goal in missions[phase,3-plan]["goals"] if goal["kind"]=="produce")
                w.produced[wrong_order]=100
                w.step(HOUR)
                assert order_id in w.production_start[row["quest"]]
                assert not w.goal_met(row["quest"],next(g for g in quests[row["quest"]]["objectives"] if g["kind"]=="produce"))
            # Structural readiness alone cannot supply an opening pulse.
            if phase==1:
                w.stress=0.35
                w.step(HOUR)
                assert state(w,"stroke")==0
            # Pre-existing stock and completed city goals still cannot skip
            # the pressure sequence, and a shut-off Generator cannot pulse.
            w.generator=False
            w=fulfill_city(w,row)
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
                if phase==5:
                    w.buildings[structures["Signal Relay"]]=1
                    w.stress=(campaign["relay_reset"]-0.4)/100
                else:
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
                if phase==1 and index<=2:
                    assert w.lessons.count(lessons["cool" if index==1 else "relay"])==1
            if watch:=row["watch"]:
                w.stress=(watch["low"]+watch["high"])/200
                if plan==2:
                    # Building two magazines still applies exactly one saving.
                    w.buildings[structures["Coal Magazine"]]=2
                shipment=watch["coal"]-(campaign["magazine_saving"] if plan==2 else 0)
                supply=w.stock[coal]
                tick(w,watch["hours"]-1)
                assert state(w,"hours")==watch["hours"]-1 and state(w,"leg")==0
                w.stock[coal]=watch["reserve"]+shipment-1
                tick(w,1)
                assert state(w,"hours")==0 and state(w,"leg")==0
                w.stock[coal]=supply
                tick(w,watch["hours"])
                assert state(w,"leg")==1 and state(w,"leak")==1 and leak in w.modifiers
                assert w.stock[coal]==supply-shipment
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
                assert w.stock[coal]==supply-campaign["watch_legs"]*shipment
            if hold:=row["hold"]:
                w.stress=(hold["low"]+hold["high"])/200
                supply=w.stock[coal]
                tick(w,hold["hours"]-1)
                assert state(w,"hold_hours")==hold["hours"]-1 and row["quest"] in w.active
                w.stock[coal]=hold["reserve"]-1
                tick(w,1)
                assert state(w,"hold_hours")==0
                w.stock[coal]=supply
                tick(w,hold["hours"])
                assert state(w,"hold_hours")==hold["hours"] and w.stock[coal]==supply
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
        assert state(w,"ending")==2 and state(w,"kept")==9 and state(w,"convoy_returned")==1
        assert w.open.count(names["end/1/9"])==1
        assert effects['faultline/'+('ridge_fitters' if route[-1]==2 else 'ridge_medics')] in w.modifiers
    assert played==set(missions)

    # A city that misses every deadline can still finish, including when the
    # player leaves the briefing alone. Unsettled plans cannot replay rewards.
    failed=world()
    failed.start()
    failed.generator=False
    failed.run(80,False)
    assert state(failed,"ending")==1 and state(failed,"kept")==0
    assert not failed.active and not failed.modifiers
    assert names["end/0/0"] in failed.open
    accord=world()
    accord.start()
    accord.variables.update({PREFIX+"phase":10,PREFIX+"offered":9,PREFIX+"kept":7,PREFIX+"final":1,
                            PREFIX+"charter":1,PREFIX+"convoy_returned":1})
    accord.run(1,False)
    assert state(accord,"ending")==3 and names["accord/7"] in accord.open
    assert accord.modifiers=={effects["faultline/accord"]}
    settled=world()
    settled.variables.update({PREFIX+"phase":8,PREFIX+"offered":7,PREFIX+"ending":3})
    settled.start()
    settled.run(5,False)
    assert not settled.active and not settled.open and not settled.sequences
    unfinished=world()
    unfinished.variables.update({PREFIX+"phase":8,PREFIX+"offered":7,PREFIX+"ending":0})
    unfinished.start()
    unfinished.run(2,False)
    assert state(unfinished,"plan")==1 and names["briefing/8"] in unfinished.open
    for scenario in (DEFAULT,story["scenario"],story["winter_road"]["scenario"]):
        other=world(scenario)
        other.start()
        other.buildings[BEACON]=1
        other.run(2,False)
        assert not any(key.startswith(PREFIX) for key in other.variables)
        assert not any(uid in other.open for uid in names.values()) and not other.lessons
    return dict(plans=len(played),endings=3,trip_recovery=True,stress_is_spent=True,deadlines_continue=True,
                route_unlocks_verified=True,old_saves_isolated=True,watch_resets=True,leak_repairs=True,
                pledge_paid_once=True,cinematic_signal_and_fallback=True,lesson_timing=True,
                relay_recovery=True,nonstacking_fuel_saving=True,order_baselines=True,
                pressure_hold_resets=True,convoy_route_guards=True)
