(() => {
  const config=window.DECK_VIEWER,$=id=>document.getElementById(id),holders=[],near=new Set();let exporting=false;
  if(config.pdfExport===false)$('viewer-export').hidden=true;
  $('deck-title').textContent=config.kind==='Backs'?'Card backs':'Your deck';$('sheet-count').textContent=`${config.sheet_count} ${config.sheet_count===1?'sheet':'sheets'} · Letter paper`;$('sheet-total').textContent=`/ ${config.sheet_count}`;$('jump-sheet').max=config.sheet_count;
  function scale(){const value=$('viewer-zoom').value==='1'?1:Math.min(1,(document.documentElement.clientWidth-28)/856);document.documentElement.style.setProperty('--sheet-width',(856*value)+'px');document.documentElement.style.setProperty('--sheet-height',(1096*value)+'px');document.documentElement.style.setProperty('--sheet-scale',value);}
  function sync(){
    const center=innerHeight/2;
    const wanted=[...near].sort((a,b)=>Math.abs(holders[a].getBoundingClientRect().top-center)-Math.abs(holders[b].getBoundingClientRect().top-center)).slice(0,4);
    holders.forEach((holder,index)=>{
      const surface=holder.querySelector('.sheet-surface'),existing=surface.querySelector('iframe');
      if(wanted.includes(index)&&!existing){const frame=document.createElement('iframe');frame.className='sheet-frame';frame.title=`Sheet ${index+1}`;frame.tabIndex=-1;frame.addEventListener('load',()=>surface.classList.add('loaded'));frame.src=config.files[index];surface.append(frame);}
      else if(!wanted.includes(index)&&existing){existing.remove();surface.classList.remove('loaded');}
    });
    const visible=wanted.find(index=>{const r=holders[index].getBoundingClientRect();return r.bottom>130&&r.top<innerHeight;});
    if(visible!==undefined&&document.activeElement!==$('jump-sheet'))$('jump-sheet').value=visible+1;
  }
  const observer=new IntersectionObserver(entries=>{entries.forEach(entry=>{const i=Number(entry.target.dataset.sheet);entry.isIntersecting?near.add(i):near.delete(i);});sync();},{rootMargin:'90% 0px'});
  for(let index=0;index<config.files.length;index++){
    const holder=document.createElement('section');holder.className='sheet-placeholder';holder.dataset.sheet=index;holder.setAttribute('aria-label',`Sheet ${index+1}`);holder.id=`sheet-${index+1}`;
    const label=document.createElement('div');label.className='sheet-label';label.textContent=`SHEET ${index+1}`;
    const surface=document.createElement('div');surface.className='sheet-surface';holder.append(label,surface);$('sheets').append(holder);holders.push(holder);observer.observe(holder);
  }
  $('jump-sheet').addEventListener('change',()=>{const value=Math.max(1,Math.min(config.sheet_count,Number($('jump-sheet').value)||1));$('jump-sheet').value=value;holders[value-1].scrollIntoView({block:'start'});});
  $('viewer-zoom').addEventListener('change',()=>{scale();sync();});window.addEventListener('resize',()=>{scale();sync();});scale();
  $('viewer-export').addEventListener('click',async()=>{
    if(exporting)return;exporting=true;$('viewer-export').disabled=true;$('viewer-status').textContent='Preparing your complete PDF…';
    try{
      const response=await fetch('/export-pdf',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:config.kind})});const job=await response.json();if(!response.ok)throw new Error(job.error||'Export could not start.');
      if(config.platform==='android'&&window.AndroidUI?.beginExport)window.AndroidUI.beginExport(job.id);
      let result;
      do{await new Promise(r=>setTimeout(r,800));const status=await fetch('/export-status?id='+encodeURIComponent(job.id));result=await status.json();if(!status.ok||result.state==='failed')throw new Error(result.error||'Export could not finish.');$('viewer-status').textContent=`Creating PDF: ${result.completed_sheets||0} / ${result.total_sheets||'?'} pages`;}while(result.state!=='complete');
      $('viewer-status').textContent='Your complete PDF is ready.';const link=document.createElement('a');link.textContent='Save PDF';link.href=result.download;link.download=result.download.split('/').pop();
      if(config.platform==='android'&&window.AndroidUI?.savePdf)link.addEventListener('click',e=>{e.preventDefault();window.AndroidUI.savePdf(link.download);});
      $('viewer-status').append(link);
    }catch(error){$('viewer-status').textContent=error.message;}finally{exporting=false;$('viewer-export').disabled=false;}
  });
})();
