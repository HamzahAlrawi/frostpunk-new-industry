"""Register Faultline's movie and direct city replay using native elements."""
from pathlib import Path

from tools.native_binary import Cursor, SchemaError, Span, entry, f32, replace_spans, string, u32
from tools.story_schema import NATIVE_INTRO


CONFIG = "configs/frostpunkcinematicsconfig.bin"
CINEMA = "NI Faultline Opening"
MOVIE = "faultline_opening_wide"
VIDEO = MOVIE+".ogv"
DONOR = "logo_11bit_wide.ogv"
DIRECTORY = entry("MainScenario","ab2e62ce4d0126bab64492bc81c4a46a")
INTRO = entry("Intro-Cinematic",NATIVE_INTRO.hex())
NEUTRAL = entry("Endlog - neutral","61e149c3164a1ea62146a5a85d5af1d4")
VIDEO_ELEMENT = string("FrostpunkCinematicVideoElement")+bytes(4)
TIMELAPSE_CONFIG = "configs/frostpunktimelapseconfig.bin"
REPLAY_NAME = "NI Faultline City Replay"
RECORDING = "5ae0f465a1091287a34c952ac1765dc8"
PLAYBACK = "f32be631d716db8ea74a1f505819218e"
STOCK_REPLAY = "10840b19f7ad60aed7428c41621645fd"
VICTORY = "a9de3813fff72fb15743819f6887629b"
UNLIMITED = "Main - Single segment unlimited"
REFERENCE = entry("Endlog - full timeline test",STOCK_REPLAY)
REFERENCE_END = entry("Endlog - multiple segments test","f9c37ec2e505cb86d044fc3f6192a8e8")


def reference_replay(native):
    start=native.index(REFERENCE)+len(REFERENCE)
    end=native.index(REFERENCE_END,start)
    return native[start:end]


def city_replay(native, timelapse, uid):
    segment = entry(UNLIMITED,RECORDING)+b"\0"
    player = entry(UNLIMITED,PLAYBACK)+u32(1)+bytes.fromhex(RECORDING)
    if segment not in timelapse or player not in timelapse:
        raise SchemaError("The replay must use the same unlimited segment that Faultline records")
    raw=Cursor(reference_replay(native))
    if raw.u32()!=19 or raw.string()!="FrostpunkCinematicSequenceElement" or raw.f32()!=0:
        raise SchemaError("Unsupported native victory sequence header")
    if raw.string()!="VictoryLong" or not raw.boolean():
        raise SchemaError("Unsupported native victory sequence body")
    methods = (
        ("FadeInOut",22,22), ("PreloadTimelapse",20,22), ("ToggleTimerMode",5,0),
        ("PlayPreloadedTimelapse",21,.05), ("PlaySound",20,1), ("FadeInOut",22,1.1),
        *(("BasketSlot",20,time) for time in (7.7,14,32,45.5,58,71,80.6)),
        ("FadeInOut",22,86), ("BasketSlot",20,90.25), ("StopSound",8,95),
        ("FadeInOut",22,99), ("ToggleTimerMode",5,0),
    )
    records=[]
    for index,(name,length,time) in enumerate(methods):
        label="FrostpunkCinematic"+name+"Element"
        if raw.string()!=label or raw.take(4)!=f32(time):
            raise SchemaError("Unsupported replay element "+label)
        body=raw.take(length-4)
        if name=="PreloadTimelapse" and body!=bytes.fromhex(PLAYBACK):
            raise SchemaError("Unsupported replay profile")
        if name=="BasketSlot" or time==86:
            continue
        # The native lead-in holds a black frame before preloading at second
        # 22. Remove the live flyover and begin both steps at the entry point.
        records.append(string(label)+f32(0 if index<2 else time)+body)
    if raw.position!=len(raw.data):
        raise SchemaError("Unexpected native replay tail")
    return entry(REPLAY_NAME,uid)+u32(len(records))+b"".join(records)


def build(native, timelapse, intro, replay):
    directory = native.index(DIRECTORY)+len(DIRECTORY)
    count=Cursor(native,directory).count(20)
    start=native.index(INTRO,directory)
    end=native.index(NEUTRAL,start)
    body=native[start+len(INTRO):end]
    original=VIDEO_ELEMENT+string("intro_wide")+string("UI/IntroSubtitles/Main")
    if count!=12 or not body.startswith(u32(3)) or not body.endswith(original):
        raise SchemaError("Unsupported stock intro movie entry")
    revised=entry(CINEMA,intro)+body[:-len(original)]+VIDEO_ELEMENT+string(MOVIE)+string(None)
    revised+=city_replay(native,timelapse,replay)
    at = directory+4
    return replace_spans(native,[(Span(directory,at),u32(count+2)),(Span(at,at),revised)])


def video_file():
    data=(Path(__file__).parent/"media"/VIDEO).read_bytes()
    if not data.startswith(b"OggS") or b"\x80theora" not in data[:512] or b"\x01vorbis" not in data[:512]:
        raise SchemaError("The Faultline movie must have Theora and Vorbis tracks")
    return data
