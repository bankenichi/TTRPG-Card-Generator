"""Presentation-only source labels; card selection and layout stay in the engine."""
from html import escape,unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re

from data_paths import discover_data_root,is_within


def load_source_labels(data_root=None):
    root=data_root or discover_data_root()
    if not root:return {}
    root=Path(root);labels={}
    def read(path):
        try:
            data=json.loads(path.read_text(encoding='utf-8'))
            return data if isinstance(data,dict) else {}
        except (OSError,json.JSONDecodeError):return {}
    for name,key in [('books.json','book'),('adventures.json','adventure')]:
        for book in read(root/'data'/name).get(key,[]):
            code=str(book.get('source') or book.get('id') or '')
            if code:labels.setdefault(code.casefold(),{'code':code,'label':code,'full':str(book.get('name') or code)})
    for directory in ('prerelease','homebrew'):
        folder=root/directory
        for relative in read(folder/'index.json').get('toImport',[]):
            if not isinstance(relative,str):continue
            path=folder/relative
            if not is_within(path,folder):raise ValueError('Source metadata path escapes its data tree')
            for source in read(path).get('_meta',{}).get('sources',[]):
                code=str(source.get('json') or '')
                if code:labels.setdefault(code.casefold(),{'code':code,'label':str(source.get('abbreviation') or code),'full':str(source.get('full') or code)})
    return labels


class _SourceLabels(HTMLParser):
    """Preserve the document verbatim except the source span in metadata rows."""
    VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    def __init__(self,labels):
        super().__init__(convert_charrefs=False)
        self.labels=labels;self.output=[];self.stack=[];self.capture=None;self.changed=0;self.used={}

    def emit(self,text):
        (self.capture['parts'] if self.capture else self.output).append(text)

    def handle_starttag(self,tag,attrs):
        raw=self.get_starttag_text();attributes=dict(attrs)
        parent=self.stack[-1] if self.stack else ('',{})
        is_source=(tag=='span' and parent[0]=='div' and 'meta' in parent[1].get('class','').split()
                   and re.search(r'font-style\s*:\s*italic',attributes.get('style',''),re.I))
        if is_source and self.capture is None:
            self.capture={'start':raw,'attrs':attrs,'parts':[],'depth':len(self.stack)+1,'complex':False}
        else:
            if self.capture:self.capture['complex']=True
            self.emit(raw)
        if tag not in self.VOID:self.stack.append((tag,attributes))

    def handle_endtag(self,tag):
        if self.capture and tag=='span' and len(self.stack)==self.capture['depth']:
            capture=self.capture;self.capture=None
            inner=''.join(capture['parts']);visible=unescape(inner)
            base,suffix=visible.rsplit(' p.',1) if ' p.' in visible else (visible,None)
            attrs=dict(capture['attrs']);code=attrs.get('data-source-id',base)
            source=self.labels.get(code.casefold())
            if source and not capture['complex']:
                label=source['label']+(' p.'+suffix if suffix is not None else '')
                attrs['title']=source['full']+' ['+source['code']+']';attrs['data-source-id']=source['code']
                start='<span'+''.join(' '+key+(f'="{escape(value,quote=True)}"' if value is not None else '') for key,value in attrs.items())+'>'
                self.output.extend((start,escape(label),'</span>'))
                self.changed+=label!=visible;self.used[source['code']]=source
            else:self.output.extend((capture['start'],inner,'</span>'))
        else:self.emit('</'+tag+'>')
        if self.stack:
            for index in range(len(self.stack)-1,-1,-1):
                if self.stack[index][0]==tag:
                    del self.stack[index:];break

    def handle_data(self,data):self.emit(data)
    def handle_entityref(self,name):self.emit('&'+name+';')
    def handle_charref(self,name):self.emit('&#'+name+';')
    def handle_comment(self,data):self.emit('<!--'+data+'-->')
    def handle_decl(self,decl):self.emit('<!'+decl+'>')
    def handle_pi(self,data):self.emit('<?'+data+'>')
    def handle_startendtag(self,tag,attrs):self.emit(self.get_starttag_text())


def apply_source_labels(path,labels=None,data_root=None):
    path=Path(path);parser=_SourceLabels(load_source_labels(data_root) if labels is None else labels)
    original=path.read_text(encoding='utf-8');parser.feed(original);parser.close()
    if parser.capture:raise ValueError('Generated source metadata span is incomplete')
    result=''.join(parser.output)
    if result!=original:path.write_text(result,encoding='utf-8')
    return {'changed_labels':parser.changed,'sources':parser.used}
