"""Drive decoded Faultline events through each refit and ending."""
from math import isclose
from faultline_buildings import DEFINITIONS, RELIEF_DISPATCH, VALVE_WORKS
from tools.native_binary import Cursor, string
from tools.scenario_model import World
from tools.housing_schema import BEACON
from tools.story_schema import DEFAULT
from winter_road_maps import LEGACY_POINTS, LEGACY_TEMPLATES


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
        if "reconnect_at" in spec:
            assert string("FrostpunkHeaterComponentTemplate") not in prefab
            assert string("FrostpunkAbilitiesComponentTemplate") not in prefab
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
              "EaseCameraPosition", "SetCameraLookAt", "SetVisibleGameHUD", "PlaySound", "EmitSignal",
              "ShowSequenceMessage", "SetVisibleSequenceHUD")
    sizes = dict(zip(tracks,(12,0,2,43,38,21,2,34,16,None,4)))
    native_count=Cursor(native).u32()
    reader=Cursor(revised)
    films={f["shot"]:f["signal"] for f in campaign["films"].values()}
    assert reader.u32()==native_count+len(films)
    for shot in ("FirstCall","Fracture","NightWatch","DawnBasin","DawnSignal","DawnAccord"):
        assert shot in films
        assert reader.u8()==1 and reader.string()=="NI_Faultline_"+shot
        actions={}
        for _ in range(reader.count(16)):
            assert reader.u32()==1
            for _ in range(reader.count(8)):
                name=reader.string().removeprefix("SequenceAction")
                duration,start,extent=(reader.f32() for _ in range(3))
                assert duration>=0 and 0<=start<=extent<=10
                if name not in ("StoreCameraLocation","EmitSignal","SetCameraPosition","SetCameraLookAt",
                                "ShowSequenceMessage","SetVisibleSequenceHUD"):
                    assert isclose(start+duration,extent,abs_tol=1e-5)
                assert reader.take(5)==bytes(5)
                if name == "ShowSequenceMessage":
                    assert not reader.boolean()
                    payload = reader.string()
                    assert payload == "Mods/NewIndustry/Faultline/Cinematic/" + shot
                else:
                    payload = reader.take(sizes[name])
                actions.setdefault(name,[]).append((start,extent,payload))
        assert set(actions)==set(tracks)
        assert reader.u8()==1 and reader.string()=="GENRAL"
        assert reader.u32()==0 and reader.boolean() and not reader.boolean()
        assert (reader.f32(),reader.f32())==(5,45000)
        assert [row[2][0] for row in actions["Fade"]]==[0,1,0,1]
        assert [row[2] for row in actions["SetVisibleGameHUD"]]==[b"\1\0",b"\0\1"]
        target=actions["SetCameraPosition"][0][2][-16:]
        from faultline_cinematics import scene_anchor
        assert target==scene_anchor(city,"Generator_000")
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
    names = {d["name"].removeprefix("NI Faultline "):d["guid"] for d in dialogs.values()
             if d["name"].startswith("NI Faultline ")}
    quests = {q["guid"]:q for q in decoded["quests"]}
    missions = {(q["phase"],q["plan"]):q for q in campaign["missions"]}
    effects = campaign["modifiers"]
    leak = effects["faultline/leak"]
    coal = resource_ids["Coal"]
    structures = {row["name"]:row["guid"] for row in campaign["buildings"]}
    revealed = ({("marker","DefaultRandomizationPoint_"+point) for point in LEGACY_POINTS} |
                {("site",uid) for uid in LEGACY_TEMPLATES})
    assert len(missions)==19
    assert all(g["kind"]!="operate" for row in missions.values() for g in row["goals"])

    def world(scenario=None):
        return World(None,events,dialogs,quests,{guid:10000 for guid in resource_ids.values()},
                     campaign["scenario"] if scenario is None else scenario)

    def state(w, name):
        return w.variables.get(PREFIX+name,0)

    def tick(w, hours):
        for _ in range(hours*4):
            w.step(HOUR/4)

    def film(w, key):
        shot=campaign["films"][key]
        assert w.sequences.count("NI_Faultline_"+shot["shot"])==1
        w.sequence_signal(shot["signal"])
        w.sequence_signal(shot["signal"])

    def fulfill_city(w, row):
        for goal in quests[row["quest"]]["objectives"]:
            kind,count=goal["kind"],goal["quantity"]
            if kind=="build":
                w.buildings[goal["target"][0]]=count
            elif kind=="research":
                w.researched.add(goal["target"])
            elif kind=="warm":
                w.warm_homes=count
            elif kind=="produce":
                # No legacy stock or orders from the other panel slot qualify.
                assert not w.goal_met(row["quest"],goal)
                target,=goal["target"]
                w.produced[target]=w.produced.get(target,0)+count
            elif goal["label"]=="Scout":
                tick(w,7)
                assert w.world_map and w.revealed_sites==revealed and not w.placed_sites
                w.return_scouts()
                w.return_scouts()
                assert w.progress[row["quest"]]["Scout"]==1

    def send(w, key, cost, hours):
        order=names[key+"/dispatch"]
        assert order in w.open
        before={resource_ids[name]:w.stock[resource_ids[name]] for name in cost}
        assert w.click(order,0)
        assert not w.click(order,0)
        assert state(w,"shipment")==2
        for name,n in cost.items():
            account=resource_ids[name]
            assert w.stock[account]==before[account]-n
        tick(w,hours+1)

    played=set()
    for route in ((1,1,1,1,2,1,1,1,1), (2,2,2,2,3,2,2,2,2), (1,2,1,2,1,1,2,2,1)):
        w=world()
        w.start()
        assert len(w.recorded_city)==1
        for phase, number in enumerate(route,1):
            w.stress=0
            key=f"briefing/{phase}"
            tick(w,6)
            if key in campaign["films"]:
                if phase==6:
                    w=w.checkpoint()
                    w.start()
                    assert len(w.recorded_city)==1
                    tick(w,10)
                film(w,key)
            briefing=names[key]
            assert w.open.count(briefing)==1,(key,state(w,"phase"))
            if phase==5:
                choices=dialogs[briefing]["choices"]
                assert w.all(choices[1]["conditions"])==(route[1]==1)
                assert w.all(choices[2]["conditions"])==(route[1:3]==(2,2))
            if phase==9:
                assert w.all(dialogs[briefing]["choices"][1]["conditions"])==(route[7]==2)
            row=missions[phase,number]
            quest=row["quest"]
            task=f"act/{phase}/{number}"
            if phase>=8:
                order,= (goal for goal in row["goals"] if goal["kind"]=="produce")
                other,= (goal for goal in missions[phase,3-number]["goals"] if goal["kind"]=="produce")
                w.produced[order["target"][0]]=100
                w.produced[other["target"][0]]=100
            assert w.click(briefing,number-1)
            if phase>=8:
                w.produced[other["target"][0]]+=100
            lesson={1:"gauge",2:"refit",6:"watch",7:"charter",8:"valve_orders",9:"dispatch_orders"}.get(phase)
            if lesson:
                assert w.lessons.count(campaign["lessons"][lesson])==1
            profile=effects["faultline/"+row["profile"]]
            assert quest in w.active and profile in w.modifiers
            w.generator=False
            fulfill_city(w,row)
            if band:=row["signal"]:
                low,high=band
                w.stress=(low+high)/200
                tick(w,1)
                assert state(w,"stroke")==0
                w.generator=True
                w.stress=(low-4)/100
                tick(w,1)
                assert state(w,"stroke")==0
                if phase==1 and route[0]==2:
                    w.stress=0.82
                    tick(w,1)
                    assert effects["faultline/trip"] in w.modifiers and state(w,"stroke")==0
                    w.stress=(campaign["relay_reset"]-.5)/100
                    tick(w,1)
                    assert effects["faultline/trip"] not in w.modifiers
                w.stress=(low+high)/200
                expected=w.stress
                w.step(HOUR/4)
                assert state(w,"stroke")==1 and w.stress==expected
            w.generator=True
            if watch:=row["watch"]:
                mag=number==2
                if mag:
                    w.buildings[structures["Coal Magazine"]]=2
                cost=watch["coal"]-(campaign["magazine_saving"] if mag else 0)
                dispatch=task+("/covered" if mag else "/open")
                reserve=watch["reserve"]
                before=w.stock[coal]
                w.stock[coal]=reserve+cost-1
                tick(w,1)
                assert names[dispatch+"/dispatch"] not in w.open
                w.stock[coal]=before
                tick(w,1)
                assert w.click(names[dispatch+"/dispatch"],1)
                assert w.stock[coal]==before
                tick(w,7)
                send(w,dispatch,{"Coal":cost},watch["travel"])
                assert state(w,"leg")==1 and leak in w.modifiers
                outage=names[task+"/leak"]
                if mag:
                    tick(w,31)
                else:
                    w.stress=0.30
                    assert w.click(outage,0)
                    tick(w,3)
                assert leak not in w.modifiers
                for _ in range(2):
                    tick(w,1)
                    send(w,dispatch,{"Coal":cost},watch["travel"])
                assert state(w,"leg")==campaign["watch_legs"]
            if hold:=row["hold"]:
                w.stress=(hold["low"]+hold["high"])/200
                tick(w,1)
                assert state(w,"hold_hours")==1
                stock=w.stock[coal]
                w.stock[coal]=hold["reserve"]-1
                tick(w,2)
                assert state(w,"hold_hours")==1 and w.progress[quest]["PressureTest"]==1
                assert names[task+"/dispatch"] not in w.open
                w.stock[coal]=stock
                tick(w,hold["hours"]-1)
                assert state(w,"hold_hours")==hold["hours"]
            if pledge:=row["pledge"]:
                tick(w,2)
                send(w,task,pledge,2 if row["hold"] else 8)
            assert state(w,"phase")==phase+1 and profile not in w.modifiers,(task,state(w,"phase"))
            assert quest in w.completed
            played.add((phase,number))
        tick(w,6)
        ending=state(w,"ending")
        assert ending==3 and state(w,"kept")==9 and state(w,"convoy_returned")==1, (route,w.variables)
        film(w,"dawn/3")
        epilogue=names["accord/9"]
        assert w.open.count(epilogue)==1 and w.click(epilogue)
        tick(w,25)
        assert len(w.city_endings)==1 and not w.click(epilogue)
    assert played==set(missions)

    expired=world()
    expired.start()
    expired.generator=False
    expired.run(80,False)
    assert state(expired,"ending")==1 and state(expired,"kept")==0
    assert not expired.active and not expired.modifiers and len(expired.city_endings)==1
    assert names["end/0/0"] in expired.open

    middle=world()
    middle.start()
    middle.variables.update({PREFIX+"phase":10,PREFIX+"offered":9,PREFIX+"kept":6,PREFIX+"final":1})
    middle.run(2,False)
    assert state(middle,"ending")==2 and names["end/1/6"] in middle.open and len(middle.city_endings)==1

    for scenario in (DEFAULT,story["scenario"],story["winter_road"]["scenario"]):
        other=world(scenario)
        other.start()
        other.buildings[BEACON]=1
        other.run(2,False)
        assert not any(key.startswith(PREFIX) for key in other.variables)
        assert not any(uid in other.open for uid in names.values()) and not other.lessons
        assert not other.recorded_city and not other.city_endings
    return dict(plans=len(played),endings=3,trip_recovery=True,deadlines_continue=True,
                production_baselines=True,pressure_hours_persist=True,dispatch_paid_once=True,
                dispatch_arrivals=True,stockpile_independent_buildings=True,frostland_reveals=True,
                city_replay_once=True,cinematic_signal_and_fallback=True)
