"""On-demand Faultline lessons using the native tutorial message panel."""
from tools.native_binary import Cursor, SchemaError, string, u32
from tools.native_scenario import append_directory, typed


PATH = "configs/frostpunkmessagesconfig.bin"
MESSAGE = "FrostpunkTutorialMessageEntry"
SHOW = "FrostpunkCreateTutorialMessageEffect"
SHOW_FLAGS = u32(0)+b"\1"
LESSONS = {
    "gauge": ("Pressure and Overdrive",
        "Select the Generator to see its stress gauge. The main switch supplies heat. Overdrive is a separate switch "
        "that makes stress climb. Switch Overdrive off to lower stress while keeping the Generator itself running.\n\n"
        "A circuit is the route you send steam through. Read your chosen route's heat and workplace effects. "
        "Follow the numbered steps in the objective tracker, and slow the game down while adjusting the gauge."),
    "cool": ("A pulse has gone through",
        "A pulse is a short burst of steam. When the hourly check sees stress inside the specified band, "
        "the line sends it automatically and the gauge drops by the listed amount. A band is a range, not an exact number.\n\n"
        "Turn Overdrive off now. Wait for the cooling step in the tracker to finish. Then turn it back on for the next pulse."),
    "relay": ("Commission a Signal Relay",
        "Find Signal Relay under Tech in the construction menu. It is available as soon as the city starts. "
        "It warms a small area while the Generator runs. Once built, it also lets a tripped main reconnect at 20% stress instead of 14%.\n\n"
        "A trip is a safety shutdown of the main at 72% stress. Buildings lose two heat levels until the circuit reconnects. "
        "Turn off Overdrive and let the gauge fall. The current pressure job keeps its progress."),
    "refit": ("Refits, the accumulator and the bypass",
        "A refit is a permanent change to the pipework. The pressure accumulator lets stress fall faster with Overdrive off "
        "and opens a shorter route for the second signal. The isolated bypass keeps clinics warmer. Its route for the second "
        "signal also needs a survey brought home by scouts."),
    "survey": ("Bring the survey back",
        "Build a Beacon to open Frostland. Form a scout team, send it to a revealed site, then order the team back to the city. "
        "The survey counts when scouts return during this job. Explore nearby salvage sites to make the trip pay for itself."),
    "watch": ("Keep a fuel watch",
        "A watch is a series of hourly checks. Keep the Generator on, stress inside the band in the tracker, and enough coal "
        "in storage to fund the shipment and leave the city's reserve. Losing any of these resets the current watch. "
        "Coal already delivered still counts.\n\n"
        "Under Resources, build a Coal Magazine and assign it to coal for storage. A completed Magazine cuts the cost of each "
        "dispatch by 20 coal. When the leak interrupts the watch, choose a repair and wait for the heat penalty to lift."),
    "charter": ("Send the charter supplies",
        "A charter is the final agreement with the shelters. Its listed supplies are sent once, automatically, once stock "
        "and any required pressure steps are ready. The job still needs its other city objectives. "
        "Completing the watches opens the permanent supply plan. Resettlement remains available after a missed watch."),
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
