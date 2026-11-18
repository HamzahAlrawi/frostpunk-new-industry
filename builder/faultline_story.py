"""The choices, operating envelopes and consequences of the Faultline campaign."""
from winter_road_story import COAL, DEPOTS, FOOD, STEEL, WARDS, build, operate, produce, research, warm


def pulse(low, high, draw=10):
    return dict(low=low, high=high, draw=draw)


def cool(ceiling):
    return dict(low=0, high=ceiling, draw=0)


def plan(title, profile, strokes, goals, report, **rewards):
    return dict(title=title, profile=profile, strokes=strokes, goals=goals, report=report, **rewards)


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
    dict(title="When the Ice Lets Go", days=7, story=(
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
        "The last front reaches the basin. A weak signal can reach the nearest shelter. To reach all of them, use the equipment "
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
)
