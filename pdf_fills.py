"""Remove native-PDF seams between exactly adjacent translucent cell fills.

Only pure, path-inactive rectangle fills under an explicit simple RGB/alpha
state qualify. Geometry uses bounded raw decimal tokens; all other stream bytes
remain unchanged. A second parsed-operation check rejects misplaced matches.
This PDF serialization step does not change HTML, layout, text or splitting.
"""
from collections import defaultdict,deque
from decimal import Decimal,localcontext
import re

from pypdf.generic import ContentStream,DecodedStreamObject,NameObject

NUMBER=rb'[-+]?(?:\d+(?:\.\d*)?|\.\d+)'
SPACE=rb'[ \t]+'
RECT=rb'('+NUMBER+rb')'+SPACE+rb'('+NUMBER+rb')'+SPACE+rb'('+NUMBER+rb')'+SPACE+rb'('+NUMBER+rb') re\nf\n'
RECTANGLE=re.compile(RECT)
BLOCK=re.compile(rb'(?<!\S)(?P<prefix>'+NUMBER+SPACE+NUMBER+SPACE+NUMBER+rb' rg\n/[A-Za-z0-9]+ gs\n)(?P<rectangles>(?:'+RECT+rb'){2,})')


def parse(raw):
    stream=DecodedStreamObject();stream.set_data(raw)
    return ContentStream(stream,None).operations


def key(ops):return tuple((tuple(args),op) for args,op in ops)


def safe_blocks(ops,states):
    result=defaultdict(deque);path=False;i=0
    while i<len(ops):
        args,op=ops[i]
        state=states.get(ops[i-1][0][0]) if i>0 and ops[i-1][1]==b'gs' else None
        if state is not None:state=state.get_object()
        eligible=(not path and op==b're' and len(args)==4 and i>=2 and ops[i-2][1]==b'rg'
                  and state is not None and set(state)=={'/ca','/BM'} and state['/BM']=='/Normal'
                  and 0<float(state['/ca'])<1 and i+1<len(ops) and ops[i+1]==([],b'f'))
        if eligible:
            end=i
            while end+1<len(ops) and ops[end][1]==b're' and len(ops[end][0])==4 and ops[end+1]==([],b'f'):end+=2
            result[key(ops[i-2:end])].append((i-2,end))
            i=end;path=False;continue
        if op in {b'm',b'l',b'c',b'v',b'y',b'h',b're'}:path=True
        if op in {b'S',b's',b'f',b'F',b'f*',b'B',b'B*',b'b',b'b*',b'n'}:path=False
        i+=1
    return result


def combine(raw):
    pieces=[];count=0
    with localcontext() as context:
        context.prec=256
        for match in RECTANGLE.finditer(raw):
            tokens=match.groups()
            if any(len(t)>64 for t in tokens):return raw,0
            values=tuple(Decimal(t.decode('ascii')) for t in tokens)
            x,y,w,h=values
            if pieces:
                previous=pieces[-1];px,py,pw,ph=previous['values']
                if min(w,h,pw,ph)>0 and y==py and h==ph and px+pw==x:
                    total=pw+w
                    previous['values']=(px,py,total,ph)
                    old=previous['tokens']
                    previous['tokens']=(old[0],old[1],format(total,'f').encode('ascii'),old[3])
                    previous['raw']=b' '.join(previous['tokens'])+b' re\nf\n'
                    count+=1;continue
            pieces.append({'tokens':tokens,'values':values,'raw':match.group()})
    return b''.join(p['raw'] for p in pieces),count


def normalize_raw(raw,states):
    original=parse(raw);available=safe_blocks(original,states);changes=[];total=0
    def replace(match):
        nonlocal total
        candidate=parse(match.group());blocks=available.get(key(candidate))
        if not blocks:return match.group()
        start,end=blocks.popleft()
        rectangles,count=combine(match['rectangles'])
        if not count:return match.group()
        replacement=match['prefix']+rectangles
        changes.append((start,end,parse(replacement)));total+=count
        return replacement
    result=BLOCK.sub(replace,raw)
    if not total:return raw,0
    expected=[];end=0
    for start,stop,replacement in sorted(changes,key=lambda c:c[0]):
        if start<end:raise ValueError('Overlapping PDF fill transformations')
        expected.extend(original[end:start]);expected.extend(replacement);end=stop
    expected.extend(original[end:])
    if parse(result)!=expected:raise ValueError('PDF fill transformation changed other drawing commands')
    return result,total


def coalesce_native_fills(page,writer):
    contents=page.get_contents()
    if contents is None:return 0
    states=page['/Resources'].get('/ExtGState',{})
    result,count=normalize_raw(contents.get_data(),states)
    if count:
        stream=DecodedStreamObject();stream.set_data(result)
        page[NameObject('/Contents')]=writer._add_object(stream.flate_encode())
    return count
