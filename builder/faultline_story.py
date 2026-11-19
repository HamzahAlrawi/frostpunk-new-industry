"""Faultline routes, deadlines and the field work each route requires."""
from faultline_buildings import RELAY, RELIEF_DISPATCH, VALVE_WORKS
from winter_road_story import COAL, DEPOTS, STEEL, WARDS, build, research, warm


WATCH_LEGS = 3
LEAK_REPAIR = {"Steel": 35, "Coal": 60}
LINE_INSPECTIONS = 3
WHITEOUT_HOURS = 18
OPENING_HOURS = 48
ADVANCE_CREWS = {
    "medics": dict(label="the clinic scouts", warm="Medical Post", description="a Medical Post",
                   people={"workers":8,"children":4}, cargo={"Raw Food":45}, reward="ward_crew"),
    "fitters": dict(label="the advance fitters", warm="Engineers Lab", description="a Workshop",
                    people={"workers":4,"engineers":5}, cargo={"Steel":50}, reward="works_crew"),
}
RELIEF_LINES = {
    "clinic": dict(name="Clinic", pact="clinic_pact", groups=(WARDS, ("Food Processing",)),
                   services="one medical building and one Cookhouse",
                   households={"workers":12,"children":6},
                   relief={"Coal":75,"Food Rations":25}, reward="ridge_medics"),
    "lift": dict(name="Lift", pact="lift_pact", groups=(STEEL, COAL),
                 services="one Steelworks and one Coal Mine or Coal Thumper",
                 households={"workers":6,"engineers":8}, cargo={"Steam Cores":2},
                 relief={"Coal":100,"Steel":25}, reward="ridge_fitters"),
}


def plan(title, preview, profile, goals, report, **terms):
    return dict(title=title, preview=preview, profile=profile, goals=goals, report=report, **terms)


def order(building, button, key, count):
    return dict(kind="produce", recipe=key, station=building, quantity=count, text=f"Finish {count} × {button}",
                description=f"Queue this work order in {building} under General. Assign engineers. "
                            f"Finish {count} orders after accepting this job. Keep the finished supplies for departure.")


ACTS = (
    dict(title="A Signal Through the Pipe", days=5,
         story="Two advance parties made it off the ridge. A Signal Relay can guide them the rest of the way. Warm a receiving station and decide who comes in first. Once you answer, there are two days to reach the other party.",
         plans=(
            plan("Bring in the clinic scouts", "Warm a Medical Post. Gain workers, families and field medics.", "ward",
                 [build("Build a Signal Relay",RELAY), build("Have a Medical Post","Medical Post")],
                 "The clinic scouts come in with four children and bags of frozen food. The fitters can follow if you make a warm Workshop ready in the next two days.",
                 first_crew="medics"),
            plan("Bring in the advance fitters", "Warm a Workshop. Gain engineers, steel and fitter training.", "works",
                 [build("Build a Signal Relay",RELAY), build("Have a Workshop","Engineers Lab")],
                 "The fitters go straight to the Workshop. The clinic scouts can follow if you make a warm Medical Post ready in the next two days.",
                 first_crew="fitters"),
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
    dict(title="When the Ice Lets Go", days=7, lesson="districts",
         story="The rupture has cut both ridge stations off. The city has fittings for one branch. Repair it, then prove your district can keep the far end warm.",
         plans=(
            plan("Connect the clinic road", "Heat healthcare and kitchens. The road carries coal faster.", "bypass",
                 [build("Have one medical building",*WARDS),build("Have a Cookhouse","Food Processing")],
                 "Mara clears a ward for road crews. The clinic and kitchens keep an extra heat level, and coal convoys can shelter on this road.",
                 district="clinic", persistent="clinic_pact"),
            plan("Connect the works spur", "Heat steel and coal works. The tram runs faster.", "works",
                 [build("Have a Steelworks",*STEEL),build("Have a coal mine or thumper",*COAL)],
                 "Ivo’s crew fixes the main and opens the siding. The works keep an extra heat level and the Generator trips at 82% stress instead of 72%.",
                 district="lift", flag="welded", persistent="lift_pact"),
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
    dict(title="A Watch at Broken Mile", days=5,
         story="Three crews are trying to keep Broken Mile open. Dispatchers will load the sledges themselves. Your job is to keep their heated stops open and leave coal for the city.",
         plans=(
            plan("Use the clinic road", "50 coal per load. Keep a medical building and Cookhouse warm.", "ward",
                 [build("Have a medical building",*WARDS),build("Have a Cookhouse","Food Processing")],
                 "The third crew comes back with ice on their coats. The lamp stays on.",
                 watch=dict(reserve=180,coal=50,travel=12, district="clinic"),flag="watch_kept"),
            plan("Use the ridge tramway", "65 coal per load. Keep a Steelworks and coal works warm.", "works",
                 [build("Have a coal mine or thumper",*COAL),build("Have a Steelworks",*STEEL)],
                 "The pump crew pulls the last cart off the bend. The main holds.",
                 watch=dict(reserve=165,coal=65,travel=8, district="lift"),flag="watch_kept"),
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
    dict(title="Two Crews in the Whiteout", days=7, lesson="dispatch_orders",clears=("convoy_returned",),
         story="The last front is eighteen hours wide. Pack the lead convoy. Its crew gets a head start. With two heated routes, both crews can make it down.",
         plans=(
            plan("Lead with the clinic sledges", "Pack 4 clinic sledges. The clinic gets a two-hour head start.", "ward",
                 [build("Build a Relief Dispatch",RELIEF_DISPATCH),warm(12),
                  order(RELIEF_DISPATCH,"Pack Clinic Sledge","FaultlineClinicSledge",4)],
                 "The clinic convoy takes the road first.",
                 pledge={"Wooden Materials":4}, lead="clinic"),
            plan("Lead with the lift crew", "Pack 3 heavy sledges. Requires the repaired ridge lift.", "works",
                 [build("Build a Relief Dispatch",RELIEF_DISPATCH),build("Have two Steelworks",*STEEL,quantity=2),
                  order(RELIEF_DISPATCH,"Pack Lift Sledge","FaultlineLiftSledge",3)],
                 "The lift crew takes the cable first.",
                 pledge={"Steel Plates":3},lead="lift",requires=("ridge_lift",)),
         ), failure="The road closes while the convoy is still on the ridge. The city listens for their lamp all winter."),
)
