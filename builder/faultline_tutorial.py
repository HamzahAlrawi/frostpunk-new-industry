"""On-demand Faultline lessons using the native tutorial message panel."""
from tools.native_binary import Cursor, SchemaError, string, u32
from tools.native_scenario import append_directory, typed


PATH = "configs/frostpunkmessagesconfig.bin"
MESSAGE = "FrostpunkTutorialMessageEntry"
SHOW = "FrostpunkCreateTutorialMessageEffect"
SHOW_FLAGS = u32(0)+b"\1"
LESSONS = {
    "gauge": ("Send the first signal",
        "Build a Signal Relay under Tech. Select the Generator and leave its main switch on. Turn on Overdrive to raise the stress gauge into the range in the objective. The relay checks every 15 game minutes. When the objective ticks, switch Overdrive off."),
    "cool": ("Cool the main",
        "Switch Overdrive off and leave the Generator running. Stress falls while it cools."),
    "relay": ("Reconnect the relay",
        "The main trips at 72% stress. Switch Overdrive off until the gauge drops to 25% with a Signal Relay or 14% without one. Loss of heat ends when the line reconnects."),
    "refit": ("Choose a refit",
        "The accumulator recovers stress faster and can transmit to all stations. The isolated return line keeps wards warmer and opens another route with a scout survey."),
    "survey": ("Bring the survey back",
        "Build a Beacon to open Frostland. Form a scout team, visit one of the revealed sites and order the team back to the city. The tracker credits a return during this mission."),
    "watch": ("Send fuel to Broken Mile",
        "A watch is one relief crew's shift at the bend. Keep enough coal for the listed load and the city reserve. Select Send coal on the dispatch order. The goal counts the delivery when it arrives. Send three loads in total.\n\n"
        "A Coal Magazine cuts each load by 20 coal. Repair the leak after the first delivery before sending the next load."),
    "charter": ("Dispatch supplies",
        "Set aside the listed cargo, then approve departure in the dispatch order. The tracker credits the arrival. A brief delay is available whenever you need the stock for the city."),
    "valve_orders": ("Commission the new line",
        "Staff the Valve Works and queue the listed parts in General. The gauges count one test hour whenever the Generator is running in the specified stress band with enough coal. The counter pauses outside the band and keeps its progress. Once the parts and test are ready, choose Install parts."),
    "dispatch_orders": ("Load the last convoy",
        "Staff the Relief Dispatch and queue the orders named in your tracker. Clinic sledges use Wooden Materials as finished cargo. Heavy sledges use Steel Plates. Keep the finished cargo and choose Send supplies when the dispatch order opens."),

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
