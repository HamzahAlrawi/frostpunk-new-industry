"""Compile the unskinned, one-material Liquid Engine mesh format.

The input is original geometry in metres, with Y up. Retain the supplied
game's material, vertex declaration and render passes from its owned cube.
"""
from math import sqrt
from struct import Struct, iter_unpack, pack_into, unpack_from

from .native_binary import SchemaError, u32


DONOR = "graphics/primitives/cube.binarytemplate"
VERTEX = Struct("<3f8h4B2e")
POSITIONS = 473
DESCRIPTOR = 445
DRAW_RANGES = (930, 1062, 1074, 1086)
BOUNDS = (56, 114, 146)


def vector(a, b):
    return tuple(y - x for x, y in zip(a, b))


def unit(v):
    length = sqrt(sum(x*x for x in v))
    if length < 1e-8:
        raise ValueError("Degenerate mesh face")
    return tuple(x/length for x in v)


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def layout(data):
    if data[16:30] != bytes.fromhex("01 00 00 00 b5 94 03 ad 00 00 00 00 00 00"):
        raise SchemaError("Unsupported static mesh header")
    vertices, stride, zero_a, zero_b, zero_c, size, zero_d = unpack_from("<7I", data, DESCRIPTOR)
    if stride != VERTEX.size or size != vertices*stride or (zero_a,zero_b,zero_c,zero_d) != (0,0,0,0):
        raise SchemaError("Unsupported vertex buffer")
    start = POSITIONS + size
    triangles, zero_a, zero_b, zero_c, size = unpack_from("<5I", data, start)
    if size != triangles*6 or (zero_a,zero_b,zero_c) != (0,0,0):
        raise SchemaError("Unsupported 16-bit index buffer")
    end = start + 20 + size
    if data[end:end+19] != u32(0)+u32(1)+u32(7)+b"Default":
        raise SchemaError("Expected exactly one native material")
    return vertices, triangles, start, end


def compile_mesh(donor, uid, faces):
    vertices, triangles, _, footer = layout(donor)
    if (vertices,triangles) != (24,12):
        raise SchemaError("Expected the owned cube material and draw ranges")
    tail = bytearray(donor[footer:])
    points, buffer = [], bytearray()
    for polygon, color in faces:
        a, b, c = polygon
        tangent = unit(vector(a,b))
        normal = unit(cross(tangent,vector(a,c)))
        def pack_axis(axis):
            return tuple(round(32767*x) for x in axis)
        for point, uv in zip(polygon,((0,0),(1,0),(0,1))):
            points.append(point)
            buffer.extend(VERTEX.pack(*point,*pack_axis(normal),32767,*pack_axis(tangent),32767,*color,*uv))
    count = len(points)
    if not 0 < count < 65536:
        raise ValueError("Mesh exceeds its 16-bit index declaration")
    faces_count = count//3
    prefix = bytearray(donor[:POSITIONS])
    prefix[:16] = uid
    low = tuple(min(p[i] for p in points) for i in range(3))
    high = tuple(max(p[i] for p in points) for i in range(3))
    for at in BOUNDS:
        pack_into("<8f",prefix,at,*low,1,*high,1)
    pack_into("<I",prefix,DESCRIPTOR,count)
    pack_into("<I",prefix,465,len(buffer))
    for at in DRAW_RANGES:
        if tail[at:at+4] != u32(triangles):
            raise SchemaError("Unsupported native mesh render pass")
        pack_into("<I",tail,at,faces_count)
    if tail[934:938] != bytes.fromhex("00 00 17 00"):
        raise SchemaError("Unsupported mesh vertex range")
    pack_into("<H",tail,936,count-1)
    indices = bytearray(count*2)
    for i in range(0,count,3):
        pack_into("<3H",indices,i*2,i,i+1,i+2)
    return bytes(prefix)+buffer+u32(faces_count)+bytes(12)+u32(len(indices))+indices+tail


def audit_mesh(data, expected_faces):
    vertices, faces, start, end = layout(data)
    assert faces == expected_faces and vertices == 3*faces
    lo = unpack_from('<3f',data,BOUNDS[0])
    hi = unpack_from('<3f',data,BOUNDS[0]+16)
    assert lo[1]>=0 and all(a<b for a,b in zip(lo,hi))
    for indices in iter_unpack('<3H',data[start+20:end]):
        assert max(indices)<vertices and len(set(indices))==3
        a,b,c = [VERTEX.unpack_from(data,POSITIONS+i*VERTEX.size) for i in indices]
        assert all(lo[j]-1e-5<=p[j]<=hi[j]+1e-5 for p in (a,b,c) for j in range(3))
        direction=cross(vector(a[:3],b[:3]),vector(a[:3],c[:3]))
        assert sum(x*y for x,y in zip(direction,a[3:6]))>0, 'Winding disagrees with the stored normal'
    assert all(unpack_from('<I',data,end+i)[0]==faces for i in DRAW_RANGES)
    assert unpack_from('<H',data,end+936)[0]==vertices-1
