"""Bounded readers/writers for Frostpunk's native configuration records."""
import struct
from dataclasses import dataclass


class SchemaError(ValueError):
    pass


class Cursor:
    def __init__(self,data,position=0):
        self.data=data;self.position=position

    def take(self,length):
        if length<0 or self.position+length>len(self.data):
            raise SchemaError(f'Read outside record at {self.position}, length {length}')
        result=self.data[self.position:self.position+length];self.position+=length
        return result

    def number(self,code):
        size=struct.calcsize('<'+code)
        return struct.unpack('<'+code,self.take(size))[0]

    def u8(self):return self.number('B')
    def u32(self):return self.number('I')
    def i32(self):return self.number('i')
    def f32(self):return self.number('f')
    def guid(self):return self.take(16).hex()

    def boolean(self):
        value=self.u8()
        if value not in (0,1):raise SchemaError(f'Invalid boolean {value} at {self.position-1}')
        return bool(value)

    def string(self):
        if not self.boolean():return None
        end=self.data.find(b'\0',self.position)
        if end<0:raise SchemaError(f'Unterminated string at {self.position}')
        value=self.take(end-self.position).decode('utf-8');self.take(1)
        return value

    def entry(self):
        if not self.boolean():raise SchemaError('Null entry is not supported')
        return self.string(),self.guid()

    def count(self,limit=10000):
        result=self.u32()
        if result>limit:raise SchemaError(f'Invalid vector count {result} at {self.position-4}')
        return result


def u32(value):return struct.pack('<I',value)
def i32(value):return struct.pack('<i',value)
def f32(value):return struct.pack('<f',value)
def string(value):return b'\1'+value.encode()+b'\0' if value is not None else b'\0'
def entry(name,guid):return b'\1'+string(name)+bytes.fromhex(guid)


@dataclass(frozen=True)
class Span:
    start:int
    end:int

    def read(self,data):return data[self.start:self.end]


def replace_spans(data,changes):
    """Replace disjoint, explicitly bounded regions without shifting later edits."""
    last=len(data)
    for span,replacement in sorted(changes,key=lambda change:change[0].start,reverse=True):
        if not 0<=span.start<=span.end<=last:raise SchemaError('Overlapping or invalid edits')
        data=data[:span.start]+replacement+data[span.end:];last=span.start
    return data
