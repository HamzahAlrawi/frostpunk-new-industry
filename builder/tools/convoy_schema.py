"""Native citizen arrivals, using the shipped Survivor appearance records."""
from .native_binary import SchemaError, i32, string, u32

APPEARANCE = {
    "well": "42bffe581b3e7782154e5275aea4849d",
    "ill": "d39cb11b88d53b97a841032cccef39f1",
}
ROLES = {
    "workers": "35f253d13457b6b9734cc39318b268e9",
    "engineers": "61f133978a5e9e84af48b6fe6ef2e6ea",
    "children": "afd04dda565f618d214d07e72f6f74c1",
}


def arrive(quantity, role, health="well"):
    if not 0 < quantity <= 60:
        raise SchemaError("Unsupported size for a convoy group")
    return (string("FrostpunkCreateAgentEffect") + i32(quantity)
            + bytes.fromhex(APPEARANCE[health] + ROLES[role]) + u32(0))


def validate_arrivals(events):
    fixture = b"".join(arrive(count, role) for role, count in
                       (("workers", 60), ("children", 30), ("engineers", 30)))
    # The native stress-test convoy uses 60 of its first group. The rest
    # of its bytes match the production schema, including the final vector.
    if fixture not in events or arrive(50, "workers", "ill") not in events:
        raise SchemaError("Unsupported native survivor effect layout")
