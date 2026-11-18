"""Faultline routes, deadlines and the field work each route requires."""
from faultline_buildings import MAGAZINE, RELAY, RELIEF_DISPATCH, VALVE_WORKS
from winter_road_story import COAL, DEPOTS, FOOD, STEEL, WARDS, build, research, warm


WATCH_LEGS = 3
LEAK_REPAIR = {"Steel": 35, "Coal": 60}


def plan(title, preview, profile, goals, report, **terms):
    return dict(title=title, preview=preview, profile=profile, goals=goals, report=report, **terms)


def order(building, button, key, count):
    return dict(kind="produce", recipe=key, station=building, quantity=count, text=f"Finish {count} × {button}",
                description=f"Queue this work order in {building} under General. Assign engineers. "
                            f"Finish {count} orders after accepting this job. Keep the finished supplies for departure.")


ACTS = (
    dict(title="A Signal Through the Pipe", days=5,
         story="Three knocks rise through the buried main. Somebody is still alive on the ridge. Edith needs a relay and a working line to answer.",
         plans=(
            plan("Keep the wards warm", "Warmer homes and wards. The station sends medics.", "ward",
                 [build("Build a Signal Relay",RELAY), build("Have a Medical Post","Medical Post")],
                 "The relay knocks back. Eight workers follow the flagged pipe to the city.",
                 signal=(18,58), people={"workers":8}, cargo={"Raw Food":45}, persistent="ward_crew"),
            plan("Give the workshops steam", "More industrial output. The station sends fitters.", "works",
                 [build("Build a Signal Relay",RELAY), build("Have a Workshop","Engineers Lab")],
                 "The crew recognises the old pumping station's signal and follows the pipe.",
                 signal=(23,63), people={"workers":4,"engineers":5}, cargo={"Steel":50}, persistent="works_crew"),
         ), failure="The station will keep signalling. Its first crew could not reach the city."),
    dict(title="The Junction Has Two Doors", days=6,
         story="There is room at the junction for one refit. Ivo wants a pressure accumulator. Mara wants a separate line to keep the clinics warm.",
         plans=(
            plan("Fit the accumulator", "Faster stress recovery. Opens a direct route to the ridge.", "works",
                 [research("Research Steam Hubs","H 1_SteamHub"),build("Have a Steelworks",*STEEL)],
                 "The new vessel takes the blow before it reaches the Generator.",
                 pledge={"Steel":85}, flag="accumulator", persistent="accumulator"),
            plan("Isolate the ward line", "Warmer clinics. A scout survey can open a second route.", "bypass",
                 [research("Research Heaters","H 1_Boilers"),build("Have two medical buildings",*WARDS,quantity=2)],
                 "The outer main cools. Heat keeps flowing into the wards.",
                 pledge={"Wood":55,"Steel":35}, flag="bypass", persistent="isolation"),
         ), failure="The junction stays as it was. Each shelter will have to be contacted separately."),
    dict(title="The Reply From Below", days=7,
         story="The lower shelter has families ready to move. The ridge surveyors can mark a second path if scouts collect their bearings.",
         plans=(
            plan("Guide the families down", "Provide warm beds and travelling rations.", "ward",
                 [warm(12),build("Have a Cookhouse","Food Processing")],
                 "The first sledges arrive carrying children and stove bricks.",
                 pledge={"Food Rations":60}, people={"workers":10,"children":7}, cargo={"Raw Food":125}),
            plan("Survey the upper shelf", "Send scouts out and bring them home with the route.", "works",
                 [build("Build a Beacon","Beacon"),dict(kind="scout",text="Send Scouts out and return them to the city")],
                 "The surveyors mark out a route for a second line.",
                 flag="surveyed", people={"engineers":8},cargo={"Steam Cores":2}),
         ), failure="Edith hangs two lamps by the gate. Nobody has answered yet."),
    dict(title="When the Ice Lets Go", days=7, shot="Fracture",
         story="The outer main splits. Send provisions along the ridge footpath or bring a load of steel to the break so the welders can reopen it.",
         plans=(
            plan("Send a food convoy", "100 rations and 30 coal. Cookhouses gain efficiency.", "bypass",
                 [build("Have a Hothouse",*FOOD),build("Have two Cookhouses","Food Processing",quantity=2)],
                 "The first sledge breaks. Its partner brings both loads to the shelters.",
                 pledge={"Food Rations":100,"Coal":30}, persistent="shelters"),
            plan("Send the welding crew", "100 steel and 60 coal. Raises the safe stress limit.", "works",
                 [build("Have two Steelworks",*STEEL,quantity=2),build("Have a Large Resource Depot","Resource Depot Big")],
                 "The welders close the seam and install a testing port on the far branch.",
                 pledge={"Steel":100,"Coal":60}, flag="welded"),
         ), failure="The split freezes solid. The surviving shelters have to share the old pipe."),
    dict(title="The Second Signal", days=8,
         story="The ridge stations have seen a front gathering. Your refit and scout survey determine which routes are still open.",
         plans=(
            plan("Call the shelters in order", "Prepare warm homes and send fuel along the main.", "ward",
                 [warm(18),build("Have three medical buildings",*WARDS,quantity=3)],
                 "The farthest shelter answers with the others' names.",
                 pledge={"Coal":155,"Food Rations":50}, flag="final"),
            plan("Use the accumulator", "One signal reaches every station. Requires the accumulator.", "works",
                 [build("Have two Resource Depots",*DEPOTS,quantity=2)],
                 "The three stations tap back the same word. Received.",
                 signal=(35,68),flag="final",requires=("accumulator",)),
            plan("Use the surveyed bypass", "The short route needs a survey and an isolated ward line.", "bypass",
                 [warm(14),build("Have two medical buildings",*WARDS,quantity=2)],
                 "Both crews hear the call at lower pressure and answer down separate pipes.",
                 pledge={"Coal":85,"Steel":30},flag="final",requires=("bypass","surveyed")),
         ), failure="The nearest shelter ties its call sign to the pipe. The rest stay silent."),
    dict(title="A Watch at Broken Mile", days=5, shot="NightWatch",
         story="The lamp at Broken Mile has gone out. Each watch is a coal delivery to one relief crew. Send three loads from the dispatch orders.",
         plans=(
            plan("Use the sheltered road", "50 coal per load. A longer journey through safer ground.", "ward",
                 [warm(14),build("Have two medical buildings",*WARDS,quantity=2)],
                 "The third crew comes back with ice on their coats. The lamp stays on.",
                 watch=dict(reserve=180,coal=50,travel=12),flag="watch_kept"),
            plan("Use the ridge tramway", "65 coal per load. A quicker route with a higher fuel bill.", "works",
                 [build("Have two coal mines or thumpers",*COAL,quantity=2),
                  build("Have two Steelworks",*STEEL,quantity=2)],
                 "The pump crew pulls the last cart off the bend. The main holds.",
                 watch=dict(reserve=165,coal=65,travel=7),flag="watch_kept"),
         ), failure="The lamp goes out for good. The remaining families will need a different bargain."),
    dict(title="What We Owe the Shelters", days=6, clears=("charter",),
         story="The ridge sends a list of names. Promise a share of the city's heat, or prepare warm homes and bring the remaining families inside.",
         plans=(
            plan("Sign a supply charter", "Send coal and rations. Requires all three Broken Mile loads.", "bypass",
                 [build("Have two Signal Relays",RELAY,quantity=2),warm(20)],
                 "The signed charter travels up the road with the last sledge.",
                 pledge={"Coal":250,"Food Rations":80},requires=("watch_kept",),flag="charter"),
            plan("Bring the families inside", "Build warm homes and send wood and rations.", "ward",
                 [warm(18),build("Have two Cookhouses","Food Processing",quantity=2)],
                 "The people at the gate carry a length of pipe for the houses on their street.",
                 pledge={"Wood":100,"Food Rations":65}, people={"workers":10,"children":6},
                 cargo={"Steel":80},persistent="resettled",flag="charter"),
         ), failure="Neither shelter will sign the charter. Some sledges will stay on the ridge."),
    dict(title="The Line Under the Lake", days=7, lesson="valve_orders", clears=("ridge_lift",),
         story="Ivo finds an old branch under the ice. Seal it and keep the footpath open, or build a bypass to power the stranded ridge lift.",
         plans=(
            plan("Seal the lake branch", "Make 4 valves. Run a low-stress test and commission the valves.", "ward",
                 [build("Build a Valve Works",VALVE_WORKS),
                  order(VALVE_WORKS,"Machine Isolation Valve","FaultlineIsolationValve",4)],
                 "The fourth valve closes quietly. The ridge lift will have to wait for spring.",
                 hold=dict(hours=4,low=0,high=38,reserve=225),pledge={"Steam Tools":4}),
            plan("Restore the ridge lift", "Make 3 bypass sections. Run a loaded test to open the lift route.", "works",
                 [build("Build a Valve Works",VALVE_WORKS),
                  order(VALVE_WORKS,"Rivet Bypass Section","FaultlineBypassSection",3)],
                 "The lift keeper answers with three blows of a hammer. The cage can run again.",
                 hold=dict(hours=3,low=25,high=63,reserve=300),pledge={"Steel Plates":3},flag="ridge_lift"),
         ), failure="The lake freezes over the break. The footpath remains open to the clinic."),
    dict(title="The Last Convoy", days=7, lesson="dispatch_orders",clears=("convoy_returned",),
         story="Mara counts beds. Edith listens for the lift keeper. There is time for one convoy before the road closes.",
         plans=(
            plan("Bring the clinic down", "Send 4 clinic sledges. Prepare beds for families and medics.", "ward",
                 [build("Build a Relief Dispatch",RELIEF_DISPATCH),warm(22),
                  order(RELIEF_DISPATCH,"Pack Clinic Sledge","FaultlineClinicSledge",4)],
                 "Six children arrive asleep. The medics put them straight into warm beds.",
                 pledge={"Wooden Materials":4}, flag="convoy_returned",
                 people={"workers":12,"children":6},persistent="ridge_medics"),
            plan("Bring the lift crew down", "Send 3 heavy sledges. Requires the repaired ridge lift.", "works",
                 [build("Build a Relief Dispatch",RELIEF_DISPATCH),build("Have two Steelworks",*STEEL,quantity=2),
                  order(RELIEF_DISPATCH,"Pack Lift Sledge","FaultlineLiftSledge",3)],
                 "The lift keeper sits on a crate of drill parts in the last cage. His crew puts them to work in the timber yards.",
                 pledge={"Steel Plates":3},flag="convoy_returned",requires=("ridge_lift",),
                 people={"workers":6,"engineers":8},cargo={"Steam Cores":2},persistent="ridge_fitters"),
         ), failure="The road closes while the convoy is still on the ridge. The city listens for their lamp all winter."),
)
