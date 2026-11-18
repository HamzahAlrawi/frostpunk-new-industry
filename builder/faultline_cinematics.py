"""Compose native camera timelines over Switchback Basin's scene objects."""
from struct import pack

from tools.native_binary import SchemaError, f32, string, u32
from tools.native_scenario import typed
from winter_road_maps import translation


ARCHIVE_KEY = 0x13bf7038
ASSET = "faultline-sequences"
SIGNAL = "FrostpunkSequenceSignalEventTrigger"
SHOTS = {
    # Use the stock aerial framing around the Generator rather than the
    # authoring-only Camera1/Camera2 markers buried in the Points terrain.
    "FirstCall": (7.5,(233,135,60),(131,151,56),"FAULTLINE\nThree knocks beneath the ice"),
    "Fracture": (6.0,(155,124,62),(209,112,59),"THE MAIN HAS SPLIT\nThe ridge shelters are cut off"),
    "NightWatch": (6.5,(182,149,67),(128,134,57),"BROKEN MILE\nThree relief crews await fuel"),
    "DawnBasin": (7.5,(141,136,60),(223,155,68),"A LIGHT IN THE BASIN\nSomewhere to come home to"),
    "DawnSignal": (7.5,(137,152,57),(231,135,64),"THE SIGNAL HOLDS\nThe shelters answer across the ridge"),
    "DawnAccord": (8.0,(129,134,58),(233,146,71),"THE BASIN ACCORD\nOne line, kept open together"),
}


def sequence_name(key):
    return "NI_Faultline_" + key


def play(key):
    return typed("FrostpunkStartSequenceEffect") + string(sequence_name(key)) + u32(0)


def signal(key, guid):
    return guid("faultline/cinematic/"+key).hex()


def action(kind, payload=b"", start=0, duration=0.1, extent=None):
    timeline = pack("<3f", duration, start, start+duration if extent is None else extent)
    return typed("SequenceAction"+kind) + timeline + bytes(5) + payload


def track(*actions):
    return u32(1)+u32(len(actions))+b"".join(actions)


def camera(target, coordinates):
    distance, azimuth, height = coordinates
    return pack("<IffIff", 0xffffffff, distance, azimuth, 1, height, 0) + bytes(3) + target


def fade(reveal, start, duration):
    return action("Fade", bytes([reveal])+bytes(6)+b"\xff"+f32(1), start, duration)


def scene_anchor(scene, name):
    translation(scene, name, "0293725008399bab68477356f99c43b9")
    after_name = scene.index(name.encode()+b"\0")+len(name)+1
    target = scene[after_name:after_name+16]
    if scene.count(target) != 2:
        raise SchemaError(f"Expected a unique camera target: {name}")
    return target


def build(native, city, events, guid, localize):
    intro = b"\1"+string("ENDLESS_Intro")
    start = native.index(intro)
    donor = native[start:native.index(b"\1"+string("ENDLESS_Monument"),start)]
    anchor = bytes.fromhex("cbd3bf91e10d9bab244c9f34d0d155d8")
    sound = bytes.fromhex("07005ab9b31523a363475ac5699a93b700")+bytes(17)
    samples = (
        action("Fade", b"\0"*7+b"\xff"+f32(1), duration=0, extent=0.1),
        action("StoreCameraLocation", duration=0, extent=0.6),
        action("SetCameraPosition", camera(anchor,(233,135,60)), duration=0, extent=3),
        action("SetCameraLookAt", b"\0"+anchor+f32(0), duration=0, extent=0.4),
        action("EaseCameraPosition", camera(anchor,(117,135,52))[:22]+anchor, duration=10.3, extent=10.3),
        action("PlaySound", sound, duration=9.5, extent=9.5),
    )
    native_footer = b"\1"+string("GENRAL")+u32(0)+b"\1\0"+f32(5)+f32(45000)
    # Statically check every writable parameter layout against the shipped
    # sequence, including grouped tracks, and the event playback signature.
    play_donor = typed("FrostpunkStartSequenceEffect")+string("BeaconUp")+u32(0)
    native_signal = bytes.fromhex("2cfb09f5f05796adf64b5ca64e70ae71")
    checks = {
        "intro actions": all(sample in donor for sample in samples),
        "footer": native_footer in native,
        "playback": play_donor in events,
        "directory count": native[:4]==u32(152),
        "signal trigger": any(events[p+16:p+32]==native_signal for p in signal_offsets(events)),
        "signal action": action("EmitSignal",native_signal,1,0,3) in native,
        "caption": action("ShowSequenceMessage",b"\0"+string("UI/EndMessages/TechHavenEnd"),1,5,5) in native,
        "cinematic HUD": action("SetVisibleSequenceHUD",b"\1\0\1\0",1,0,3) in native,
    }
    if missing:=[name for name,match in checks.items() if not match]:
        raise SchemaError("Unsupported native cinematic layout: "+", ".join(missing))
    records = []
    target = scene_anchor(city,"Generator_000")
    for key,(seconds,opening,closing,caption) in SHOTS.items():
        caption_key = localize("Faultline/Cinematic/"+key,caption).replace(b"\1@",b"\1",1)
        fade_out = seconds-1.45
        reveal = seconds-0.8
        tracks = (
            track(fade(False,0,0.25), fade(True,0.28,0.65),
                  fade(False,fade_out,0.45), fade(True,reveal,0.62)),
            track(action("StoreCameraLocation", duration=0, extent=0.58),
                  action("RestoreCameraLocation", b"\1\0",fade_out+0.46,0.16)),
            track(action("SetCameraPosition", camera(target,opening),0.25,0,0.48),
                  action("EaseCameraPosition", camera(target,closing)[:22]+target,0.35,fade_out-0.25)),
            track(action("SetCameraLookAt", b"\0"+target+f32(0),0.25,0,0.65)),
            track(action("SetVisibleGameHUD",b"\1\0",0.2,0.3),
                  action("SetVisibleGameHUD",b"\0\1",reveal,0.35)),
            track(action("SetVisibleSequenceHUD",b"\1\0\1\0",0.45,0,3),
                  action("SetVisibleSequenceHUD",b"\0\0\0\0",reveal,0,seconds)),
            track(action("ShowSequenceMessage",b"\0"+caption_key,1.0,4,4)),
            track(action("PlaySound",sound,0.32,seconds-0.4)),
            track(action("EmitSignal",bytes.fromhex(signal(key,guid)),seconds-0.1,0,seconds)),
        )
        records.append(b"\1"+string(sequence_name(key))+u32(len(tracks))+b"".join(tracks)+native_footer)
    return u32(152+len(records))+b"".join(records)+native[4:]


def signal_offsets(events):
    marker = typed(SIGNAL)
    start = events.find(marker)
    while start != -1:
        yield start+len(marker)
        start = events.find(marker,start+len(marker))
