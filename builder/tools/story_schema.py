"""Register a playable scenario without changing the original story records."""
from .native_binary import Cursor, SchemaError, Span, entry, replace_spans, string, u32

NAME = "NI The Last Signal"
DEFAULT = "eab266e3fb82e2b1334c7cc1e953e30f"
DEFAULT_EVENTS = "129eb2986c3cda9fc24f187d61026e53"
NATIVE_INTRO = bytes.fromhex("d29f819b0694f9b81141e8c70117bd28")


def register(data, identity, event_directory, localize):
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
    edits = [
        (Span(1, 2), b"\0"),
        (Span(10, 79), u32(0)*3),
        (Span(95, 163), u32(0)),
        (Span(intro, intro+16), bytes(16)),
        (Span(intro+16, intro+36), u32(1)+bytes.fromhex(identity("event-setup"))),
    ]
    for suffix, label in (
        ("DisplayName", "The Last Signal"),
        ("Description", "Three settlements call through the storm. Route scarce heat between districts, keep your promises, and decide who inherits the last working relay."),
    ):
        old = string("@Generated/ScenariosConfig/Scenarios/DEFAULT/"+suffix)
        at = body.index(old)
        edits.append((Span(at, at+len(old)), localize("LastSignal/Menu/"+suffix, label)))
    name = entry(NAME, identity("scenario"))
    scenario = name + replace_spans(body, edits)
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
    return replace_spans(data, [
        (Span(16, 20), u32(count+1)),
        (Span(setup_count, setup_count+4), u32(9)),
        (Span(setup_count, setup_count), scenario),
        (Span(old_setup.position, old_setup.position), new_setup),
    ])
