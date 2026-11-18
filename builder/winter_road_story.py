"""Winter Road chapter and side project catalogue."""

HOMES=("Tent","Bunkhouse","House")
WARDS=("Medical Post","Ambulatorium","HospitalOfMercy")
STEEL=("Iron Ore Mine","SteamIronOreMine","AdvancedOreMine")
COAL=("Coal Mine","SteamCoalMine","AdvancedCoalMine","CoalThumper","CoalThumperSteam")
FOOD=("Plantation","Steam Plantation")
DEPOTS=("Resource Depot","Resource Depot Big")


def build(text,*names,quantity=1):
    return dict(kind="build",text=text,names=names,quantity=quantity)


def operate(text,*names,quantity=1):
    return dict(kind="operate",text=text,names=names,quantity=quantity)


def research(text,name):
    return dict(kind="research",text=text,tech=name)


def warm(quantity):
    return dict(kind="warm",text=f"Keep {quantity} homes Liveable or warmer",quantity=quantity,
                description="Use the temperature overlay to find cold homes. Tents, Bunkhouses and Houses count.")


def produce(text,key,quantity):
    return dict(kind="produce",text=text,recipe=key,quantity=quantity)


def plan(title,detail,goals,cost=None,people=None,cargo=None,**extra):
    return dict(title=title,detail=detail,goals=goals,cost=cost or {},people=people or {},cargo=cargo or {},**extra)


CHAPTERS=(
    dict(key="first-sled",title="Two Bells in the Fog",days=3,story=(
        "The night relay repeats the same clearance twice. Mara’s school group is on the lower shelf; Ivo’s "
        "pump crew is above it, following the same rope. Twelve outriders have reached the gate. We can guide "
        "one party down before dark. The others will have to survive another night on the pass."),
        plans=(
            plan("Bring Mara down first","Build a Medical Post for the school convoy. The outriders bring 40 wood and 20 coal.",
                 [build("Build a Medical Post","Medical Post")],{"Food Rations":20},{"workers":10,"children":10},
                 {"Raw Food":35},entry={"Wood":40,"Coal":20},report="Mara arrives with the school register wrapped in a wool blanket. The names on it are still legible."),
            plan("Bring Ivo down first","Build a Gathering Post for the winch crew. The outriders bring 25 steel and one steam core.",
                 [build("Build a Gathering Post","GatheringPost")],{"Coal":85},{"workers":10,"engineers":8},
                 {"Coal":140},entry={"Steel":25,"Steam Cores":1},report="Ivo’s people reach the gate with their tools. He asks Edith to leave the second bell ringing for the school party."),
        ),lost={"workers":3,"children":1},
        failure="Four people found the stair cut into the rock. They say the main party stayed at the last lamp."),
    dict(key="winch",title="The Broken Winch",days=5,story=(
        "The winch splits under the next sled. A small party can reach us now, but the rest are pinned above the switchback. "
        "Take the wounded and make room to treat them, or take the crew that can rebuild the winch. We have to live with whoever "
        "comes through that gate, and with whoever is still outside it."),
        plans=(
            plan("Take the injured","Six gravely ill workers arrive immediately. Open enough beds to receive the rest of the party.",
                 [operate("Operate two medical buildings",*WARDS,quantity=2)],{"Food Rations":45,"Coal":80},
                 {"workers":12,"engineers":4,"children":8},{"Food Rations":45},sick=6,
                 report="The ward lights stay on until morning. The last sled carries a boy who refuses to let go of the bell pull."),
            plan("Repair the winch","Six engineers arrive immediately. Build the local steel and heat supply they need.",
                 [build("Build a Steelworks",*STEEL),build("Build a Steam Hub","Steam Hub")],{"Steel":70,"Coal":100},
                 {"workers":12,"engineers":6},{"Steam Cores":2},engineers=6,
                 report="The rebuilt winch holds. Ivo’s late crew bring two sealed steam cores down in the empty tool chest."),
        ),lost={"workers":4,"engineers":1},failure="Five people crossed on foot. The winch and most of the cargo are still on the ridge."),
    dict(key="charter",title="Who Gets a Key?",days=5,story=(
        "Mara has drawn a map of the beds, with both convoys on it. Ivo has drawn a map of the fuel stores, "
        "with a lock on every door. They agree we cannot keep going on promises. This city needs rules about "
        "who controls supplies, where to send workers, and which district gets scarce steam first."),
        plans=(
            plan("Give the wards a charter","Build a district that can take in families. A successful charter makes homes and wards warmer.",
                 [warm(6),operate("Operate a Cookhouse","Food Processing"),operate("Operate two medical buildings",*WARDS,quantity=2)],
                 {"Wood":60,"Food Rations":40},cargo={"Raw Food":100},bonus="public",
                 report="Mara hangs a key beside the ward door. Nobody has to ask whose bed it is anymore."),
            plan("Charter the works council","Put the coal and steel crews in charge of emergency supplies. A successful charter makes their plants more productive.",
                 [operate("Operate a Steelworks",*STEEL),operate("Operate a coal mine or thumper",*COAL),
                  research("Research Steam Hubs","H 1_SteamHub")],
                 {"Steel":65,"Coal":120},cargo={"Coal":300},bonus="works",
                 report="The works council opens its books. Ivo leaves the first load of coal outside the ward before anyone asks."),
        ),failure="The delegates leave with their keys. The city goes on without either district charter."),
    dict(key="survey",title="A Road Off the Map",days=5,story=(
        "The relay answers from the wrong compass bearing. An old survey route crosses the lee side of the ridge. "
        "If scouts can bring back a fix, we can stop guessing. If not, a heated line of waystations might let local "
        "guides work from the crater toward the pass."),
        plans=(
            plan("Send a survey party","Build a Beacon, send scouts into the Frostland, then bring them back to the city. Earlier trips do not count.",
                 [build("Build a Beacon","Beacon"),dict(kind="scout",text="Bring a scout expedition back to the city",quantity=1)],
                 {"Food Rations":40},cargo={"Steel":80,"Steam Cores":2},flag="mapped",
                 report="The scouts come back with a bearing and a strip of torn flag. It marks an approach wide enough for two sledges."),
            plan("Lay a line of warm stops","Research Steam Hubs and build three. The surveyors will follow the heated route on foot.",
                 [research("Research Steam Hubs","H 1_SteamHub"),build("Build three Steam Hubs","Steam Hub",quantity=3),
                  operate("Operate a Gathering Post","GatheringPost")],
                 {"Steel":90,"Coal":100},cargo={"Wood":140,"Coal":160},flag="mapped",
                 report="The third waystation lights as the guides return. They have found the same approach the old maps show."),
        ),failure="The whiteout buries the survey marks. The old crossing is still usable, but there is no safe route for a twin operation."),
    dict(key="embargo",title="The Locked Bins",days=5,story=(
        "Someone has padlocked the syndicate’s coal bins. They blame the newcomers for burning through the reserve; "
        "the newcomers say the bins were half empty before they arrived. The next cold front does not care who is right. "
        "You can build a common reserve, or prove the city can keep the heat on without bargaining for every shovel."),
        plans=(
            plan("Open a common reserve","Build three depots and keep the cookhouse running. Commit a shared coal and food reserve once.",
                 [build("Build three Resource Depots",*DEPOTS,quantity=3),operate("Operate a Cookhouse","Food Processing"),warm(8)],
                 {"Coal":350,"Food Rations":120},cargo={"Wood":160,"Food Rations":80},flag="reserve",
                 report="The first common ration line opens. Neighbours who argued over coal spend the morning stamping the same tickets."),
            plan("Break the coal monopoly","Staff two coal works and upgrade Generator efficiency. Build a large reserve of your own.",
                 [operate("Operate two coal mines or thumpers",*COAL,quantity=2),
                  research("Research Generator Efficiency Upgrade","H 3_Generator Upgrade - less coal"),
                  build("Build a Large Resource Depot","Resource Depot Big")],
                 {"Steel":110,"Coal":275},cargo={"Coal":440,"Steam Cores":2},flag="reserve",
                 report="The syndicate returns the keys when its members see the new depot. They ask for a place on the shift roster."),
        ),failure="The lock comes off too late. Some bins are empty. The city will have no dispatch reserve to draw on at the crossing."),
    dict(key="crossing",title="The False Clearance",days=6,story=(
        "Edith puts the original clearance tape on the desk. Her call sign is on both orders. She erased the children "
        "to get the second party out of the depot before the storm closed it. Now neither party has enough time. "
        "Read every name and clear the slower road, carry the repair crews and their gear by ferry, or lead both crossings "
        "if the city has actually surveyed the pass and rigged the spare line."),
        plans=(
            plan("Read every name","Bring families down the open road. Make beds and hold staffed wards ready.",
                 [warm(12),operate("Operate two medical buildings",*WARDS,quantity=2),operate("Operate a Cookhouse","Food Processing")],
                 {"Food Rations":125,"Coal":200},{"workers":18,"engineers":6,"children":22},{"Raw Food":110},flag="crossed",
                 report="Mara reads the last names in front of the gate. There is a long pause, then a child answers from a sled with a broken runner."),
            plan("Run the rope ferry","Use a heated landing and the works crews. Carry the heaviest sleds and their machinery.",
                 [build("Build two Steam Hubs","Steam Hub",quantity=2),operate("Operate two Steelworks",*STEEL,quantity=2),warm(9)],
                 {"Steel":110,"Coal":240},{"workers":18,"engineers":16,"children":2},{"Steam Cores":3,"Steel":80},flag="crossed",
                 report="Ivo brings the relay down on the last sled. The first signal he sends is a request for the names of the people left on the ridge."),
            plan("Open both crossings","Requires a survey and a completed spare-rope project. Make room for both parties and bring both loads down.",
                 [warm(14),build("Build three Steam Hubs","Steam Hub",quantity=3),operate("Operate three medical buildings",*WARDS,quantity=3)],
                 {"Food Rations":155,"Steel":90,"Coal":300},{"workers":24,"engineers":16,"children":24},
                 {"Steam Cores":3,"Food Rations":100},flag="crossed",requires=("mapped","rope"),
                 report="Both ropes come down taut. The two crews meet in the square; Edith puts both manifests under glass with no names crossed out."),
        ),lost={"workers":5,"engineers":2,"children":1},failure="Eight people reach the south gate. Lamps are still visible on the ridge, but the large sleds cannot move."),
    dict(key="rebuild",title="The City After the Crossing",days=6,story=(
        "The last rope is tied off. There are people sleeping three to a bench, and some of them have never seen a Generator. "
        "The next threat is the city itself: either rebuild its food and wards for the new population, or teach its new crews "
        "to build the machines that will work when nobody can stand outside."),
        plans=(
            plan("Provision the shelter district","Run a Hothouse and hand out fresh Cookhouse rations. Old stock does not count for the new batches.",
                 [operate("Operate a Hothouse",*FOOD),produce("Cook 10 new batches of rations","meals",10),warm(14)],
                 {"Wood":110,"Food Rations":80},cargo={"Food Rations":140,"Raw Food":140},flag="provisioned",
                 report="The kitchen serves a second sitting. For the first time since the crossing it puts quiet work ahead of emergency orders."),
            plan("Build the winter machines","Open a Factory and build two automatons. Machines from before this promise do not count.",
                 [build("Build a Factory","Factory"),produce("Manufacture two new automatons","automatons",2),
                  operate("Operate a Steelworks",*STEEL)],{"Coal":260,"Steel":115},cargo={"Steam Cores":3,"Coal":280},
                 flag="provisioned",report="The apprentices mark two names on the shift board. Under them Ivo writes one word: Machines."),
        ),failure="The crews finish only the emergency repairs. The city must take the next front without an extra provisioning reserve."),
    dict(key="long-night",title="The Long Night",days=5,story=(
        "The cold breaks a joint in the outer steam ring. The whole city drops two levels of insulation while it is exposed. "
        "Keep the Generator lit and its fuel safe through six consecutive inspections. At the same time, make either the "
        "residential wards or the industrial lifeline warm and useful. The joint can be sealed only if you do both."),
        plans=(
            plan("Hold the heated wards","Keep sixteen homes Liveable and three wards running through the inspections.",
                 [warm(16),operate("Operate three medical buildings",*WARDS,quantity=3)],{"Coal":360,"Food Rations":135},
                 flag="held",watch=6,report="On the last inspection a nurse opens the ward window a crack. Steam is finally returning to the outer ring."),
            plan("Hold the industrial lifeline","Keep twelve homes Liveable, two coal works operating and four hubs standing through the inspections.",
                 [warm(12),operate("Operate two coal mines or thumpers",*COAL,quantity=2),build("Build four Steam Hubs","Steam Hub",quantity=4)],
                 {"Coal":360,"Steel":140},flag="held",watch=6,report="The last shift keeps the coal coming. The joint is welded shut while the people on the night watch are still awake to hear it."),
        ),failure="The outer joint is finally isolated. The city survives the blackout, but the relief crews have to leave the ridge route closed for the winter."),
)


AFTERMATH=(
    dict(title="The People Beyond the Gate", days=6, story=(
        "A runner brings the names of people who never made it onto a convoy. They are sheltering in the disused rope station. "
        "Mara wants to bring the families down. Ivo says the station is also the last dry shelter for the crews repairing the pass. "
        "The city can prepare either a reception district or a supply base for the road crews."),
        plans=(
            plan("Make room for the station families","Run three wards and cook ten new batches of rations. Keep sixteen homes warm during the reception watch.",
                 [warm(16),operate("Operate three medical buildings",*WARDS,quantity=3),
                  produce("Cook ten new batches of rations","meals",10)],
                 {"Wood":110,"Food Rations":120,"Coal":180},people={"workers":14,"children":8},
                 cargo={"Raw Food":120},watch=4,
                 report="The children arrive first. The station keeper waits at the gate until every name is read back to her."),
            plan("Supply the isolated road crews","Staff two Steelworks and a coal works. A large depot stages the payload through the loading watch.",
                 [operate("Operate two Steelworks",*STEEL,quantity=2),
                  operate("Operate a coal mine or thumper",*COAL),build("Build a Large Resource Depot","Resource Depot Big")],
                 {"Steel":150,"Wood":100,"Coal":230},people={"workers":8,"engineers":4},
                 cargo={"Steam Cores":2},watch=4,
                 report="The last wagon brings back the road crew's spare cores. They leave one person at the station to keep the bell working."),
        ), failure="The station shuts down as the ridge freezes over. Its keeper sends the city the list of shelters they will try next."),
    dict(title="The Ice Under the Road", days=7, story=(
        "The thaw has opened cracks below the old signal line. Then the wind turns and freezes each crack into a blade. "
        "The crews can save the heated roadbed or abandon it and build a kitchen reserve for people cut off by the ice."),
        plans=(
            plan("Shore up the heated road","Keep four Steam Hubs standing and two coal works operating through six inspections.",
                 [build("Build four Steam Hubs","Steam Hub",quantity=4),
                  operate("Operate two coal mines or thumpers",*COAL,quantity=2)],
                 {"Steel":160,"Coal":380},cargo={"Wood":150,"Steel":80},watch=6,
                 report="Ivo marks the safe side of the embankment with furnace ash. The sledge drivers follow it in single file."),
            plan("Build a reserve kitchen","Grow food in two Hothouses and run two Cookhouses. Cook eighteen new batches while holding the reserve.",
                 [operate("Operate two Hothouses",*FOOD,quantity=2),
                  operate("Operate two Cookhouses","Food Processing",quantity=2),
                  produce("Cook eighteen new batches of rations","meals",18)],
                 {"Wood":160,"Coal":220,"Food Rations":160},cargo={"Food Rations":200,"Raw Food":100},watch=6,
                 report="The kitchen wheels its first hot cauldron to the shelter before the lanterns go out. The people there send back the empty bowls."),
        ), failure="The ice cuts the line. Edith records the last call and gives the crews a route back to the city."),
    dict(title="A Place on the Winter Map", days=8, story=(
        "The regional surveyors ask what they should mark here. We can keep a refuge staffed and heated through the next bad winter, "
        "or send machines out to maintain the shelters scattered across the pass. Whichever promise we make, someone will rely on it."),
        plans=(
            plan("Keep a permanent refuge","Run an Infirmary and two Cookhouses. Hold twenty-four homes warm through the final two-day watch.",
                 [warm(24),operate("Operate an Infirmary","Ambulatorium"),
                  operate("Operate two Cookhouses","Food Processing",quantity=2)],
                 {"Coal":450,"Food Rations":240,"Wood":140},people={"engineers":6},
                 cargo={"Food Rations":210},watch=8,
                 report="The surveyors mark the basin with an open door. Mara pins a copy beside the names of the first outriders."),
            plan("Send the winter machines","Operate a Factory and two Steelworks. Manufacture two new automatons during the final two-day watch.",
                 [operate("Operate a Factory","Factory"),operate("Operate two Steelworks",*STEEL,quantity=2),
                  produce("Manufacture two new automatons","automatons",2)],
                 {"Coal":450,"Steel":220},cargo={"Steam Cores":4},watch=8,
                 report="The last two machines leave with spare parts and engraved route plates. Edith hears their leads check in from the first shelter."),
        ), failure="The surveyors mark the city as a winter refuge when its own stores permit. The work has reached the limit of what we can promise."),
)


PROJECTS=(
    dict(at=2,key="rope",title="The Spare Rope",story="Ivo can rig a second crossing if we make a heated stop and find enough timber.",
         days=4,cost={"Wood":45},goals=[build("Build a Steam Hub","Steam Hub")],reward={"Wood":90},flag="rope",
         finish="The new line is marked. Survey the pass and you can use both ropes in the final evacuation."),
    dict(at=3,key="school",title="A Room for the School",story="Mara asks for two permanent Bunkhouses where children can sleep between kitchen shifts.",
         days=4,cost={"Wood":40},goals=[build("Build two Bunkhouses or Houses","Bunkhouse","House",quantity=2)],
         reward={"Raw Food":120,"Wood":60},flag="school",finish="The school moves off the floor of the ward. Its food parcel is shared with the kitchens."),
    dict(at=4,key="clinic",title="The Night Clinic",story="The stragglers know how to reach another stranded work gang. They will guide it home if our ward is ready.",
         days=4,cost={"Food Rations":40},goals=[operate("Operate three medical buildings",*WARDS,quantity=3)],
         reward={"Raw Food":75},people={"workers":12,"children":6},flag="clinic",
         finish="Eighteen people arrive through the night. Six are children. The city now needs eighteen more beds and meals."),
    dict(at=5,key="lamp",title="Keep the Signal Lit",story="The upper relay gives up a signal whenever the cold line cracks. Fit the run with real heaters.",
         days=4,cost={"Steel":60},goals=[research("Research Heaters","H 1_Boilers"),build("Build three Steam Hubs","Steam Hub",quantity=3)],
         reward={"Coal":300},flag="lamp",finish="The relay no longer drops every other signal. Its crew sends 300 coal for the next inspection."),
    dict(at=6,key="bread",title="Bread for the Landing",story="The cooks can send hot meals down to the landing. Cook the supplies fresh; we need to keep some food in the city as well.",
         days=4,cost={"Food Rations":65},goals=[produce("Cook 10 new batches of rations","meals",10)],
         reward={"Raw Food":180,"Wood":110},flag="bread",finish="The guides bring back the empty cups and a food cache marked on the old map."),
    dict(at=7,key="repair",title="The Apprentice’s Machine",story="A newcomer says she can rebuild a salvage machine with a real Factory and a single new automaton frame.",
         days=5,cost={"Steel":100},goals=[produce("Manufacture one new automaton","automatons",1)],
         reward={"Steam Cores":2,"Coal":220},flag="repair",
         finish="The machine is yours to assign. The apprentices use the salvaged fittings to reinforce the city’s heating ring."),
)
