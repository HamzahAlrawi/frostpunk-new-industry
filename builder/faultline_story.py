"""The choices, operating envelopes and consequences of the Faultline campaign."""
from faultline_buildings import RELIEF_DISPATCH, VALVE_WORKS
from winter_road_story import COAL, DEPOTS, FOOD, STEEL, WARDS, build, operate, produce, research, warm

# Each completed watch sends fuel down the line. A lapse resets the current
# watch, and a leak interrupts both plans after the first delivery.
WATCH_LEGS = 3
LEAK_REPAIR = {"Steel": 35, "Coal": 60}


def pulse(low, high, draw=10):
    return dict(low=low, high=high, draw=draw)


def cool(ceiling):
    return dict(low=0, high=ceiling, draw=0)


def plan(title, profile, strokes, goals, report, **rewards):
    return dict(title=title, profile=profile, strokes=strokes, goals=goals, report=report, **rewards)


def order(building, button, key, count):
    return dict(kind="produce", recipe=key, station=building, quantity=count, text=f"{building}: complete {count} × {button}",
                description=f"Select {building}, staff it with engineers and add {button} to the queue under General. "
                            f"Finish {count} orders during this job. Orders finished earlier do not count.")


ACTS = (
    dict(title="A Signal Through the Pipe", days=5, story=(
        "An occupied weather station taps its call sign through a buried steam main. Its telegraph wire is gone. "
        "Our Generator can answer, but the same pipes serve our city. Decide which local circuit keeps its full supply "
        "while Edith establishes contact with the station."),
        plans=(
            plan("Give the wards priority", "ward", [pulse(20, 55), cool(8), pulse(26, 57)],
                 [build("Build a Medical Post", "Medical Post"), build("Build a Workshop", "Engineers Lab")],
                 "When the second pulse reaches the station, the reply spells out names instead of numbers. Eight workers walk in that evening.",
                 people={"workers": 8}, cargo={"Raw Food": 45}, persistent="ward_crew"),
            plan("Give the works priority", "works", [pulse(24, 60), cool(9), pulse(29, 60)],
                 [build("Build a Gathering Post", "GatheringPost"), build("Build a Workshop", "Engineers Lab")],
                 "The crew recognises the interval used by the old pumping stations. They follow the steam vents back to the basin.",
                 people={"workers": 4, "engineers": 5}, cargo={"Steel": 50}, persistent="works_crew"),
        ),
        failure="The station calls again on its own timetable. We recovered its frequency, but the first crew could not get here."),
    dict(title="The Junction Has Two Doors", days=6, story=(
        "The old junction has room for one rebuild. Ivo can fit a pressure accumulator that smooths heavy pulses. "
        "Mara wants an isolated line, with shut-off valves that let the city cool the main while the shelters stay warm. "
        "The refit you finish determines which routes you can use in the last whiteout."),
        plans=(
            plan("Fit the pressure accumulator", "works", [pulse(34, 61, 12), cool(12), pulse(39, 63, 13)],
                 [research("Research Steam Hubs", "H 1_SteamHub"), build("Build two Steam Hubs", "Steam Hub", quantity=2),
                  operate("Operate a Steelworks", *STEEL)],
                 "The pressure vessel takes the first blow. The main can now pass a heavy signal without putting its full load on the Generator.",
                 flag="accumulator", cargo={"Steel": 75}, persistent="accumulator"),
            plan("Fit an isolated bypass", "bypass", [cool(12), pulse(22, 54, 8), cool(10), pulse(27, 57, 9)],
                 [research("Research Heaters", "H 1_Boilers"), build("Build two Steam Hubs", "Steam Hub", quantity=2),
                  operate("Operate two medical buildings", *WARDS, quantity=2)],
                 "Mara closes one valve while Edith watches the gauge. The beds on the new line stay warm while the outer main cools.",
                 flag="bypass", cargo={"Coal": 125}, persistent="isolation"),
        ),
        failure="The junction stays as it was. We can still use the old main, but the station has to listen between each discharge."),
    dict(title="The Reply From Below", days=7, story=(
        "There are two replies to our call. The lower shelter can bring its families down if we keep the path thawed. "
        "The upper survey team can lead a bigger party tomorrow, if a scout brings home the route and we keep its pumps running. "
        "Each route gives the city something different before the storm."),
        plans=(
            plan("Guide the lower shelter", "ward", [pulse(28, 58), cool(11), pulse(34, 59, 11), cool(11)],
                 [warm(12), operate("Operate a Cookhouse", "Food Processing"),
                  produce("Cook eight new batches for the shelter", "meals", 8)],
                 "The families arrive carrying stove bricks. They ask where to put the bricks before they ask where they will sleep.",
                 people={"workers": 10, "children": 7}, cargo={"Raw Food": 125}),
            plan("Survey the upper shelf", "works", [pulse(35, 64, 12), cool(12), pulse(40, 65, 14)],
                 [build("Build a Beacon", "Beacon"), dict(kind="scout", text="Send Scouts out and return them to the city"),
                  operate("Operate a coal mine or thumper", *COAL)],
                 "The survey party sketches a branch that never appeared on the maps. The new line can take a signal at lower pressure.",
                 flag="surveyed", people={"engineers": 8}, cargo={"Steam Cores": 2}),
        ),
        failure="Edith hangs two lamps at the gate. Nobody has answered yet. We have enough time to prepare for the front."),
    dict(title="When the Ice Lets Go", days=7, shot="Fracture", story=(
        "An ice shelf shifts and punches a hole in the outer main. Close the branch and supply the stranded shelters from your "
        "own kitchens, or run pressure into the crack long enough for Ivo to weld it. A trip now will chill the entire city."),
        plans=(
            plan("Feed the shelters from the basin", "bypass",
                 [cool(10), pulse(27, 56, 9), cool(10), pulse(34, 60, 10)],
                 [operate("Operate a Hothouse", *FOOD), operate("Operate two Cookhouses", "Food Processing", quantity=2),
                  produce("Cook twelve new batches for the relief sleds", "meals", 12)],
                 "Mara sends the kitchen crews in pairs. When a sledge breaks, the other crew takes its load. No shelter misses its meal.",
                 cargo={"Food Rations": 150}, persistent="shelters"),
            plan("Hold pressure for the welders", "works",
                 [pulse(39, 63, 12), cool(13), pulse(44, 67, 15), cool(13)],
                 [operate("Operate two Steelworks", *STEEL, quantity=2),
                  build("Build a Large Resource Depot for the repair crew", "Resource Depot Big")],
                 "The welders finish with ice on their cuffs. They leave a testing port where we can read the pressure of the far branch.",
                 flag="welded", cargo={"Steel": 125}),
        ),
        failure="The outer line freezes solid. The remaining signals have to go through the same narrow pipe as before."),
    dict(title="The Night of the Second Signal", days=8, story=(
        "The shelters have seen a front gathering beyond the ridge. A weak signal can reach the nearest shelter. To reach all of them, use the equipment "
        "and safe bearings you earned, or take the extra time to call each shelter in turn. Once the line is quiet, "
        "the people on it will decide what they owe each other."),
        plans=(
            plan("Call the shelters in order", "ward",
                 [pulse(35, 62, 12), cool(12), pulse(41, 64, 13), cool(11), pulse(46, 67, 15)],
                 [warm(18), operate("Operate three medical buildings", *WARDS, quantity=3),
                  build("Build three Steam Hubs", "Steam Hub", quantity=3)],
                 "The farthest shelter answers just before dawn. It has the names of the others, and starts reading them back.",
                 flag="final"),
            plan("Send one heavy signal through the accumulator", "works",
                 [pulse(42, 64, 15), cool(15), pulse(51, 69, 18), cool(12)],
                 [operate("Operate two coal mines or thumpers", *COAL, quantity=2),
                  build("Build two Resource Depots", *DEPOTS, quantity=2)],
                 "The accumulator falls quiet. Ten minutes later, three stations tap the same word in the same rhythm. Received.",
                 flag="final", requires=("accumulator",)),
            plan("Send paired pulses down the surveyed bypass", "bypass",
                 [cool(10), pulse(30, 57, 10), cool(12), pulse(36, 62, 12)],
                 [warm(14), operate("Operate two medical buildings", *WARDS, quantity=2),
                  operate("Operate a Hothouse", *FOOD)],
                 "The two shelter crews hear different calls on their own pipes. By dawn each has the other's answer.",
                 flag="final", requires=("bypass", "surveyed")),
        ),
        failure="Some stations are still silent. The nearest shelter writes its own call sign on a flag and ties it to the pipe."),
    dict(title="A Watch at Broken Mile", days=5, shot="NightWatch", story=(
        "The lamp at Broken Mile has gone out. It marks a bend where the main runs above ground. "
        "Edith asks for three watches to keep steam flowing across the bend. Each watch needs coal unloaded while the reserve crew is there. "
        "Choose whether to send crews from the wards or bring the coal works onto the line."),
        plans=(
            plan("Run a low-pressure watch", "ward", [],
                 [build("Build two Steam Hubs", "Steam Hub", quantity=2), warm(14),
                  operate("Operate three medical buildings", *WARDS, quantity=3)],
                 "The third relief crew comes home with ice on their collars. The lamp behind them keeps burning.",
                 watch=dict(hours=8, low=0, high=34, reserve=180, coal=50), flag="watch_kept"),
            plan("Run a hot transfer", "works", [],
                 [build("Build two Steam Hubs", "Steam Hub", quantity=2),
                  operate("Operate two coal mines or thumpers", *COAL, quantity=2),
                  operate("Operate two Steelworks", *STEEL, quantity=2)],
                 "The pump crew pulls the last cart off the bend. One of them leaves a weld mark to show where the pipe held.",
                 watch=dict(hours=6, low=14, high=55, reserve=165, coal=65), flag="watch_kept"),
        ),
        failure="The line freezes at the bend. The last watch crew comes home on foot. The shelters will have to make a different bargain."),
    dict(title="What We Owe the Shelters", days=6, story=(
        "At first light, a sled carrying lists of names reaches the basin. The people on the ridge ask for a share of the main. "
        "The city can commit to supplying that line or dismantle the exposed span and bring the remaining families inside. "
        "Either decision has to work through the next winter."),
        plans=(
            plan("Offer the shelters a permanent supply", "bypass", [pulse(34, 61, 12), cool(13)],
                 [build("Build four Steam Hubs", "Steam Hub", quantity=4), warm(20),
                  produce("Cook sixteen new batches for the ridge", "meals", 16)],
                 "The signed charter travels back with the last coal sledge. The pump crews put up a second gauge so both settlements can read it.",
                 pledge={"Coal": 250, "Food Rations": 80}, requires=("watch_kept",), flag="charter"),
            plan("Move the remaining families into the basin", "ward", [],
                 [warm(18), operate("Operate two Cookhouses", "Food Processing", quantity=2),
                  produce("Cook fourteen new batches for the arrivals", "meals", 14)],
                 "The people at the gate carry a coil of pipe between them. They ask if the street behind the first row of houses has a name.",
                 pledge={"Wood": 100, "Food Rations": 65}, people={"workers": 10, "children": 6},
                 cargo={"Steel": 80}, persistent="resettled", flag="charter"),
        ),
        failure="Some sledges will stay on the ridge until spring. Neither shelter writes its name on the charter."),
    dict(title="The Line Under the Lake", days=7, lesson="valve_orders", clears=("ridge_lift",), story=(
        "The lake ice has peeled back from the old line. Ivo finds a second branch leading to the ridge lift, where a work crew "
        "has been stranded above the break since the storm. With the metal we have, we can seal the branch and bring the shelter "
        "sledges around it, or fit a bypass that gives the lift one more run. Build a Valve Works under Tech and staff it with engineers."),
        plans=(
            plan("Isolate the lake branch", "ward", [],
                 [build("Build a Valve Works", VALVE_WORKS),
                  order(VALVE_WORKS,"Machine Isolation Valve","FaultlineIsolationValve",4)],
                 "The fourth valve closes without a whistle. The clinic convoy can get down on foot while the lake branch cools. "
                 "The ridge lift will have to wait for spring.",
                 hold=dict(hours=6,low=12,high=36,reserve=225), cargo={"Food Rations":90}),
            plan("Power the ridge lift with a bypass", "works", [],
                 [build("Build a Valve Works", VALVE_WORKS),
                  order(VALVE_WORKS,"Rivet Bypass Section","FaultlineBypassSection",3)],
                 "Edith hears the lift drum through the new pipe. The lift keeper answers with a hammer: three blows for a loaded cage. "
                 "The Relief Dispatch can prepare a heavy sled train for those passengers.",
                 hold=dict(hours=4,low=37,high=59,reserve=300), flag="ridge_lift", cargo={"Steel":65}),
        ),
        failure="The lake freezes over the break. The ridge lift is stranded, but the clinic convoy can still descend along the footpath."),
    dict(title="The Last Convoy", days=7, lesson="dispatch_orders", clears=("convoy_returned",), story=(
        "Mara has been counting beds. Edith has been counting the pauses between the lift keeper's calls. We have enough crew to "
        "send one convoy before the road closes. The footpath brings the clinic out on sledges. If the bypass held, we can instead "
        "use the lift to bring its stranded crew down. Build and staff a Relief Dispatch under Tech to load the chosen convoy."),
        plans=(
            plan("Bring the clinic down the footpath", "ward", [pulse(24,49,8),cool(12)],
                 [build("Build a Relief Dispatch", RELIEF_DISPATCH), warm(22),
                  operate("Operate two medical buildings", *WARDS, quantity=2),
                  order(RELIEF_DISPATCH,"Pack Clinic Sledge","FaultlineClinicSledge",4)],
                 "Mara puts the steepest part of the trail behind her before she sits down. The clinic doors open that evening. "
                 "Six children arrive asleep and wake up in beds warm enough to go back to sleep.",
                 flag="convoy_returned", people={"workers":12,"children":6}, persistent="ridge_medics"),
            plan("Bring the lift crew down with its tools", "works", [pulse(38,58,12),cool(13),pulse(42,61,13)],
                 [build("Build a Relief Dispatch", RELIEF_DISPATCH),
                  operate("Operate two Steelworks", *STEEL, quantity=2),
                  order(RELIEF_DISPATCH,"Pack Lift Sledge","FaultlineLiftSledge",3)],
                 "The lift keeper rides down in the last cage, sitting on a crate of drill couplings. His crew uses them to refit our timber yards. "
                 "The next morning the empty cage goes back up carrying coal for the clinic.",
                 requires=("ridge_lift",), flag="convoy_returned", people={"workers":6,"engineers":8},
                 cargo={"Steam Cores":2}, persistent="ridge_fitters"),
        ),
        failure="The road closes while the convoy is still on the ridge. The crews turn back with their supplies, and the city spends the winter listening for their lamp."),
)
