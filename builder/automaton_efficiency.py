"""Apply workplace research to the engine's human and automaton work roles."""
import struct


ROLE_WORKPLACE_BONUSES = {
    "CoalMineOutput3", "MedicalEfficiency2", "FieldDressings", "WardProtocols", "CropRotation", "SeedSelection2",
    "WorkshopBench", "WorkshopSpeed1", "WorkshopSpeed2", "WorkshopSpeed3", "InfirmaryRounds",
    "EdgeWarehouseSorting", "EdgeWarehouseWinches", "EdgeMealPrep", "EdgeClinicRotas", "EdgeKilnCrews", "EdgeCoalCrews",
    "MasteryPrepBenches", "MasteryKilnRotas", "MasteryIrrigation", "MasteryClinicRotas",
    "MasteryProvisionLines", "MasteryFactoryLines", "MasteryFuelDistrict", "InfirmaryRecoveryWards",
    "SteelworksShiftTeams",
}


def workplace_offset(payload):
    # In this place-modifier layout the optional display string starts at byte 25.
    if len(payload) < 238 or payload[25] not in (0, 1):
        return None
    shift = payload.index(0, 26) - 25 if payload[25] else 0
    return 72 + shift if len(payload) == 238 + shift else None


def split_workplace_efficiency(payload):
    # A native Agitator writes role 0, and Medical Automaton Integration writes role 1.
    efficiency = workplace_offset(payload)
    assert efficiency is not None
    factor, condition_count, role_count, human, automaton = struct.unpack_from("<fIIff", payload, efficiency)
    assert 1.0 < factor <= 1.5 and (condition_count, role_count, human, automaton) == (0, 2, 1.0, 1.0)
    # Neutralize the general field so each work role receives the research bonus once.
    roles = struct.pack("<fIIff", 1.0, 0, 2, factor, factor)
    return payload[:efficiency] + roles + payload[efficiency + len(roles):]


def raise_workplace_research(payload, description):
    """Raise positive permanent workplace multipliers, including specialized roles."""
    if payload[:12] != struct.pack("<IfI", 0, -1.0, 2):
        return payload, description
    offset = workplace_offset(payload)
    if offset is None:
        return payload, description
    factor, conditions, count, human, automaton = struct.unpack_from("<fIIff", payload, offset)
    if (conditions, count) != (0, 2):
        return payload, description
    active = {value for value in (factor, human, automaton) if 1.0 < value < 1.75}
    if not active:
        return payload, description
    original, = active
    percentage = f"{round((original - 1.0) * 100)}%"
    assert description.count(percentage) == 1, description
    factor, human, automaton = (1.75 if value == original else value for value in (factor, human, automaton))
    fields = struct.pack("<fIIff", factor, conditions, count, human, automaton)
    return payload[:offset] + fields + payload[offset+20:], description.replace(percentage, "75%")
