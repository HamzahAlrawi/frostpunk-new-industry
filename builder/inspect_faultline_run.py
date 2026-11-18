"""Read the Faultline campaign variables and successful events from a save/run."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
from struct import unpack
import zlib


MAX_SCENE_BYTES=512*1024*1024
VARIABLE=re.compile(rb"\x01NI/Faultline/([A-Za-z0-9_/-]{1,75})\x00\x03Int(.{4})",re.S)
EVENT=re.compile(rb"\[Event\]\[NI Faultline ([^\]]+)\] Conditions satisfied")


def read_save(path):
    with path.open("rb") as source:
        signature, version=unpack("<2I",source.read(8))
        if (signature,version)!=(0xfeda0212,105):
            raise ValueError("Unsupported Frostpunk save header")
        source.read(12)
        count,=unpack("<I",source.read(4))
        if not 1<=count<=16:
            raise ValueError("Invalid save directory length")
        locations={}
        for _ in range(count):
            width,=unpack("<I",source.read(4))
            if not 1<=width<=40:
                raise ValueError("Invalid save record label")
            name=source.read(width)
            locations[name]=unpack("<QQ",source.read(16))
            if source.read(12)!=bytes([255])*12:
                raise ValueError("Unsupported save directory flags")
        base=source.tell()
        offset, size=locations[b"Scene"]
        if base+offset+4+size>path.stat().st_size or size>MAX_SCENE_BYTES:
            raise ValueError("Scene record exceeds the file bounds")
        source.seek(base+offset)
        expected,=unpack("<I",source.read(4))
        if not 1<=expected<=MAX_SCENE_BYTES:
            raise ValueError("Scene exceeds the diagnostic size limit")
        stream=zlib.decompressobj()
        data=stream.decompress(source.read(size),expected+1)
    if len(data)!=expected or not stream.eof:
        raise ValueError("Invalid compressed scene record")
    variables={}
    for match in VARIABLE.finditer(data):
        name=match[1].decode()
        value,=unpack("<i",match[2])
        if name in variables and variables[name]!=value:
            raise ValueError(f"Ambiguous campaign variable {name}")
        variables[name]=value
    if "phase" not in variables:
        raise ValueError("The save has no Faultline campaign state")
    return variables


def read_log(path):
    active=Counter()
    with path.open("rb") as source:
        for line in source:
            if match:=EVENT.search(line):
                active[match[1].decode("ascii","replace")]+=1
    return dict(active)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save",type=Path)
    parser.add_argument("--log",type=Path)
    args=parser.parse_args()
    if not args.save and not args.log:
        parser.error("Provide --save, --log or both")
    result={}
    if args.save:
        result["campaign"]=read_save(args.save)
    if args.log:
        result["matched_event_conditions"]=read_log(args.log)
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
