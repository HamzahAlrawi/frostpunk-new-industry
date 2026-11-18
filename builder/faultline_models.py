"""Original, vertex-painted Faultline buildings in the game's Y-up coordinates."""
from math import cos, pi, sin, sqrt
from pathlib import PurePosixPath
from random import Random
import re

from tools.native_binary import SchemaError, string
from tools.native_mesh import DONOR, compile_mesh, cross, unit, vector


IRON = (66, 76, 83)
STEEL = (107, 121, 128)
RUST = (111, 61, 43)
COPPER = (142, 91, 55)
BRASS = (183, 143, 79)
BRICK = (116, 77, 64)
MORTAR = (79, 71, 66)
STONE = (105, 113, 119)
TIMBER = (103, 78, 60)
TAR = (49, 55, 58)
COAL = (38, 43, 48)
SLATE = (79, 99, 114)
CANVAS = (140, 137, 107)
SNOW = (219, 233, 243)
ICE = (158, 183, 200)
LAMP = (255, 190, 87)
GLASS = (177, 126, 66)


def tone(color, variation):
    return tuple(max(0, min(255, channel + variation)) for channel in color)


class Mesh:
    def __init__(self):
        self.faces = []
        self.random = Random(1824)

    def worn(self, color, amount=12):
        return tone(color, self.random.randint(-amount, amount))

    def face(self, vertices, color):
        for i in range(1, len(vertices) - 1):
            self.faces.append(((vertices[0], vertices[i], vertices[i + 1]), (*color, 255)))

    def box(self, x, y, z, width, height, length, color):
        a, b = x - width/2, x + width/2
        e, f = z - length/2, z + length/2
        c = y + height
        points = ((a,y,e),(b,y,e),(b,y,f),(a,y,f),(a,c,e),(b,c,e),(b,c,f),(a,c,f))
        for indices in ((0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)):
            self.face(tuple(points[i] for i in indices), color)

    def beam(self, a, b, half, color):
        axis = unit(vector(a, b))
        seed = (0, 0, 1) if abs(axis[2]) < .9 else (1, 0, 0)
        u = unit(cross(seed, axis))
        v = cross(axis, u)

        def corners(point):
            return [tuple(point[i] + half*(s*u[i] + t*v[i]) for i in range(3))
                    for s, t in ((-1,-1),(1,-1),(1,1),(-1,1))]

        points = corners(a) + corners(b)
        self.face(tuple(reversed(points[:4])), color)
        self.face(points[4:], color)
        for i in range(4):
            j = (i + 1) % 4
            self.face((points[i], points[j], points[j+4], points[i+4]), color)

    def turn(self, points, radius, color, sides=10):
        """Continuous tube through the centreline, with bevels at each bend."""
        rings = []
        u = None
        for i, point in enumerate(points):
            axis = unit(vector(points[max(i-1, 0)], points[min(i+1, len(points)-1)]))
            if u is None:
                seed = (0, 0, 1) if abs(axis[2]) < .95 else (0, 1, 0)
                u = unit(cross(seed, axis))
            else:
                projection = sum(a*b for a,b in zip(u,axis))
                u = unit(tuple(a-projection*b for a,b in zip(u,axis)))
            v = cross(axis, u)
            rings.append([tuple(q + radius*(s*cos(j*2*pi/sides) + t*sin(j*2*pi/sides))
                                for q, s, t in zip(point, u, v)) for j in range(sides)])
        self.face(tuple(reversed(rings[0])), color)
        self.face(rings[-1], color)
        for a, b in zip(rings, rings[1:]):
            for i in range(sides):
                j = (i + 1) % sides
                self.face((a[i], a[j], b[j], b[i]), tone(color, (i % 5)-2))

    def lathe(self, x, z, profile, sides=20):
        previous = None
        for height, radius, color in profile:
            ring = [(x+radius*cos(i*2*pi/sides), height, z+radius*sin(i*2*pi/sides))
                    for i in range(sides)]
            if previous:
                for i in range(sides):
                    j = (i+1) % sides
                    self.face((previous[i], ring[i], ring[j], previous[j]), tone(color, i % 5-2))
            else:
                self.face(ring, color)
            previous = ring
        self.face(tuple(reversed(ring)), color)

    def prism(self, profile, back, front, color):
        a = [(x,y,back) for x,y in profile]
        b = [(x,y,front) for x,y in profile]
        self.face(tuple(reversed(a)), color)
        self.face(b, color)
        for i in range(len(a)):
            j = (i+1) % len(a)
            self.face((b[i], a[i], a[j], b[j]), color)

    def brick_faces(self, x, z, width, length, bottom, top, color=BRICK):
        """Staggered masonry relief on the four sides of an existing wall."""
        rows = round((top-bottom)/.19)
        for row in range(rows):
            y = bottom + (top-bottom)*row/rows + .012
            height = (top-bottom)/rows - .022
            for along_x, span, origin, sides in (
                (True,width,x,((z+length/2,1),(z-length/2,-1))),
                (False,length,z,((x-width/2,1),(x+width/2,-1))),
            ):
                begin, end = origin-span/2+.012, origin+span/2-.012
                step = span / max(1, round(span/.34))
                start = begin - (row % 2)*step/2
                while start < end:
                    left, right = max(begin,start+.009), min(end,start+step-.009)
                    if right > left:
                        paint = self.worn(color, 17)
                        for side, sign in sides:
                            plane = side + sign*.018 if along_x else side - sign*.018
                            if along_x:
                                points = [(left,y,plane),(right,y,plane),(right,y+height,plane),(left,y+height,plane)]
                            else:
                                points = [(plane,y,left),(plane,y,right),(plane,y+height,right),(plane,y+height,left)]
                            self.face(points if sign == 1 else tuple(reversed(points)), paint)
                    start += step

    def base(self, x, z, width, length, height=.26, paving=STONE):
        self.box(x,0,z,width,height*.82,length,MORTAR)
        self.brick_faces(x,z,width,length,.015,height*.82,paving)
        self.box(x,height*.80,z,width+.055,height*.20,length+.055,paving)

    def arch(self, x, y, z, width, height, fill, frame, *, bars=False):
        radius = width/2
        spring = y + height - radius
        angles = [i*pi/10 for i in range(11)]
        arc = [(x+radius*cos(a),spring+radius*sin(a)) for a in angles]
        profile = [(x-radius,y),(x+radius,y)] + arc
        self.prism(profile,z-.018,z+.016,fill)
        trim = .065 if width<1 else .10
        outside = [(x+(radius+trim)*cos(a),spring+(radius+trim)*sin(a)) for a in angles]
        for i in range(10):
            self.prism((arc[i],outside[i],outside[i+1],arc[i+1]),z-.025,z+.05,self.worn(frame,8))
        for sign in (-1, 1):
            self.box(x+sign*(radius+trim/2),y,z,trim,spring-y,.10,frame)
        if bars:
            self.box(x,y,z+.044,.047,height,.045,frame)
            self.box(x,spring-.04,z+.044,width,.054,.048,frame)
        self.box(x,y-.045,z+.044,width+trim*2,.054,.16,frame)

    def gable(self, x, y, z, width, length, rise, paint, ridge_offset=0):
        outline = ((x-width/2,y),(x+width/2,y),(x+ridge_offset,y+rise))
        self.prism(outline,z-length/2,z+length/2,paint)

    def roof(self, x, y, z, width, length, rise, paint=SLATE, snowline=(.54,.71), ridge_offset=0):
        ridge = x + ridge_offset
        for side, coverage in zip((-1,1), snowline):
            edge = x + side*width/2

            def point(slope, distance, height=0):
                return (ridge+(edge-ridge)*slope, y+rise*(1-slope)+height, z+length*(distance-.5))

            panels = max(5, round(length/.49))
            for row in range(panels):
                a, b = row/panels, (row+1)/panels
                corners = (point(0,a),point(0,b),point(1,b),point(1,a))
                self.face(corners if side==1 else tuple(reversed(corners)), self.worn(paint,15))
                self.beam(point(0,a,.022),point(1,a,.022),.019,tone(paint,-20))
            phase = self.random.uniform(-pi,pi)

            def snow_points(t):
                margin = min(t,1-t)
                taper = min(1,.32+6.0*margin)
                fall = coverage*taper + .085*sin(16*t+phase) + .047*sin(35*t+phase)
                edge = min(.98,max(.12,fall))
                drift = .069 + .022*sin(21*t+phase)
                return (point(0,t,drift),point(edge*.46,t,drift+.024),
                        point(edge*.85,t,drift*.58),point(edge,t,.009))

            # The snow crosses the standing seams instead of following every panel.
            strips = panels*3
            drift = [snow_points(.014+.972*i/strips) for i in range(strips+1)]
            for a,b in zip(drift,drift[1:]):
                for i, paint_band in enumerate((SNOW,SNOW,tone(SNOW,-15))):
                    patch = (a[i],b[i],b[i+1],a[i+1])
                    self.face(patch if side==1 else tuple(reversed(patch)),self.worn(paint_band,4))
            self.beam(point(1,0),point(1,1),.056,TAR)
            for station in (.18,.28,.74):
                high = point(1,station)
                lo = (high[0]+side*.009,high[1]-self.random.uniform(.11,.24),high[2]+.016)
                self.turn((lo,high),.016,ICE,sides=4)
        self.beam((ridge,y+rise+.044,z-length/2),(ridge,y+rise+.044,z+length/2),.04,ICE)


def relay(m):
    m.base(0,0,2.68,2.62,.26)
    m.box(0,.26,.15,1.62,1.05,1.67,MORTAR)
    m.brick_faces(0,.15,1.62,1.67,.26,1.31)
    m.roof(0,1.33,.15,1.86,1.87,.34,SLATE,(.42,.73))
    m.arch(0,.32,1.01,.67,.87,TIMBER,IRON)
    m.box(.16,.68,1.05,.085,.052,.055,BRASS)
    m.box(0,.19,1.22,.88,.20,.34,STONE)
    for x in (-1.09,1.09):
        for z in (-1.07,1.07):
            m.box(x,.24,z,.305,.28,.30,STONE)
            m.beam((x,.46,z),(.47*x,5.71,.44*z),.058,IRON)
    for y, extent in ((1.62,.93),(2.77,.81),(3.89,.68),(5.0,.57)):
        upper = extent-.14
        for sign in (-1,1):
            m.beam((-extent,y,sign*extent),(extent,y,sign*extent),.043,STEEL)
            m.beam((sign*extent,y,-extent),(sign*extent,y,extent),.043,STEEL)
            m.beam((-extent,y,sign*extent),(upper,y+1.0,sign*upper),.029,RUST)
            m.beam((extent,y,sign*extent),(-upper,y+1.0,sign*upper),.023,IRON)
            m.beam((sign*extent,y,-extent),(sign*upper,y+1.0,upper),.031,IRON)
    for z in (-.75,.75):
        m.beam((-.84,5.12,z),(.84,5.12,z),.069,IRON)
        m.beam((-.83,5.55,z),(.83,5.55,z),.023,STEEL)
        for x in (-.78,0,.78):
            m.beam((x,5.09,z),(x,5.55,z),.022,STEEL)
    for i in range(12):
        m.box(0,5.09,(i-5.5)*.13,1.64,.064,.11,m.worn(TIMBER))
    m.lathe(0,-.07,[(5.11,.36,IRON),(5.25,.37,BRASS),(5.37,.30,RUST),
                   (5.81,.25,COPPER),(5.84,.34,IRON),(5.91,.34,STEEL)])
    for x in (-.65,.65):
        m.lathe(x,.10,[(5.24,.18,IRON),(5.37,.19,COPPER),(5.43,.14,IRON),
                      (5.72,.14,LAMP),(5.76,.20,IRON),(5.91,.10,COPPER),(5.97,.025,BRASS)])
        for off in (-.12,.12):
            m.beam((x+off,5.38,.17),(x+off,5.75,.17),.016,TAR)
    m.beam((-1.15,6.15,-.12),(1.15,6.15,-.12),.047,IRON)
    m.beam((0,5.78,-.11),(0,6.68,-.11),.033,STEEL)
    for x in (-.94,.94):
        m.lathe(x,-.12,[(6.13,.075,IRON),(6.23,.084,ICE),(6.27,.058,STONE),(6.31,.078,ICE)],12)
        m.turn(((x,6.29,-.12),(x,5.46,.28),(x*1.13,3.22,.93),(x*1.19,.38,1.09)),.015,TAR,5)
    for x in (.48,.69):
        m.beam((x,.32,1.04),(.72*x,5.08,.55),.021,STEEL)
    for i in range(17):
        t = i/17
        x = .48-.136*t
        m.beam((x,.46+4.48*t,1.04-.46*t),(x+.18,.46+4.48*t,1.04-.46*t),.016,IRON)


def seam_roof(m):
    def point(angle,z,height=0):
        return (2.83*cos(angle),1.95+1.13*sin(angle)+height,z)

    for j in range(14):
        a, b = j*pi/14, (j+1)*pi/14
        for k in range(9):
            z = -2.00+k*.31
            points = (point(a,z),point(b,z),point(b,z+.31),point(a,z+.31))
            m.face(points,m.worn(SLATE,15))
        if j % 2 == 0:
            m.beam((2.85*cos(a),1.97+1.13*sin(a),-2.01),
                   (2.85*cos(a),1.97+1.13*sin(a),.80),.025,STEEL)
    strips = []
    for j in range(22):
        t = j/21
        z = -1.94 + t*2.66
        a = .35+.19*sin(11*t)+.08*sin(29*t)
        b = 2.65+.17*sin(9*t+1.4)+.10*sin(31*t)
        strips.append([point(a+(b-a)*i/17,z,.033+.055*sin(pi*i/17)) for i in range(18)])
    for a,b in zip(strips,strips[1:]):
        for i in range(17):
            paint = tone(SNOW,-13) if i in (0,16) else SNOW
            m.face((a[i],a[i+1],b[i+1],b[i]),m.worn(paint,5))
    for z in (-1.98,.79):
        arch = [(2.85*cos(i*pi/16),1.95+1.13*sin(i*pi/16),z) for i in range(17)]
        for a,b in zip(arch,arch[1:]):
            m.beam(a,b,.055,IRON)


def coal_heap(m, x, z):
    sides = 9
    outline = []
    middle = []
    for i in range(sides):
        angle = i*2*pi/sides
        radius = m.random.uniform(.83,1)
        dx, dz = radius*cos(angle), radius*sin(angle)
        outline.append((x+.73*dx,.28,z+1.15*dz))
        middle.append((x+.52*dx,m.random.uniform(.65,.95),z+.84*dz))
    peak = (x+.12,1.08,z-.27)
    for i in range(sides):
        j = (i+1) % sides
        m.face((outline[i],middle[i],middle[j],outline[j]),m.worn(COAL,13))
        m.face((middle[i],peak,middle[j]),m.worn(COAL,16))
    for i in range(11):
        dx=m.random.uniform(-.59,.59)
        dz=m.random.uniform(-.58,.74)
        y=.26+.7*(1-abs(dx)*1.10-abs(dz)*.49)
        a=(x+dx,y,z+dz)
        b=(a[0]+.12,y+.11,a[2]-.14)
        c=(a[0]+.23,y+.035,a[2]+.10)
        d=(a[0]-.023,y-.07,a[2]+.15)
        for panel in ((a,b,c),(b,d,c),(a,d,b)):
            m.face(panel,m.worn(COAL,22))


def magazine(m):
    m.base(0,-.02,5.78,3.95,.25)
    m.box(0,.23,-1.79,5.48,1.71,.29,MORTAR)
    m.brick_faces(0,-1.79,5.48,.29,.25,1.94,STONE)
    seam_roof(m)
    gable = [(-2.77,1.88),(2.77,1.88)] + [
        (2.77*cos(i*pi/16),1.94+1.08*sin(i*pi/16)) for i in range(17)]
    m.prism(gable,-1.82,-1.69,IRON)
    # End the front roof above the three exposed gravity-fed bins.
    for x in (-2.68,-.91,.91,2.68):
        m.box(x,.24,-.45,.22,1.72,2.82,MORTAR)
        m.brick_faces(x,-.45,.22,2.82,.25,1.96,STONE)
        m.box(x,.24,1.02,.24,1.77,.25,IRON)
        m.box(x,.26,1.18,.34,.46,.37,STONE)
    for x in (-1.80,0,1.80):
        coal_heap(m,x,-.04)
        for i in range(3):
            m.box(x,.26+i*.14,1.26,1.55,.12,.13,m.worn(TIMBER))
        for edge in (-.66,.66):
            m.box(x+edge,.23,1.36,.075,.58,.08,IRON)
        m.box(x,1.74,1.12,1.59,.18,.18,IRON)
        m.box(x,1.79,1.219,.37,.082,.018,BRASS)
        m.box(x,.25,1.67,1.47,.10,.50,STONE)
    for x in (-1.78,1.78):
        y = 1.95+1.13*sqrt(1-(x/2.83)**2)
        m.lathe(x,-.72,[(y-.08,.17,IRON),(y+.07,.14,STEEL),
                         (y+.27,.14,IRON),(y+.34,.23,SLATE),(y+.40,.16,ICE)],12)


def valve_wheel(m, x, y, z, radius):
    ring = [(x+radius*cos(i*2*pi/16),y+radius*sin(i*2*pi/16),z) for i in range(17)]
    for a,b in zip(ring,ring[1:]):
        m.beam(a,b,.035,RUST)
    for i in range(5):
        a=i*2*pi/5
        m.beam((x,y,z),(x+radius*cos(a),y+radius*sin(a),z),.025,COPPER)
    m.turn(((x,y,z-.15),(x,y,z+.052)),.081,BRASS,12)


def works(m):
    m.base(-1.46,-.41,4.54,5.99,.26)
    m.base(2.22,-.11,2.87,6.44,.19)
    m.box(-1.46,.25,-.41,4.37,2.52,5.79,MORTAR)
    m.brick_faces(-1.46,-.41,4.37,5.79,.26,2.77)
    m.gable(-1.46,2.77,-.41,4.37,5.79,1.45,BRICK,ridge_offset=.18)
    m.roof(-1.46,2.81,-.41,4.62,6.02,1.46,SLATE,(.47,.67),ridge_offset=.18)
    m.arch(-1.77,.29,2.53,1.27,1.90,TAR,STONE)
    for x in (-2.30,-2.03,-1.76,-1.49,-1.22):
        m.box(x,.33,2.568,.24,1.20,m.random.uniform(.050,.068),m.worn(RUST))
    m.box(-1.76,.33,2.626,1.11,.07,.07,IRON)
    m.box(-1.76,1.08,2.626,1.11,.06,.07,IRON)
    m.arch(-3.05,1.17,2.54,.77,1.14,GLASS,STONE,bars=True)
    m.arch(-.42,1.17,2.54,.77,1.14,LAMP,STONE,bars=True)
    m.arch(-1.29,2.93,2.53,.73,.58,GLASS,IRON,bars=True)
    for z in (-1.91,-.24,1.36):
        m.box(-3.68,1.34,z,.09,.88,1.13,STONE)
        m.box(-3.74,1.41,z,.04,.72,.96,GLASS)
        for off in (-.27,.0,.27):
            m.box(-3.77,1.41,z+off,.05,.72,.048,IRON)
    m.box(-1.76,.27,2.91,1.68,.12,.48,STONE)
    m.box(-1.76,.15,3.15,1.80,.15,.38,STONE)
    m.lathe(-2.68,-2.25,[(2.99,.46,IRON),(3.17,.46,STONE),(3.33,.37,BRICK),
                         (4.65,.30,RUST),(4.73,.34,IRON),(4.83,.29,IRON),
                         (5.85,.25,RUST),(5.96,.33,IRON),(6.16,.34,BRICK),(6.25,.34,ICE)])
    for z in (-1.75,.84):
        m.lathe(2.15,z,[(.19,.45,IRON),(.37,.56,IRON),(.53,.56,STEEL),(.61,.53,COPPER),
                         (1.43,.53,RUST),(1.47,.57,IRON),(1.54,.57,IRON),
                         (1.56,.49,COPPER),(1.80,.40,COPPER),(1.96,.19,BRASS),(2.08,.15,IRON)])
        m.turn(((2.15,2.07,z),(2.15,2.46,z),(1.98,2.61,z),(1.40,2.61,z)),.109,COPPER)
        for y in (.72,1.28):
            m.lathe(2.15,z,[(y,.532,RUST),(y+.076,.543,IRON)],20)
        valve_wheel(m,2.15,1.15,z+.67,.30)
    m.turn(((1.38,2.61,-2.73),(1.38,2.61,1.84),(1.38,2.47,2.05),
            (1.38,1.60,2.43),(1.19,1.60,2.61),(.70,1.60,2.61)),.13,COPPER)
    for z in (-2.91,2.74):
        for x in (1.0,3.49):
            m.beam((x,.18,z),(x,2.88,z),.076,IRON)
        m.beam((.91,2.84,z),(3.58,2.84,z),.11,STEEL)
        m.beam((3.49,2.27,z),(2.91,2.84,z),.061,IRON)
    m.beam((3.48,2.78,-2.91),(3.48,2.78,2.74),.079,IRON)
    m.beam((1.4,2.76,-2.92),(1.4,2.76,2.74),.074,IRON)
    valve_wheel(m,1.37,1.60,2.58,.40)


def sledge(m,x,z,paint):
    for dx in (-.45,.45):
        m.turn(((x+dx,.24,z-1.02),(x+dx,.24,z+.81),
                (x+dx,.31,z+1.00),(x+dx,.50,z+1.13)),.040,IRON,6)
        for dz in (-.69,.69):
            m.beam((x+dx,.24,z+dz),(x+dx,.47,z+dz),.051,TIMBER)
    for i in range(7):
        m.box(x,.45,z+(i-3)*.245,1.03,.12,.22,m.worn(TIMBER))
    for dz in (-.54,.01,.51):
        height=m.random.uniform(.29,.51)
        m.box(x,.57,z+dz,.84,height,.43,m.worn(paint))
        m.box(x,.57+height,z+dz,.90,.046,.47,m.worn(paint))
        for dx in (-.30,.30):
            m.beam((x+dx,.568,z+dz+.231),(x+dx,.625+height,z+dz+.231),.024,TIMBER)
            m.beam((x+dx,.625+height,z+dz-.20),(x+dx,.625+height,z+dz+.23),.021,TIMBER)
    for dx in (-.26,.26):
        m.turn(((x+dx,.57,z-.93),(x+dx,.65,z-.82),(x+dx,1.06,z-.69),
                (x+dx,1.10,z+.71),(x+dx,.57,z+.83)),.017,TAR,6)


def dispatch(m):
    m.base(-2.36,-1.35,2.63,3.77,.29)
    m.base(1.30,-1.04,4.66,4.63,.23)
    m.box(-2.36,.29,-1.35,2.47,2.42,3.62,TAR)
    for i in range(15):
        y=.29+i*.16
        m.box(-2.36,y,-1.35,2.50,.136,3.65,m.worn(TIMBER,14))
    m.gable(-2.36,2.66,-1.35,2.47,3.62,1.06,TIMBER)
    m.roof(-2.36,2.71,-1.35,2.78,3.89,1.07,SLATE,(.56,.72))
    m.arch(-2.37,1.37,.501,1.31,.84,LAMP,TAR,bars=True)
    m.box(-2.39,.32,.56,1.14,.49,.16,IRON)
    m.box(-2.39,.38,.65,.73,.10,.035,COPPER)
    m.arch(-2.36,2.78,.50,.48,.41,GLASS,IRON)
    for z in (-2.71,-1.53,-.41):
        m.box(-3.63,1.10,z,.12,.81,.78,IRON)
        m.box(-3.70,1.17,z,.05,.65,.64,GLASS)
        m.box(-3.73,1.17,z,.03,.65,.062,IRON)
    for z in (-2.91,.35):
        for x in (-.91,1.42,3.51):
            m.box(x,.22,z,.26,1.93,.22,TIMBER)
            m.box(x,.22,z,.29,.17,.25,IRON)
            m.box(x,1.82,z,.29,.15,.25,IRON)
        m.beam((-.99,2.08,z),(3.65,2.08,z),.108,TIMBER)
        for x in (1.42,3.51):
            m.beam((x,1.51,z),(x-.54,2.11,z),.061,TIMBER)
    for x in (-.91,1.42,3.51):
        m.beam((x,2.08,-2.98),(x,2.08,.47),.082,TIMBER)
    m.roof(1.31,2.14,-1.29,4.83,3.86,.82,CANVAS,(.32,.63),ridge_offset=.56)
    for i in range(11):
        m.box(1.28,.188,-2.9+i*.38,4.57,.067,.35,m.worn(TIMBER))
    sledge(m,.14,1.52,CANVAS)
    sledge(m,2.09,1.61,RUST)
    for x in (-.37,2.58):
        m.beam((x,.24,2.72),(x,.96,2.72),.047,TIMBER)
        m.turn(((x,.86,2.72),(x+.19,.64,2.77),(x+.47,.48,2.64)),.022,COPPER,6)
    # Tall yard gantry with a lamp, hoist chain and cross-timber bracing.
    for x in (-1.01,3.51):
        m.beam((x,.23,-.35),(x,3.83,-.35),.083,IRON)
        m.beam((x,2.67,-1.42),(x,3.75,-.35),.070,IRON)
    m.beam((-1.09,3.81,-.35),(3.62,3.81,-.35),.111,IRON)
    m.beam((-1.09,3.94,-.35),(3.62,3.94,-.35),.042,ICE)
    m.beam((-1.01,3.19,-.35),(-.37,3.82,-.35),.061,IRON)
    m.beam((3.51,3.19,-.35),(2.88,3.82,-.35),.061,IRON)
    m.lathe(.90,-.35,[(2.66,.108,IRON),(2.83,.13,LAMP),(2.87,.18,IRON),
                      (2.95,.107,COPPER)],12)
    m.beam((.90,2.90,-.35),(.90,3.82,-.35),.020,IRON)
    m.box(2.46,3.58,-.20,1.50,.30,.13,IRON)
    m.box(2.46,3.63,-.118,1.38,.21,.04,RUST)
    m.box(2.46,3.65,-.088,.056,.17,.022,ICE)
    m.box(2.46,3.706,-.088,.16,.056,.022,ICE)


DESIGNS = {
    "Signal Relay": (relay, (1.53,1.65,1.65), "Graphics/Buildings/SteamHub/BLD_SteamHub_004_LV1"),
    "Coal Magazine": (magazine, (1.94,2.10,2.38), "Graphics/Buildings/ResourceDepot/BLD_ResourceDepot_000_LV1"),
    "Valve Works": (works, (1.91,2.50,2.20), "Graphics/Buildings/Factory/BLD_Factory_001"),
    "Relief Dispatch": (dispatch, (1.90,2.17,2.32), "Graphics/Buildings/Factory/BLD_Factory_001"),
}


def model_path(name):
    return "graphics/primitives/faultline_"+name.lower().replace(" ","_")+".binarytemplate"


def build_models(prefabs, assets, source, guid):
    donor = source(DONOR)
    models = []
    for row in prefabs:
        name = row["name"]
        design, scale, original = DESIGNS[name]
        mesh = Mesh()
        design(mesh)
        # Match the native construction plots before normals and bounds are baked.
        faces = [(tuple(tuple(axis*factor for axis,factor in zip(point,scale))
                        for point in triangle), paint) for triangle,paint in mesh.faces]
        path = model_path(name)
        uid = guid("faultline/model/"+name)
        assets[path] = (DONOR, compile_mesh(donor,uid,faces))
        prefab = row["path"]
        donor_path, data = assets[prefab]
        stem = PurePosixPath(path).with_suffix("").as_posix()
        pattern = rb"\x01"+re.escape(original.encode())+rb"(?:_construction|_contruction|_destroyed)?\x00"
        data, count = re.subn(pattern,lambda _:string(stem),data,flags=re.I)
        if count < 2:
            raise SchemaError("Missing model and construction preview slots for "+name)
        assets[prefab] = (donor_path,data)
        row["model"] = path
        models.append(dict(name=name,path=path,guid=uid.hex(),donor=DONOR,triangles=len(mesh.faces)))
    return models
