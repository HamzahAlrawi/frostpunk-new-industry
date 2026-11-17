"""The native heat-promise objective, with a fixed number of warm homes."""
from .native_binary import Cursor, SchemaError, string, u32
from .native_scenario import integer

HOME = "e8a15ad518cc5bbb134437db2359a858"
LIVEABLE = "7190dbae6f70a6a7c54481b4e09d1889"
COLD = "651581a354fc4f96bc4085482f54610c"
RETURN = "FrostpunkExpeditionReturnedEventTrigger"
ACTIVATE = "FrostpunkBuildingActivationEventTrigger"
BEACON = "99c50bbc0ec952ace541f69166fab316"
OPEN_MAP = string("FrostpunkModifyWorldMapEffect")+bytes.fromhex("01ffffffff000000000000")


def warm_homes(count):
    if not 1 <= count <= 32:
        raise SchemaError("Invalid heated home target")
    return bytes.fromhex(HOME+LIVEABLE)+integer(count)+b"\1\0"


def validate(quests, events):
    marker = string("FrostpunkHeatBuildingOfCategoryQuestObjective")
    home = marker+bytes.fromhex("cf2aa82263eb6aa42c456a3a03fe7f65")
    cursor = Cursor(quests, quests.index(home)+len(home))
    if cursor.count() or cursor.boolean():
        raise SchemaError("Unsupported heat objective gates")
    cursor.string();cursor.string();cursor.take(24)
    if cursor.take(32) != bytes.fromhex(HOME+LIVEABLE):
        raise SchemaError("Wrong native Liveable threshold")
    native = marker+bytes.fromhex("c999a64a17e7b5b14f444ac6388ebe3f")
    start = quests.index(native)
    limit = quests.index(string("FrostpunkSatisfyCitizenNeedQuestObjective"),start)
    block = quests[start:limit]
    if bytes.fromhex(COLD) not in block or not block.endswith(string("ConstantIntegerExpression")+u32(20)+b"\1\0"):
        raise SchemaError("Unsupported heat objective footer")
    donor = string(RETURN)+bytes.fromhex("8b535509ef5b008dca48ef6630f36204")
    if donor+b"\0\0"+u32(1)+string("IntegerComparisonExpression") not in events:
        raise SchemaError("Invalid native expedition-return trigger")
    beacon = string(ACTIVATE)+bytes.fromhex("741b0bc36dd7808953424d0cad0196a8"+BEACON)+u32(0)
    if beacon+u32(2) not in events or OPEN_MAP+string("FrostpunkSwitchEffect") not in events:
        raise SchemaError("Unsupported Beacon world map activation")
