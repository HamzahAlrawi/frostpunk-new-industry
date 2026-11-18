"""Count completed buildings that meet the engine's Liveable threshold."""
from .housing_schema import LIVEABLE
from .native_binary import SchemaError, u32
from .native_scenario import compact, compare, integer, typed


SELECTOR = "FrostpunkBuildingsSelector"
TEMPERATURE = "FrostpunkEntityTemperatureLevelComparisonExpression"
FILTER_FLAGS = u32(1)+u32(0)+u32(1)


def temperature(operator, level):
    return typed(TEMPERATURE)+u32(operator)+bytes.fromhex(level)


def count_filter(building, predicate, flags=FILTER_FLAGS):
    return compact("CountExpression", compact(SELECTOR, bytes.fromhex(building)+flags+predicate))


def liveable(building):
    return compare(count_filter(building, temperature(4,LIVEABLE)),4,integer(1))


def verify_native_thermal_checks(events):
    prison = "8ddcfeeca5bfe7a3c3498f20571be72e"
    freezing_limit = "75397e92f7d23598da40dcf076f6d466"
    # Prison consequences use the complete filtered CountExpression.
    cold = compare(count_filter(prison,temperature(3,freezing_limit),bytes(8)+u32(1)),4,integer(1))
    # The snow pit uses the same predicate in the opposite direction.
    warm = (compact(SELECTOR,bytes.fromhex("e6432fcf71e3a7a1794b6d5b5a12f971"))+
            u32(2)+u32(1)+u32(1)+temperature(4,LIVEABLE))
    # A native efficiency check establishes the same constructed-only selector
    # flags in a counted, filtered selector.
    workplace = count_filter("bd4550cdabb594b03342213ab62da19c",
        typed("FloatComparisonExpression")+compact("FrostpunkPlaceEfficiencyExpression")+
        u32(3)+compact("ConstantFloatExpression",bytes.fromhex("0000803e")))
    if not all(sample in events for sample in (cold,warm,workplace)):
        raise SchemaError("Unsupported native building temperature filter")
