"""Development-only independent checks using PyMuPDF, not the exporter's parser.

Compare every card's characters and glyph advance positions with the fitted HTML.
Vector glyph antialiasing is intentionally not called pixel-identical.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import time
import unicodedata


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKC',text).casefold() if c.isalnum())


def visible(text):
    return ''.join(c for c in unicodedata.normalize('NFKC',text).casefold() if not c.isspace() and unicodedata.category(c)!='Cf')


def verify(pdf_path, evidence_dir, report_path, max_advance_error=0.2, max_cross_error=2, expected_sheets=None):
    import fitz
    start=time.monotonic();pdf_path=Path(pdf_path);evidence_dir=Path(evidence_dir)
    results=[];failures=[];character_count=0
    with fitz.open(pdf_path) as document:
        expected_sheets=expected_sheets if expected_sheets is not None else len(list(evidence_dir.glob('sheet-*.layout.json')))
        if not expected_sheets or len(document)!=expected_sheets:
            report={'pdf':str(pdf_path.resolve()),'sheets':len(document),'expected_sheets':expected_sheets,'all_checks_passed':False,
                'failures':[f'PDF has {len(document)} sheets; expected {expected_sheets} HTML sheets']}
            Path(report_path).write_text(json.dumps(report,indent=2),encoding='utf-8');print(report,flush=True);return report
        for sheet_index,page in enumerate(document):
            if tuple(page.rect)!=(0,0,612,792):raise ValueError('PDF paper dimensions changed')
            layout=json.loads((evidence_dir/f'sheet-{sheet_index+1:04d}.layout.json').read_text(encoding='utf-8'))
            text_flags=fitz.TEXTFLAGS_RAWDICT & ~fitz.TEXT_PRESERVE_IMAGES
            characters=[c for block in page.get_text('rawdict',flags=text_flags)['blocks'] if 'lines' in block for line in block['lines'] for span in line['spans'] for c in span['chars'] if visible(c['c'])]
            assigned=set();cards=[]
            for card_index,card in enumerate(layout['cards']):
                x,y,width,height=card['bounds']
                actual=[];all_visible=[]
                for index,char in enumerate(characters):
                    bx,by,br,bb=[n/0.75 for n in char['bbox']]
                    cx,cy=(bx+br)/2,(by+bb)/2
                    if x<=cx<=x+width and y<=cy<=y+height:
                        assigned.add(index);all_visible.append(char['c'])
                        if normalized(char['c']):actual.append((normalized(char['c']),bx,by,br,bb))
                expected=Counter(visible(card['text']))
                observed=Counter(visible(''.join(all_visible)))
                same=expected==observed
                # PDF emits one full-advance fi/fl glyph plus a zero-advance
                # character. DOM Range divides that glyph between letters.
                # Compare the complete ligature, not fictitious glyph positions.
                clusters=[]
                for char,bx,by,br,bb in actual:
                    zero=(bb-by if card['landscape'] else br-bx)<0.0001
                    if zero and clusters:
                        previous=clusters[-1];previous[0]+=char
                        previous[1:]=[min(previous[1],bx),min(previous[2],by),max(previous[3],br),max(previous[4],bb)]
                    else:clusters.append([char,bx,by,br,bb])
                ligatures={c[0] for c in clusters if len(c[0])>1}
                source=[];cursor=0
                while cursor<len(card['characters']):
                    group=[card['characters'][cursor]]
                    for count in range(3,1,-1):
                        trial=card['characters'][cursor:cursor+count]
                        if len(trial)==count and ''.join(normalized(c[0]) for c in trial) in ligatures:
                            axis=1 if card['landscape'] else 2
                            if max(c[axis] for c in trial)-min(c[axis] for c in trial)<0.01:
                                left=min(c[1] for c in trial);top=min(c[2] for c in trial)
                                right=max(c[1]+c[3] for c in trial);bottom=max(c[2]+c[4] for c in trial)
                                advance,cross=(bottom,(left+right)/2) if card['landscape'] else (left,(top+bottom)/2)
                                key=''.join(normalized(c[0]) for c in trial)
                                def close(c):
                                    a,b=(c[4],(c[1]+c[3])/2) if card['landscape'] else (c[1],(c[2]+c[4])/2)
                                    return c[0]==key and abs(a-advance)<1 and abs(b-cross)<2.5
                                if any(close(c) for c in clusters):group=trial;break
                    left=min(c[1] for c in group);top=min(c[2] for c in group)
                    right=max(c[1]+c[3] for c in group);bottom=max(c[2]+c[4] for c in group)
                    source.append([''.join(c[0] for c in group),left,top,right-left,bottom-top])
                    cursor+=len(group)
                bins=defaultdict(list)
                landscape=card['landscape']
                for index,(char,bx,by,br,bb) in enumerate(clusters):
                    advance,cross=(bb,(bx+br)/2) if landscape else (bx,(by+bb)/2)
                    bins[(char,round(advance),round(cross/2))].append((index,advance,cross))
                used=set();errors=[];missing=[]
                for char,cx,cy,cw,ch in source:
                    char=normalized(char)
                    advance,cross=(cy+ch,cx+cw/2) if landscape else (cx,cy+ch/2)
                    matches=[]
                    for da in (-1,0,1):
                        for dc in (-2,-1,0,1,2):
                            for index,a,b in bins.get((char,round(advance)+da,round(cross/2)+dc),[]):
                                if index not in used:matches.append((abs(a-advance)+abs(b-cross),index,abs(a-advance),abs(b-cross)))
                    if not matches:missing.append([char,cx,cy]);continue
                    _,index,da,dc=min(matches);used.add(index);errors.append((da,dc))
                max_a=max((e[0] for e in errors),default=0);max_c=max((e[1] for e in errors),default=0)
                result={'card':card_index+1,'title':card['title'],'characters':sum(expected.values()),'text_equal':same,
                    'unmatched_glyphs':len(missing),'maximum_advance_error_css_px':round(max_a,5),'maximum_cross_error_css_px':round(max_c,5)}
                if not same or missing or max_a>max_advance_error or max_c>max_cross_error:
                    failures.append({'sheet':sheet_index+1,**result,'missing_characters':dict(expected-observed),'extra_characters':dict(observed-expected),'unmatched_examples':missing[:3]})
                character_count+=sum(expected.values());cards.append(result)
            if len(assigned)!=len(characters):failures.append({'sheet':sheet_index+1,'unassigned_glyphs':len(characters)-len(assigned)})
            results.append({'sheet':sheet_index+1,'cards':cards})
            if (sheet_index+1)%25==0:print(f'Checked {sheet_index+1}/{len(document)} sheets',flush=True)
    report={'pdf':str(pdf_path.resolve()),'bytes':pdf_path.stat().st_size,'pdf_sha256':hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
        'sheets':len(results),'cards':sum(len(s['cards']) for s in results),'characters':character_count,
        'all_card_text_equal':all(c['text_equal'] for s in results for c in s['cards']),
        'unmatched_glyphs':sum(c['unmatched_glyphs'] for s in results for c in s['cards']),
        'maximum_advance_error_css_px':max((c['maximum_advance_error_css_px'] for s in results for c in s['cards']),default=0),
        'maximum_cross_error_css_px':max((c['maximum_cross_error_css_px'] for s in results for c in s['cards']),default=0),
        'thresholds':{'advance_css_px':max_advance_error,'cross_css_px':max_cross_error},
        'all_checks_passed':not failures,'seconds':round(time.monotonic()-start,2),'failures':failures,'sheet_results':results}
    Path(report_path).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print({k:v for k,v in report.items() if k not in ('sheet_results','failures')},flush=True)
    if failures:print('First failures:',failures[:5],flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('pdf');parser.add_argument('evidence')
    parser.add_argument('--report',default='compact-pdf-verification.json');parser.add_argument('--expected-sheets',type=int);args=parser.parse_args()
    result=verify(args.pdf,args.evidence,args.report,expected_sheets=args.expected_sheets)
    raise SystemExit(0 if result['all_checks_passed'] else 1)
