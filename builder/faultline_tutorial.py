"""On-demand Faultline lessons using the native tutorial message panel."""
from tools.native_binary import Cursor, SchemaError, string, u32
from tools.native_scenario import append_directory, typed


PATH = "configs/frostpunkmessagesconfig.bin"
MESSAGE = "FrostpunkTutorialMessageEntry"
SHOW = "FrostpunkCreateTutorialMessageEffect"
SHOW_FLAGS = u32(0)+b"\1"
LESSONS = {
    "first_relief": ("Guide in the advance parties",
        "Build a Signal Relay under Tech. Switch on the Generator and check Heat view. The clinic scouts need a Liveable Medical Post. The advance fitters need a Liveable Workshop. Your first crew comes in as soon as its building is ready. You then have two days to warm the other building and bring the second crew home."),
    "cool": ("Cool the main",
        "Switch Overdrive off and leave the Generator running. Stress falls while it cools."),
    "relay": ("Reconnect the relay",
        "The main trips at 72% stress. Switch Overdrive off until the gauge drops to 25% with a Signal Relay or 14% without one. Loss of heat ends when the line reconnects."),
    "refit": ("Choose a refit",
        "The accumulator recovers stress faster and can transmit to all stations. The isolated return line keeps wards warmer and opens another route with a scout survey."),
    "survey": ("Bring the survey back",
        "Build a Beacon to open Frostland. Form a scout team, visit one of the revealed sites and order the team back to the city. The tracker credits a return during this mission."),
    "watch": ("Send fuel to Broken Mile",
        "Each watch is a relief crew's shift. Keep both buildings named in your objective Liveable or warmer. Convoys load and depart automatically when there is fuel above the city reserve. A convoy waits at a stop if a route goes cold.\n\n"
        "Deliver three loads. A Coal Magazine cuts each load by 20 coal. Repair the leak after the first arrival."),
    "districts": ("Prove a district heat loop",
        "Open the Heat view. Keep one of each named building Liveable or warmer. Steam Hubs and Heaters can cover workplaces outside the Generator zone. Three qualifying hourly readings commission the loop.\n\n"
        "The loop warms its buildings and shortens Broken Mile trips along that route. It will also help in the final rescue."),
    "charter": ("Dispatch supplies",
        "Set aside the listed cargo, then approve departure in the dispatch order. The tracker credits the arrival. A brief delay is available whenever you need the stock for the city."),
    "valve_orders": ("Commission the new line",
        "Staff the Valve Works and queue the listed parts in General. The gauges count one test hour whenever the Generator is running in the specified stress band with enough coal. The counter pauses outside the band and keeps its progress. Once the parts and test are ready, choose Install parts."),
    "dispatch_orders": ("Load the last convoy",
        "Staff Relief Dispatch and queue the orders in your tracker. Clinic sledges use Wooden Materials as cargo. Heavy sledges use Steel Plates. Finish the preparations and send the cargo. The lead route opens first during the whiteout."),
    "whiteout": ("Two rescue routes",
        "Keep the named buildings on each route Liveable or warmer. Six warm hours bring the lead crew in. The second route opens two hours later and needs eight warm hours. Heat loss pauses either counter.\n\n"
        "The storm lasts eighteen hours. If you repaired the lift, you can save both crews. Only one route can draw on the reserve boiler. Check Heat view before committing it."),

}


def lesson_id(guid, lesson):
    return guid("faultline/lesson/"+lesson)


def show(guid, lesson):
    return typed(SHOW)+lesson_id(guid,lesson)+SHOW_FLAGS


def donor(native):
    prefix=typed(MESSAGE)+string("[Builders] Motivation")
    start=native.index(prefix)
    end=native.index(b"\1"+string("Main Narrative Line"),start)
    c=Cursor(native,start+len(prefix)+16)
    before_title=c.take(25)
    title=c.string()
    before_text_start=c.position
    c.take(53)
    if c.string()!="FrostpunkTutorialMessageTextDescriptionField":
        raise SchemaError("Unsupported tutorial message description field")
    before_text=native[before_text_start:c.position]
    body=c.string()
    if not title.endswith("/Title") or not body.endswith("/Description") or c.position!=end:
        raise SchemaError("Unsupported tutorial message boundary")
    return before_title,before_text


def build(native, native_events, guid, loc):
    # Two complete adjoining effects pin the serialized footer independently
    # of a choice or event's following fields.
    samples=("6cfbef1d74a878b9444f7b8d3a08d4f2","ac34f62ec5c8c1b8db44c155e82aba64")
    sample=b"".join(typed(SHOW)+bytes.fromhex(uid)+SHOW_FLAGS for uid in samples)
    if sample+typed(SHOW) not in native_events:
        raise SchemaError("Unsupported native tutorial message effect")
    before_title,before_text=donor(native)
    records=[]
    for key,(title,body) in LESSONS.items():
        records.append(typed(MESSAGE)+string("NI Faultline "+key)+lesson_id(guid,key)+before_title
                       +loc(f"Faultline/Lessons/{key}/Title",title)+before_text
                       +loc(f"Faultline/Lessons/{key}/Body",body))
    return append_directory(native,"Tutorial","Main Narrative Line",records)
