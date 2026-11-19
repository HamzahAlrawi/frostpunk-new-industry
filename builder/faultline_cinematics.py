"""Clone the stock scenario-movie entry and bind the original Faultline film."""
from pathlib import Path

from tools.native_binary import Cursor, SchemaError, Span, entry, replace_spans, string, u32
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


def intro_movie(native, uid):
    directory = native.index(DIRECTORY)+len(DIRECTORY)
    count=Cursor(native,directory).count(20)
    start=native.index(INTRO,directory)
    end=native.index(NEUTRAL,start)
    body=native[start+len(INTRO):end]
    original=VIDEO_ELEMENT+string("intro_wide")+string("UI/IntroSubtitles/Main")
    if count!=12 or not body.startswith(u32(3)) or not body.endswith(original):
        raise SchemaError("Unsupported stock intro movie entry")
    revised=entry(CINEMA,uid)+body[:-len(original)]+VIDEO_ELEMENT+string(MOVIE)+string(None)
    at = directory+4
    return replace_spans(native,[(Span(directory,at),u32(count+1)),(Span(at,at),revised)])


def video_file():
    data=(Path(__file__).parent/"media"/VIDEO).read_bytes()
    if not data.startswith(b"OggS") or b"\x80theora" not in data[:512] or b"\x01vorbis" not in data[:512]:
        raise SchemaError("The Faultline movie must have Theora and Vorbis tracks")
    return data
