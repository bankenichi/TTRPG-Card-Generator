"""Capture the fitted HTML layout without introducing PDF-specific card styling."""
import hashlib
import json
import unicodedata
from collections import Counter


def text_signature(text):
    # Reading order differs for rotated cards and columns. Compare all visible
    # characters, including symbols and multiplicity; glyph positions are checked
    # separately in the full-catalog verifier.
    counts = Counter(c for c in unicodedata.normalize('NFKC', text).casefold()
                     if not c.isspace() and unicodedata.category(c)!='Cf')
    return hashlib.sha256(json.dumps(sorted(counts.items()), ensure_ascii=False).encode('utf-8')).hexdigest()


CAPTURE_LAYOUT = r"""includeCharacters => [...document.querySelectorAll('.page')].map(sheet => {
  const origin=sheet.getBoundingClientRect(),round=n=>Math.round(n*10000)/10000;
  const bounds=element=>{const r=element.getBoundingClientRect();return [r.x-origin.x,r.y-origin.y,r.width,r.height].map(round)};
  return {width:round(origin.width),height:round(origin.height),cards:[...sheet.querySelectorAll('.card-slot')].map(slot=>{
    const card=slot.querySelector('.card')||slot;
    const result={bounds:bounds(card),title:card.querySelector('.title')?.innerText||'',text:card.innerText,
      landscape:card.classList.contains('landscape'),
      elements:[...card.querySelectorAll('.title,.meta,.content-inner p,th,td,li,.card-footer')].map(e=>bounds(e))};
    if(includeCharacters){
      result.characters=[];
      const walker=document.createTreeWalker(card,NodeFilter.SHOW_TEXT),range=document.createRange();let node;
      while(node=walker.nextNode()){
        const transform=getComputedStyle(node.parentElement).textTransform;
        for(let offset=0;offset<node.length;offset++){
          let value=node.data[offset];if(!/[\p{L}\p{N}]/u.test(value))continue;
          if(transform==='uppercase')value=value.toUpperCase();
          if(transform==='lowercase')value=value.toLowerCase();
          range.setStart(node,offset);range.setEnd(node,offset+1);
          for(const rect of range.getClientRects())if(rect.width&&rect.height)
            result.characters.push([value,round(rect.x-origin.x),round(rect.y-origin.y),round(rect.width),round(rect.height)]);
        }
      }
    }
    return result;
  })};
})"""


CHECK_OVERFLOW = """() => [...document.querySelectorAll('.card')].flatMap(card=>{
  const old=card.style.transform;card.style.transform='none';
  const wrapper=card.querySelector('.content-wrapper'),inner=card.querySelector('.content-inner');
  const bounds=wrapper.getBoundingClientRect(),outside=r=>r.left<bounds.left-1.5 || r.right>bounds.right+1.5 ||
    r.top<bounds.top-1.5 || r.bottom>bounds.bottom+1.5;
  // scrollHeight includes trailing margins; text Range boxes include font
  // ascender space above the first line. Neither is painted content. Check
  // the renderer's flow blocks and table borders without those false alarms.
  const blocks=[...inner.querySelectorAll('p,table,li,.card-nested,div')].filter(e=>
    e.tagName!=='DIV' || e.matches('.card-nested') ||
    ![...e.children].some(child=>child.matches('div,p,table,ul,ol,li')));
  const bad=blocks.some(e=>
    outside(e.getBoundingClientRect()) || e.scrollWidth>e.clientWidth+1) ||
    [...card.querySelectorAll('.header,.title,.meta,.card-footer')].some(e=>e.scrollWidth>e.clientWidth+1);
  card.style.transform=old;return bad?[card.querySelector('.title').textContent.trim()]:[];
})"""


PRINT_SHEET_CSS = """
@page{size:Letter;margin:0}
html,body{margin:0!important;padding:0!important;background:white!important}
.page{margin:0!important;break-after:page!important;break-inside:avoid!important}
.page:last-of-type{break-after:auto!important;page-break-after:auto!important}
.deck-navigation{display:none!important}
*{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important}
"""


def validate_layout(layout):
    for sheet in layout:
        if (sheet['width'],sheet['height']) != (816,1056):
            raise ValueError('Rendered sheet dimensions differ from Letter paper')
        for index, card in enumerate(sheet['cards']):
            expected=(48+(index%3)*240,24+(index//3)*336,240,336)
            if any(abs(a-b)>0.01 for a,b in zip(card['bounds'],expected,strict=True)):
                raise ValueError('Card position differs from the established 3x3 print layout')
