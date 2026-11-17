"""Bounded native UI geometry edits for six modes and nine research tabs."""
import struct
import re
import math
from tools.native_binary import Cursor
from tools.native_binary import SchemaError,Span,replace_spans,string,u32,f32

MODE_UI='ui/menu/mainmenuendlessmodeselection.binarytemplate'
TECH_UI='ui/panels/city/technologypanel.binarytemplate'


def native_mode_labels():
    return {
        'UI/Menu/EndlessMode/Endurance_ForSurvivalists':'Survival',
        'Generated/EndlessModeConfig/Endless modes/Builders/Subtitle text':'Build',
        'UI/Menu/EndlessMode/Serenity_ForCityBuilders':'Create',
        'Generated/EndlessModeConfig/Endless modes/Endurance/Short description':'Scarce supplies. Severe cold. Frequent storms.',
        'Generated/EndlessModeConfig/Endless modes/Builders/Short description':'Construct the Generator before winter.',
        'Generated/EndlessModeConfig/Endless modes/Serenity/Short description':'Abundant supplies and milder weather.'}


def geometry(data,name,expected,width=None,scale=None):
    kind='UILayoutRecipe' if name.endswith('LAYOUT') else 'UIButtonRecipe'
    marker=string(kind)+string(name)
    if data.count(marker)!=1:raise SchemaError('Ambiguous UI node '+name)
    start=data.index(marker)+len(marker)
    actual=struct.unpack_from('<2f',data,start+32)
    if actual!=expected:raise SchemaError((name,'Unsupported UI size',actual))
    edits=[]
    if width is not None:edits.append((Span(start+32,start+36),f32(width)))
    if scale is not None:
        if data[start+48:start+52]!=f32(1):raise SchemaError('Unexpected UI scale '+name)
        edits.append((Span(start+48,start+52),f32(scale)))
    return replace_spans(data,edits)


def build(source):
    modes=(source/MODE_UI).read_bytes();original=modes
    # The shipped layout explicitly contains one button and two externs.
    # Supply six actual slots instead of relying on runtime fallback clones.
    first=original.index(b'\1UIExternRecipe\0'+string('EXT_MODE_BUTTON'))
    second=original.index(b'\1UIExternRecipe\0'+string('EXT_MODE_BUTTON'),first+1)
    tail=original.index(string('MODE_BUTTON'),second)+len(string('MODE_BUTTON'))
    if original[tail:tail+3]!=b'\1\1\1':raise SchemaError('Unsupported extern footer')
    end=tail+3
    count=original.index(b'\1UIButtonRecipe\0'+string('MODE_BUTTON'))-4
    if original[count:count+4]!=u32(3):raise SchemaError('Unsupported mode child vector')
    # UILayoutRecipe's native reflection order: type, orientation, alignment,
    # cell alignment, three flags, custom offsets, padding and cell margins.
    # In particular the value 3 is ALIGNMENT, not a column count.
    footer=original.index(u32(1)+u32(3)+bytes(31)+f32(80),end)
    layout=footer-4
    expected=u32(0)+u32(1)+u32(3)+u32(0)+bytes(3)+f32(0)*6+f32(80)+f32(0)
    if original[layout:layout+51]!=expected:raise SchemaError('Unsupported native layout properties')
    edits=[(Span(count,count+4),u32(6)),(Span(end,end),original[second:end]*3),
        (Span(footer+39,footer+43),f32(34))]
    # Resize rectangles and offsets, not glyph scales. Short labels retain the
    # native typeface's proportions across six narrow, explicit card slots.
    button=original.index(b'\1UIButtonRecipe\0'+string('MODE_BUTTON'));factor=160/300
    for match in re.finditer(rb'\x01(UI[A-Za-z]+(?:Recipe|Preset))\0',original[button:first]):
        cursor=Cursor(original,button+match.end());cursor.string();pos=cursor.position
        preset=match[1].endswith(b'Preset');x=pos+(1 if preset else 0);width=pos+(17 if preset else 32)
        for offset in (x,width):
            value=struct.unpack_from('<f',original,offset)[0]
            if not math.isfinite(value) or abs(value)>3000:raise SchemaError('Unsupported card geometry')
            edits.append((Span(offset,offset+4),f32(value*factor)))
    modes=replace_spans(modes,edits)
    assert 6*160+5*34+(351.9-300)*factor<=1163.95
    tech=(source/TECH_UI).read_bytes()
    tech=geometry(tech,'TABS_LAYOUT',(800,30),width=1000)
    tech=geometry(tech,'TAB_BUTTON',(128,24),width=110,scale=110/128)
    assert 178+9*110<=1200
    return {MODE_UI:modes,TECH_UI:tech},dict(mode_columns=6,mode_width=160,mode_gap=34,
        mode_extent=1130,ornament_extent=1157.68,native_orientation=1,native_alignment=3,
        research_tabs=9,tab_width=110,tab_extent=1168)
