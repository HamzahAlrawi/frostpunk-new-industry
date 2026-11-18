"""Register a playable scenario without changing the original story records."""
from struct import pack
from .native_binary import Cursor, SchemaError, Span, entry, replace_spans, string, u32

NAME = "NI The Last Signal"
ROAD_NAME = "NI Winter Road at Switchback Basin"
FAULTLINE_NAME = "NI The Last Signal Faultline"
DEFAULT = "eab266e3fb82e2b1334c7cc1e953e30f"
DEFAULT_EVENTS = "129eb2986c3cda9fc24f187d61026e53"
NATIVE_INTRO = bytes.fromhex("d29f819b0694f9b81141e8c70117bd28")
NATIVE_WEATHER = bytes.fromhex("a8d3c3f91c5277a0a34a3b1f8cd4a016")
SIMPLE_WEATHER = string("FrostpunkScenarioSimpleWeatherTimeline")
WEATHER_DONOR = SIMPLE_WEATHER + string("Always Clear0") + bytes.fromhex("c96eb26c25e29ba7ac4a2449d2649013")
FROST = (
    "8a4161fce9daa7b70b4cd22e03389555",
    "a60936d531d166b7f04693ff8f5cb847",
    "8ea27b867bcf948a0942a6fda784defa",
    "0a82a1ebbbbd34ada44408a19a38159f",
)
FORECAST = ((1,0),(4,1),(7,2),(10,1),(13,3),(17,2),(20,1))
WINTER = ((1,0),(4,1),(8,2),(11,1),(15,2),(19,3),(23,2),(26,3),(30,2),(33,1))
FAULTLINE = ((1,0),(4,1),(7,2),(10,1),(13,2),(16,3),(20,2),(23,3),(27,2),(30,3),(34,2),(37,3),(41,2),(44,1))


def forecast_record(identity, timeline="Lifeline"):
    forecast = {"Lifeline": FORECAST, "Winter Road": WINTER, "Faultline": FAULTLINE}[timeline]
    title = f"NI {timeline} Forecast"
    timeline = b"".join(pack("<HH",day,0 if day==1 else 7)+bytes.fromhex(FROST[tier])+b"\0"
                        for day,tier in forecast)
    return SIMPLE_WEATHER+string(title)+bytes.fromhex(identity)+b"\0\0"+u32(len(forecast))+timeline


def register(data, identity, event_directory, localize, winter):
    from winter_road_maps import NATIVE_CITY, NATIVE_WORLD, insert_map_setups
    count = Cursor(data, 16).count(32)
    begin = 20
    end = data.index(b"\1" + string("Endless Canyon"), begin)
    donor = data[begin:end]
    marker = entry("DEFAULT", DEFAULT)
    if count != 14 or not donor.startswith(marker):
        raise SchemaError("Unsupported story scenario vector")
    body = donor[len(marker):]
    intro = body.index(NATIVE_INTRO)
    if (body[:14] != b"\1\1" + u32(0)*2 + u32(2)
            or body[46:50] != u32(1) or body[66:79] != u32(1)+string("default")
            or body[95:99] != u32(4) or intro != 0xd4):
        raise SchemaError("Unsupported Default scenario flags or links")
    old_events = u32(1) + bytes.fromhex(DEFAULT_EVENTS)
    if body[intro+16:intro+36] != old_events:
        raise SchemaError("Unsupported Default events setup link")
    if body[0x102:0x112]!=NATIVE_WEATHER or any(bytes.fromhex(variant) not in data for variant in FROST):
        raise SchemaError("Unsupported native weather link")
    forecast=data.index(WEATHER_DONOR)
    weather_count=Cursor(data,forecast-4).count(128)
    if weather_count!=66 or data[forecast+len(WEATHER_DONOR):forecast+len(WEATHER_DONOR)+27]!=(
        b"\0\0"+u32(1)+u32(1)+bytes.fromhex(FROST[0])+b"\0"):
        raise SchemaError("Unsupported weather timeline vector")
    edits = [
        (Span(1, 2), b"\0"),
        (Span(10, 79), u32(0)*3),
        (Span(95, 163), u32(0)),
        (Span(intro, intro+16), bytes(16)),
        (Span(intro+16, intro+36), u32(1)+bytes.fromhex(identity("event-setup"))),
    ]

    def campaign_text(prefix, name, description, weather):
        labels = [(Span(0x102,0x112),bytes.fromhex(weather))]
        for suffix,label in (("DisplayName",name),("Description",description)):
            old = string("@Generated/ScenariosConfig/Scenarios/DEFAULT/"+suffix)
            at = body.index(old)
            labels.append((Span(at,at+len(old)),localize(prefix+"/Menu/"+suffix,label)))
        return labels

    road_text = campaign_text("LastSignal","The Last Signal: Winter Road",
        "Save the stranded convoys, build a city for their people, and hold its streets through the Long Night.",winter)
    name = entry(NAME, identity("scenario"))
    if body[399:415] != bytes.fromhex(NATIVE_CITY) or body[422:438] != bytes.fromhex(NATIVE_WORLD):
        raise SchemaError("Unsupported Default city or Frostland binding")
    # Keep both original map bindings for existing saves while exposing the
    # separate city and world setup only to newly started Winter Road games.
    legacy = name + replace_spans(body, edits + road_text + [(Span(0, 1), b"\0")])
    map_edits = [
        (Span(399, 415), bytes.fromhex(identity("city-setup"))),
        (Span(422, 438), bytes.fromhex(identity("world-setup"))),
    ]
    scenario = entry(ROAD_NAME, identity("switchback-scenario")) + replace_spans(body, edits + road_text + map_edits + [(Span(0,1),b"\0")])
    faultline = identity("faultline-forecast")
    faultline_text = campaign_text("Faultline","The Last Signal: Faultline",
        "Race the frost. Route the city's steam, operate the Generator in pressure cycles, and keep the remote shelters on the line.",faultline)
    new_scenario = entry(FAULTLINE_NAME,identity("faultline-scenario"))+replace_spans(body,edits+faultline_text+map_edits)
    population_count = data.index(entry("Default", "abffde98fc17e8921d495b49e5928974"))
    footer_token = entry("Default", DEFAULT_EVENTS)
    pos = data.index(footer_token, end, population_count)
    setup_count = pos-4
    old_setup = Cursor(data, pos)
    old_setup.entry()
    if old_setup.count(16) != 5 or Cursor(data, setup_count).count(32) != 8:
        raise SchemaError("Unsupported native events setup directory")
    old_setup.take(16*5)
    new_setup = entry(NAME, identity("event-setup")) + u32(1) + bytes.fromhex(event_directory)
    # The stock story's first slot and all native entries stay byte-identical.
    revised = replace_spans(data, [
        (Span(16, 20), u32(count+3)),
        (Span(setup_count, setup_count+4), u32(9)),
        (Span(setup_count, setup_count), legacy+scenario+new_scenario),
        (Span(old_setup.position, old_setup.position), new_setup),
        (Span(forecast-4,forecast),u32(weather_count+3)+forecast_record(identity("forecast"))+
            forecast_record(winter,"Winter Road")+forecast_record(faultline,"Faultline")),
    ])
    return insert_map_setups(revised, identity, localize)
