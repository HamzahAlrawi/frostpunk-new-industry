import pathlib, struct, zlib, json, sys

GAME = pathlib.Path(r'C:\Program Files (x86)\Steam\steamapps\common\Frostpunk')
ROOT = pathlib.Path(__file__).resolve().parents[1]

def murmur(data):
    m=0x5bd1e995; h=len(data); n=len(data)//4*4
    for i in range(0,n,4):
        k=int.from_bytes(data[i:i+4],'little'); k=k*m&0xffffffff; k^=k>>24; k=k*m&0xffffffff
        h=(h*m&0xffffffff)^k
    tail=data[n:]
    if tail:
        h^=int.from_bytes(tail,'little'); h=h*m&0xffffffff
    h^=h>>13; h=h*m&0xffffffff; h^=h>>15
    return h

NAMES={int(key):value for key,value in json.loads((ROOT/'archive_names.json').read_text()).items()}
source_config=ROOT/'cache/source.json'
if source_config.exists():
    GAME=pathlib.Path(json.loads(source_config.read_text())['game'])

def entries(base):
    idx=(GAME/(base+'.idx')).read_bytes()
    assert idx[:3]==b'\0\2\1' and len(idx)==11+29*struct.unpack_from('<Q',idx,3)[0]
    return [(11+i*29,)+struct.unpack_from('<IQQQB',idx,11+i*29) for i in range((len(idx)-11)//29)]

def read(f,e):
    pos,h,c,u,o,z=e; f.seek(o); b=f.read(c)
    if z and b[:2]==b'\x1f\x8b': b=zlib.decompressobj(31).decompress(b)
    assert len(b)==u,(h,len(b),u)
    return b

