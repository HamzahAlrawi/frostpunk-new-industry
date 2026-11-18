"""Original Faultline geometry for the four new buildings."""
from math import cos, pi, sin
import re
from pathlib import PurePosixPath

from tools.native_binary import SchemaError, string
from tools.native_mesh import DONOR, compile_mesh, cross, unit, vector


IRON = (96,112,120,255)
BRASS = (178,123,58,255)
WOOD = (112,79,53,255)
SNOW = (219,228,238,255)
COAL = (45,47,53,255)
RED = (154,66,43,255)
GLASS = (245,190,94,255)
CANVAS = (155,160,143,255)


class Mesh:
    def __init__(self):
        self.faces = []

    def face(self, vertices, color):
        for i in range(1,len(vertices)-1):
            self.faces.append(((vertices[0],vertices[i],vertices[i+1]),color))

    def box(self, x, y, z, w, h, d, color):
        a,b=x-w/2,x+w/2
        e,f=z-d/2,z+d/2
        c=y+h
        p=((a,y,e),(b,y,e),(b,y,f),(a,y,f),(a,c,e),(b,c,e),(b,c,f),(a,c,f))
        for indices in ((0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)):
            self.face(tuple(p[i] for i in indices),color)

    def beam(self, a, b, half, color):
        v=unit(vector(a,b))
        seed=(0,0,1) if abs(v[2])<.9 else (1,0,0)
        u=unit(cross(seed,v))
        w=cross(v,u)
        def corners(p):
            return [tuple(p[i]+half*(s*u[i]+t*w[i]) for i in range(3))
                    for s,t in ((-1,-1),(1,-1),(1,1),(-1,1))]
        p=corners(a)+corners(b)
        for i in range(4):
            j=(i+1)%4
            self.face((p[i],p[j],p[j+4],p[i+4]),color)

    def ring(self, x, y, z, bottom, top, height, color, sides=16):
        def circle(radius, at):
            return [(x+radius*cos(i*2*pi/sides),at,z+radius*sin(i*2*pi/sides)) for i in range(sides)]
        a,b=circle(bottom,y),circle(top,y+height)
        for i in range(sides):
            j=(i+1)%sides
            self.face((a[i],b[i],b[j],a[j]),color)
        self.face(tuple(reversed(b)),color)

    def roof(self, x, y, z, width, length, rise, color):
        for sign in (-1,1):
            edge=x+sign*width/2
            a=(x,y+rise,z-length/2); b=(x,y+rise,z+length/2)
            c=(edge,y,z+length/2); d=(edge,y,z-length/2)
            self.face((a,b,c,d) if sign==1 else (d,c,b,a),color)
            self.beam(d,c,.055,IRON)
            for rib in range(1,7):
                station=z-length/2+length*rib/7
                self.beam((x,y+rise+.025,station),(edge,y+.025,station),.037,IRON)

    def gables(self, x,y,z,width,length,rise,color):
        for sign in (-1,1):
            station=z+sign*length/2
            face=((x-width/2,y,station),(x+width/2,y,station),(x,y+rise,station))
            self.face(face if sign==1 else tuple(reversed(face)),color)


def relay(m):
    m.box(0,0,0,2.9,.25,2.9,IRON)
    m.box(0,.25,0,1.38,1.18,1.26,RED)
    m.box(0,1.43,0,1.55,.08,1.43,SNOW)
    for x in (-.9,.9):
        for z in (-.9,.9):
            m.beam((x,.24,z),(x*.44,5.8,z*.44),.08,IRON)
    for height,radius in ((1.1,.8),(2.7,.68),(4.3,.53)):
        for sign in (-1,1):
            m.beam((-radius,height,sign*radius),(radius*.8,height+1.6,sign*radius*.8),.045,WOOD)
            m.beam((sign*radius,height,-radius),(sign*radius*.8,height+1.6,radius*.8),.045,IRON)
    for h in (5.5,5.86,6.19):
        m.ring(0,h,0,.52,.45,.12,BRASS)
    m.ring(0,5.28,0,.30,.20,1.24,IRON)
    m.beam((-1.22,6.45,0),(1.22,6.45,0),.095,IRON)
    for x in (-1.04,1.04):
        m.ring(x,6.43,0,.18,.13,.33,GLASS)
    m.box(0,.72,.64,.60,.35,.06,BRASS)
    for y in (.38,.65,1.12):
        m.box(0,y,.65,1.24,.045,.08,IRON)
    for x in (-.74,.74):
        m.beam((x,1.41,.78),(x,5.4,.38),.025,BRASS)


def magazine(m):
    m.box(0,0,0,5.9,.23,4.1,IRON)
    for x in (-1.82,0,1.82):
        m.box(x,.23,-.55,1.68,.65,2.65,COAL)
        m.box(x,.88,-.58,1.24,.32,1.92,COAL)
    for x in (-2.85,-.99,.90,2.82):
        for z in (-1.98,.91):
            m.box(x,.22,z,.16,2.13,.16,WOOD)
        m.box(x,.22,-.61,.13,1.27,2.93,IRON)
    m.box(0,.22,-1.98,5.57,1.88,.13,RED)
    for j in range(12):
        ang=j*pi/12; nxt=(j+1)*pi/12
        m.face(((2.92*cos(ang),2.13+1.09*sin(ang),-2.12),
                (2.92*cos(nxt),2.13+1.09*sin(nxt),-2.12),
                (2.92*cos(nxt),2.13+1.09*sin(nxt),1.12),
                (2.92*cos(ang),2.13+1.09*sin(ang),1.12)),SNOW if 2<j<9 else IRON)
        if j%2:
            m.beam((2.92*cos(ang),2.16+1.09*sin(ang),-2.11),
                   (2.92*cos(ang),2.16+1.09*sin(ang),1.15),.026,IRON)
    for x in (-1.82,0,1.82):
        m.box(x,.24,1.32,1.47,.30,.55,WOOD)


def works(m):
    m.box(0,0,0,7.9,.25,7.1,IRON)
    m.box(-1.7,.25,-.53,4.03,2.45,5.7,RED)
    m.roof(-1.7,2.75,-.53,4.43,6.06,1.19,SNOW)
    m.gables(-1.7,2.71,-.53,4.03,5.7,1.17,RED)
    for x in (-3.47,-2.73,-1.99,-1.25,-.51,.23):
        m.box(x,.31,2.34,.075,2.35,.065,IRON)
    m.box(-1.55,.25,2.36,1.35,1.91,.16,IRON)
    m.box(-1.55,1.65,2.46,.92,.16,.04,GLASS)
    for z in (-2.74,-.8,1.14):
        m.box(-3.75,1.53,z,.055,.64,.99,IRON)
        m.box(-3.78,1.62,z,.06,.43,.76,GLASS)
        m.box(-3.81,1.62,z,.06,.43,.055,IRON)
    for z in (-2.94,2.74):
        for x in (.55,3.72):
            m.box(x,.25,z,.21,2.62,.20,IRON)
        m.beam((.49,2.66,z),(3.81,2.66,z),.13,IRON)
    for z in (-2,-.43,1.14):
        m.ring(2.12,.23,z,.68,.61,.6,IRON)
        m.ring(2.12,.83,z,.59,.39,.76,BRASS)
        m.ring(2.12,1.59,z,.24,.24,.41,IRON)
        m.ring(2.12,1.98,z,.55,.55,.13,RED)
        m.ring(2.12,2.11,z,.13,.13,.11,BRASS)
    m.beam((2.12,2.48,-2.92),(2.12,2.48,2.78),.18,RED)
    m.ring(-2.8,3.01,-2.19,.38,.27,3.29,IRON)
    m.ring(-2.8,6.02,-2.19,.36,.36,.25,BRASS)


def dispatch(m):
    m.box(0,0,0,8,.22,7.55,WOOD)
    m.box(-2.59,.22,-1.54,2.32,2.9,3.94,IRON)
    m.roof(-2.59,3.17,-1.54,2.67,4.20,.73,SNOW)
    m.gables(-2.59,3.10,-1.54,2.32,3.94,.76,WOOD)
    m.box(-2.59,1.87,.45,1.54,.64,.055,GLASS)
    for x in (-3.43,-2.61,-1.78):
        m.box(x,1.74,.49,.085,.86,.055,IRON)
    for y in (.61,.97,1.31):
        m.box(-2.59,y,.46,2.31,.05,.075,WOOD)
    for x in (-1.04,1.27,3.73):
        for z in (-2.95,.64):
            m.box(x,.22,z,.17,2.27,.18,WOOD)
        m.beam((x,2.31,-2.96),(x,2.31,.67),.08,IRON)
    m.roof(1.34,2.51,-1.14,5.09,3.99,.69,CANVAS)
    for x in (-1.11,1.19,3.12):
        m.box(x,.33,1.37,1.05,.44,2.57,RED if x<0 else WOOD)
        for off in (-.45,.45):
            m.beam((x+off,.285,.08),(x+off,.285,2.71),.06,IRON)
            m.beam((x+off,.285,2.71),(x+off,.51,2.98),.06,IRON)
        for z in (.74,1.31,1.88):
            m.box(x,.77,z,.91,.43,.42,CANVAS)
            for off in (-.27,.27):
                m.box(x+off,1.18,z,.045,.025,.44,WOOD)
    m.beam((-3.40,2.07,.27),(-3.40,5.76,.27),.085,IRON)
    m.box(-2.98,5.17,.27,.82,.43,.09,RED)


DESIGNS = {
    "Signal Relay": (relay, "steam hub", "Graphics/Buildings/SteamHub/BLD_SteamHub_004_LV1"),
    "Coal Magazine": (magazine, "resource depot", "Graphics/Buildings/ResourceDepot/BLD_ResourceDepot_000_LV1"),
    "Valve Works": (works, "factory", "Graphics/Buildings/Factory/BLD_Factory_001"),
    "Relief Dispatch": (dispatch, "factory", "Graphics/Buildings/Factory/BLD_Factory_001"),
}


def model_path(name):
    return "graphics/primitives/faultline_"+name.lower().replace(" ","_")+".binarytemplate"


def build_models(prefabs, assets, source, guid):
    donor=source(DONOR)
    models=[]
    for row in prefabs:
        name=row["name"]
        design, _, original=DESIGNS[name]
        mesh=Mesh()
        design(mesh)
        path=model_path(name)
        uid=guid("faultline/model/"+name)
        assets[path]=(DONOR,compile_mesh(donor,uid,mesh.faces))
        prefab=row["path"]
        donor_path,data=assets[prefab]
        stem=PurePosixPath(path).with_suffix("").as_posix()
        pattern=rb"\x01"+re.escape(original.encode())+rb"(?:_construction|_contruction|_destroyed)?\x00"
        data,count=re.subn(pattern,lambda _:string(stem),data,flags=re.I)
        if count<2:
            raise SchemaError("Missing model and construction preview slots for "+name)
        assets[prefab]=(donor_path,data)
        row["model"]=path
        models.append(dict(name=name,path=path,guid=uid.hex(),donor=DONOR,triangles=len(mesh.faces)))
    return models
