"""The native technology-state predicate used by cumulative tooltip sources."""
import struct


TECHNOLOGY_CHECK = b'\1FrostpunkTechnologyIsResearchedExpression\0'


def split_technology_condition(body):
    """Return our predicate and a scalar view with an empty condition vector.

    Other native expressions are left intact. Callers comparing effects must
    retain the returned predicate as well as the scalar values.
    """
    if body[:4] != struct.pack('<I',1) or not body.startswith(TECHNOLOGY_CHECK,4):
        return None,body
    p=4+len(TECHNOLOGY_CHECK)
    assert len(body)>=p+17 and body[p+16] in (0,1)
    predicate=dict(technology=body[p:p+16].hex(),inverted=bool(body[p+16]))
    return predicate,bytes(4)+body[p+17:]


def with_technology_condition(body,technology,inverted=True):
    assert body[:4]==bytes(4), 'Do not overwrite an existing native condition'
    return struct.pack('<I',1)+TECHNOLOGY_CHECK+bytes.fromhex(technology)+bytes([inverted])+body[4:]
