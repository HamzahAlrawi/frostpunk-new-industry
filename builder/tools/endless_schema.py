"""Lossless editing of native Endless menu definitions and custom parameters."""
from dataclasses import dataclass
try:
    from native_binary import Cursor,Span,SchemaError,u32,string,entry,replace_spans
except ImportError:
    from .native_binary import Cursor,Span,SchemaError,u32,string,entry,replace_spans


GOAL_ANCHOR=b'\1\1Goal\0'+bytes.fromhex('54f66828d4d980b4f348362a41220c45')
ENDURANCE_VALUE=bytes.fromhex('788fc7bec9e627ac954099d2ea68ee6f')


@dataclass
class Parameter:
    name:str
    guid:str
    values:list
    display:str
    description:str

    def encode(self):
        body=entry(self.name,self.guid)+u32(len(self.values))
        for value in self.values:
            body+=entry(value['name'],value['guid'])+bytes([value['default']])+string(value['display'])+string(value['description'])
        return body+string(self.display)+string(self.description)


def parameters(data):
    start=data.index(GOAL_ANCHOR)-4;cursor=Cursor(data,start);count=cursor.count(64);result=[]
    for _ in range(count):
        name,guid=cursor.entry();values=[]
        for _ in range(cursor.count(64)):
            value_name,value_guid=cursor.entry()
            values.append(dict(name=value_name,guid=value_guid,default=cursor.boolean(),display=cursor.string(),description=cursor.string()))
        result.append(Parameter(name,guid,values,cursor.string(),cursor.string()))
    span=Span(start,cursor.position)
    if span.read(data)!=u32(count)+b''.join(value.encode() for value in result):raise SchemaError('Custom parameter round-trip failed')
    if any(sum(value['default'] for value in parameter.values)!=1 for parameter in result):raise SchemaError('Parameter requires exactly one default')
    return span,result


def append_parameter(data,parameter):
    span,original=parameters(data)
    identities={p.guid for p in original}|{v['guid'] for p in original for v in p.values}
    if parameter.guid in identities or any(v['guid'] in identities for v in parameter.values):raise SchemaError('Parameter GUID collision')
    return replace_spans(data,[(span,u32(len(original)+1)+b''.join(p.encode() for p in original)+parameter.encode())])


def modes(data):
    count=Cursor(data).count(16)
    starts=[(data.index(string(name)),name) for name in ('Endurance','Builders','Serenity')]
    starts.sort()
    if count!=3 or starts[0][0]!=4:raise SchemaError('Unsupported original mode list')
    return {name:data[start:starts[i+1][0] if i+1<len(starts) else len(data)] for i,(start,name) in enumerate(starts)}


def append_mode(data,name,enabled_value,localize):
    original=modes(data);source=original['Endurance'];cursor=Cursor(source)
    if cursor.string()!='Endurance':raise SchemaError('Invalid donor mode')
    edits=[(Span(0,cursor.position),string(name))]
    if source.count(ENDURANCE_VALUE)!=1:raise SchemaError('Ambiguous Endurance parameter')
    selected=source.index(ENDURANCE_VALUE);start=selected-4
    if source[start:selected]!=u32(1):raise SchemaError('Unsupported default parameter vector')
    edits.append((Span(start,selected+16),u32(2)+ENDURANCE_VALUE+bytes.fromhex(enabled_value)))
    for suffix,text in (
        ('Display name','Reconstruction'),
        ('Short description','Rebuild the Frostland. Finance megaprojects, sustain relief routes and compete for industrial contracts. An Endless economy for New Industry.'),
    ):
        old=string('@Generated/EndlessModeConfig/Endless modes/Endurance/'+suffix)
        at=source.index(old);edits.append((Span(at,at+len(old)),localize('Endless/Menu/'+suffix,text)))
    old=string('@UI/Menu/EndlessMode/Endurance_ForSurvivalists');at=source.index(old)
    edits.append((Span(at,at+len(old)),localize('Endless/Menu/Subtitle','For builders of a new world')))
    clone=replace_spans(source,edits)
    return u32(4)+data[4:]+clone
