"""Law-book geometry, including native split-circle choices."""
from math import dist

try:
    from research_layout import point_hit,segment_conflict
except ImportError:
    from .research_layout import point_hit,segment_conflict


def choice_pair(left,right):
    return (left['book_guid']==right['book_guid']
            and left.get('excludes_laws')==[right['id']]
            and right.get('excludes_laws')==[left['id']]
            and bool(left.get('requires_laws'))
            and left['requires_laws']==right.get('requires_laws'))


def layout_errors(laws,native):
    """Native entries map names to (position, book GUID); no owned data needed."""
    errors=[];by={law['id']:law for law in laws}
    for law in laws:
        x,y=law['position']
        if abs(x)<4 and abs(y)<4:errors.append((law['id'],'book centre'))
        if law.get('default_available'):
            if abs(x)>11 or abs(y)>10:errors.append((law['id'],'remote node'))
            if law.get('branch_root') and dist((0,0),(x,y))>11.5:errors.append((law['id'],'distant root'))
        for name,(pos,book) in native.items():
            if book==law['book_guid'] and abs(x-pos[0])<5 and abs(y-pos[1])<2:
                errors.append((law['id'],'native law',name))
        for sibling in law.get('excludes_laws',[]):
            other=by[sibling]
            if not choice_pair(law,other) or law['position']!=other['position']:
                errors.append((law['id'],'separated choice halves',sibling))
    for i,law in enumerate(laws):
        for other in laws[i+1:]:
            if law['book_guid']!=other['book_guid']:continue
            if choice_pair(law,other) and law['position']==other['position']:continue
            if abs(law['position'][0]-other['position'][0])<5 and abs(law['position'][1]-other['position'][1])<2:
                errors.append((law['id'],'added law',other['id']))
    # Each exclusive pair is one visual node and one incoming connection.
    # Coordinates also identify the shared book-centre endpoint of root spokes.
    for book in {law['book_guid'] for law in laws}:
        points={tuple(pos):name for name,(pos,category) in native.items() if category==book}
        points.update({tuple(law['position']):law['id'] for law in laws if law['book_guid']==book})
        edges=set()
        for law in laws:
            if law['book_guid']!=book or not law.get('default_available'):continue
            end=tuple(law['position']);parents=law.get('requires_laws',[])
            if not parents:edges.add(((0,0),end))
            for parent in parents:
                start=tuple(by[parent]['position'])
                if dist(start,end)>5:errors.append((parent,law['id'],'distant link'))
                edges.add((start,end))
        edges=sorted(edges)
        for a,b in edges:
            for pos,key in points.items():
                if pos not in (a,b) and point_hit(a,b,pos):errors.append((a,b,'line through',key))
        for i,(a,b) in enumerate(edges):
            for c,d in edges[i+1:]:
                if not {a,b}&{c,d} and segment_conflict(a,b,c,d):errors.append((a,b,'crosses',c,d))
    return errors
