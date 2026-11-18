"""Build Switchback Basin and its Frostland routes from installed scene assets."""
import re
import struct
from math import dist

from tools.native_binary import Cursor, SchemaError, Span, entry, string, u32, replace_spans
from tools.native_scenario import compact, compare, integer, typed
from tools.housing_schema import BEACON


CITY_DONOR = "CityMaps/ENDLESS_MODE/Endless_Points"
WORLD_DONOR = "WorldMaps/FrostpunkSceneDEFAULTRandomized"
CITY = "CityMaps/WINTER_ROAD/SwitchbackBasin"
WORLD = "WorldMaps/WinterRoadSwitchbackBasinRoutes"
NATIVE_CITY = "eb1b019c86b4399bc34e66f56220f77c"
NATIVE_WORLD = "bc862bc3dc8b95ae614945068c33a9ff"
POINTS = "e32978b8909c368a5846bf8dd2367aa0"
WORLD_GROUP = "75d4d6a237fd4abb0b4f8a45d0ea9907"
PLACEMENTS = (
    ("RES_Pickable_Wood_004", "RES_Pickable_Steel_001"),
    ("RES_Pickable_Wood_002", "RES_Pickable_Coal_004_015"),
    ("RES_Pickable_Wood_000", "RES_Pickable_Coal_004_003"),
    ("RES_Pickable_Steel_000", "RES_Pickable_Coal_004_000"),
    ("RES_Pickable_Steel_002", "RES_Pickable_Coal_004_002"),
)
# Each of these sites uses the native salvage interaction and can be looted once.
SITES = (
    ("DefaultRandomizationPoint_000", "0061e4cb23f4f4b1144bf630cfbcbbbc", "Snow-covered Supplies", "01"),
    ("DefaultRandomizationPoint_004", "dbc9ce79407f5ea21e40a8ecad11519d", "Abandoned Sawmill", "04"),
    ("DefaultRandomizationPoint_005", "d50c9b355e4e3394fa4f71e4a96fe43d", "Salvage site", "05"),
)
LEGACY_POINTS = ('000', '001', '002', '004', '005', '006')
LEGACY_TEMPLATES = ('5260c3c49e6b05a7704be91e9b516d37', '2a6e69ebb22864b46f435297358d5e0f')
SELECT = typed("FrostpunkSelectEffect")
REVEAL = typed("FrostpunkRevealWorldMapEntityEffect")
BY_NAME = "FrostpunkEntitiesByNameSelector"
BY_SITE = "FrostpunkExpeditionSitesSelector"
OBJECT_HEADER = bytes.fromhex("14ebe45c65000000ffffffff0100000001000000")
TRANSFORM_FIELD = struct.Struct("<4f")
WORLD_COMPONENT = "a3b0c0fadf0565a260424b45b5db5823"
RANDOM_POINT = bytes.fromhex("a1b1cb73255cf599224f9df06ba9632a")
RANDOMIZATION = typed("FrostpunkWorldMapRandomizationComponentTemplate")


def select_name(name, effect):
    return SELECT + compact(BY_NAME, string(name) + bytes(7) + u32(1) + effect)


def reveal_site(identity):
    return SELECT + compact(BY_SITE, bytes.fromhex(identity) + bytes(7) + u32(1) + REVEAL)


def beacon_exists():
    buildings = compact("FrostpunkBuildingsSelector", bytes.fromhex(BEACON) + b"\1" + bytes(11))
    return compare(compact("CountExpression", buildings), 4, integer(1))


def validate_native_map_effects(events):
    samples = (
        beacon_exists(),
        select_name("DefaultRandomizationPoint_016", REVEAL),
        SELECT + compact(BY_SITE, bytes.fromhex("c4c959314313c585be451c2b775a206a") + bytes(7) + u32(2) + REVEAL),
    )
    if not all(sample in events for sample in samples):
        raise SchemaError("Unsupported native Frostland spawn or reveal layout")


def translation(data, label, component):
    """Find the unique object instance and its row-vector affine translation."""
    key = label.encode() + b"\0"
    locations = []
    for match in re.finditer(re.escape(key), data):
        end = match.end()
        identity = data[end:end+16]
        if data.count(identity) == 2:
            prefix = data.find(identity, end+16)
            if data[prefix+28:prefix+44] == bytes.fromhex(component):
                locations.append(prefix+111)
    if len(locations) != 1:
        raise SchemaError(f"Ambiguous scene object: {label}")
    offset, = locations
    vector = TRANSFORM_FIELD.unpack_from(data, offset)
    if not 0.99 <= vector[3] <= 1.01 or any(abs(value) > 9000 for value in vector[:3]):
        raise SchemaError(f"Unsupported scene translation: {label}")
    return offset, vector


def renamed(data, original, name):
    if not data.startswith(OBJECT_HEADER + string(original)) or len(name) != len(original):
        raise SchemaError(f"Unsupported scene header: {original}")
    start = len(OBJECT_HEADER)
    return data[:start] + string(name) + data[start+len(string(original)):]


def fixed_site(data, point, template_id, transform):
    """Use a scene-placed site, with no native randomization override."""
    name = data.index(point.encode()+b"\0")
    begin = name-19
    if data[begin-16:begin] != bytes.fromhex(WORLD_COMPONENT) or data[begin:begin+16] != RANDOM_POINT:
        raise SchemaError(f"Unsupported random point template: {point}")
    start = data.index(RANDOMIZATION, transform+TRANSFORM_FIELD.size)-4
    if start-transform != 93 or data[start:start+4] != u32(1):
        raise SchemaError(f"Unexpected random point override location: {point}")
    cursor = Cursor(data, start+4+len(RANDOMIZATION))
    cursor.guid()
    if cursor.count(8) != 1:
        raise SchemaError(f"Unsupported random point group: {point}")
    cursor.guid()
    if cursor.u32() != 0:
        raise SchemaError(f"Unexpected extra random point groups: {point}")
    for _ in range(cursor.count(8)):
        if not cursor.string().startswith("DefaultRandomizationPoint_"):
            raise SchemaError(f"Unexpected random point connection: {point}")
    if cursor.take(12) != struct.pack("<3f",1,1,1):
        raise SchemaError(f"Unexpected random point override footer: {point}")
    return ((Span(begin,begin+16),bytes.fromhex(template_id)), (Span(start,cursor.position),u32(0)))


def build_scenes(read_owned):
    city = read_owned("scenes", CITY_DONOR.lower()+".binaryscene")
    world = read_owned("scenes", WORLD_DONOR.lower()+".binaryscene")
    city_component = "0293725008399bab68477356f99c43b9"
    _, generator = translation(city, "Generator_000", city_component)
    revised = bytearray(renamed(city, CITY_DONOR, CITY))
    piles = {}
    for left, right in PLACEMENTS:
        left_at, left_position = translation(city, left, city_component)
        right_at, right_position = translation(city, right, city_component)
        if abs(left_position[1] - right_position[1]) > 0.01:
            raise SchemaError("Opening resource placement is not on the basin floor")
        for name, offset, position in ((left, left_at, right_position), (right, right_at, left_position)):
            TRANSFORM_FIELD.pack_into(revised, offset, *position)
            piles[name] = [round(value, 2) for value in position[:3]]
    if any(min(dist(generator[:3], p) for name, p in piles.items() if material in name) > 95
           for material in ("Coal", "Steel", "Wood")):
        raise SchemaError("Generator has no nearby source of an opening resource")
    sites = []
    _, home = translation(world, "City_000", WORLD_COMPONENT)
    site_edits = []
    for point, template_id, label, donor_id in SITES:
        offset, position = translation(world, point, WORLD_COMPONENT)
        path = f"gameentities/worldmap/expeditionsites/_shared/[t-plain]resources{donor_id}.binarytemplate"
        donor = read_owned("templates", path)
        if not donor.startswith(bytes.fromhex(template_id)) or string("FrostpunkExpeditionSiteComponentTemplate") not in donor:
            raise SchemaError(f"Unsupported salvage site donor: {path}")
        site_edits.extend(fixed_site(world, point, template_id, offset))
        sites.append(dict(point=point, template=template_id, name=label, position=list(position[:3]),
                          distance=round(dist(home[:3], position[:3]))))
    if not all(600 < s["distance"] < 3000 for s in sites):
        raise SchemaError("Opening scout sites must be within range of the city")
    scenes = {
        CITY.lower()+".binaryscene": (CITY_DONOR.lower()+".binaryscene", bytes(revised)),
        WORLD.lower()+".binaryscene": (WORLD_DONOR.lower()+".binaryscene",
                                        renamed(replace_spans(world,site_edits), WORLD_DONOR, WORLD)),
    }
    for target, donor in ((CITY, CITY_DONOR), (WORLD, WORLD_DONOR)):
        original = donor.lower()+".gi"
        scenes[target.lower()+".gi"] = (original, read_owned("scenes", original))
    return scenes, dict(name="Switchback Basin", city=CITY, world=WORLD, piles=piles, sites=sites)


def insert_map_setups(data, identity, localize):
    default_city = entry("Default", NATIVE_CITY)
    start = data.index(default_city+string("CityMaps/FrostpunkSceneDEFAULT"))
    points = Cursor(data, data.index(entry("Endless_Points", POINTS)))
    points.entry()
    if points.string() != CITY_DONOR or points.count(4) != 3 or points.string() != "Var1":
        raise SchemaError("Unsupported Points city setup")
    variant = points.take(23)   # GUID, weight and native variant flags.
    if variant[16:] != struct.pack("<f", 1) + bytes(3):
        raise SchemaError("Unsupported Points variation")
    city = (entry("NI Switchback Basin", identity("city-setup")) + string(CITY) + u32(1) + string("Var1")
            + bytes.fromhex(identity("city-variant")) + variant[16:]
            + localize("LastSignal/Map/Name", "Switchback Basin")
            + localize("LastSignal/Map/Description", "A divided basin below the winter road."))

    world_prefix = entry("Story Randomized", NATIVE_WORLD) + string(WORLD_DONOR)
    at = data.index(world_prefix)
    rand = Cursor(data, at+len(world_prefix))
    if rand.count(2) != 2 or rand.string() != "Random A":
        raise SchemaError("Unsupported Frostland map setup")
    rand.guid()
    if rand.count(4) != 1 or rand.guid() != WORLD_GROUP or rand.u32() != 0:
        raise SchemaError("Unsupported Frostland site-set link")
    rand.string()
    if rand.string() is not None:
        raise SchemaError("Unexpected native world variation description")
    world = (entry("NI Switchback Frostland", identity("world-setup")) + string(WORLD) + u32(1) + string("Random A")
             + bytes.fromhex(identity("world-variant")) + u32(0)*2
             + localize("LastSignal/Map/Route", "Winter Road scouting routes") + string(None)
             + localize("LastSignal/Map/World", "Switchback Frostland")
             + localize("LastSignal/Map/WorldDescription", "Three salvage routes lead out from the city.")
             + b"\0")
    world_start = data.index(entry("Refugees", "e56253859755dc8b364092403628c7ef") + string("WorldMaps/WorldMapRefugees"))
    if Cursor(data, start-4).count(64) != 30 or Cursor(data, world_start-4).count(64) != 19:
        raise SchemaError("Unsupported scene setup directories")
    return replace_spans(data, ((Span(start-4,start),u32(31)+city),
                                (Span(world_start-4,world_start),u32(20)+world)))
