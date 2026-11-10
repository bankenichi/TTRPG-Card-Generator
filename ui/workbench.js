(() => {
  'use strict';
  const config = window.WORKBENCH;
  const catalog = config.datasets;
  const names = Object.keys(catalog);
  const $ = id => document.getElementById(id);
  const defaults = {background:'parchment-background.svg',watermark:'watermark-emblem.svg',cardBack:'card-back.svg'};
  const storageKey = 'ttrpg.workbench.v1';
  const labels = {'0':'Cantrips',A:'Abjuration',C:'Conjuration',D:'Divination',E:'Enchantment',I:'Illusion',N:'Necromancy',T:'Transmutation',V:'Evocation',str:'Strength',dex:'Dexterity',con:'Constitution',int:'Intelligence',wis:'Wisdom',cha:'Charisma',EI:'Eldritch Invocations',AI:'Artificer Infusions',AS:'Arcane Shots',ED:'Elemental Disciplines','FS:F':'Fighting Styles',RN:'Rune Knight Runes',PB:'Pact Boons','MV:B':'Battle Master Maneuvers',MM:'Metamagic',RP:'Renown Perks',none:'None / Other',yes:'Required',no:'Not required'};
  const icons = {Actions:'action-triangle-glyph',Backgrounds:'backgrounds',Bastions:'bastions',Bestiary:'bestiary',Classes:'classes','Conditions / Diseases':'conditions-diseases',Decks:'decks',Deities:'deities',Feats:'feats',Items:'items',Languages:'languages','Optional Features':'optionalfeatures',Psionics:'psionics',Races:'races',Skills:'skills',Spells:'spells',Vehicles:'vehicles'};
  const filterNames = {playtest:'Source material',cr:'Challenge rating',reqAttune:'Attunement',attunement:'Attunement',featureType:'Feature type',name:'Class'};
  const pretty = text => String(text).replace(/\.svg$/i,'').replace(/[-_]/g,' ').replace(/\b\w/g,c=>c.toUpperCase());
  const state = {selected:[],filters:{},assets:{...defaults},active:catalog.Items?'Items':names[0]};
  const uploads = {};
  let generating = false, exporting = false, pdfResult = null;
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey)||'null');
    if (saved) {
      state.selected = (saved.selected||[]).filter(name=>name in catalog);
      state.active = names.includes(saved.active)?saved.active:state.active;
      for (const name of names) {
        state.filters[name] = {};
        for (const [key, values] of Object.entries(catalog[name].filters||{})) {
          state.filters[name][key] = (saved.filters?.[name]?.[key]||[]).filter(value=>values.includes(value));
        }
      }
      for (const [key,options] of Object.entries({background:config.assets.backgrounds,watermark:config.assets.watermarks,cardBack:config.assets.cardBacks})) {
        if ((options||[]).includes(saved.assets?.[key])||saved.assets?.[key]==='Default')state.assets[key]=saved.assets[key];
      }
    }
  } catch (_) { /* An unavailable/corrupt local preference must not block the app. */ }
  function persist() {
    try { localStorage.setItem(storageKey,JSON.stringify(state)); } catch (_) {}
  }
  function element(tag, className, text) {
    const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=text;return node;
  }
  function glyph(name) {
    const node=element('span','glyph');node.setAttribute('aria-hidden','true');node.style.setProperty('--glyph',`url('/icons/${icons[name]||'action-triangle-glyph'}.svg')`);return node;
  }
  function setStatus(message,error=false,busy=false) {
    $('status').textContent=message;$('status').classList.toggle('error',error);$('status').classList.toggle('busy',busy);
  }
  function selectCategory(name,include) {
    state.selected=include?[...new Set([...state.selected,name])]:state.selected.filter(n=>n!==name);
    if(include)state.active=name;
    persist();renderLibrary();renderFilters();renderSummary();
  }
  function renderLibrary() {
    const container=$('category-list');container.replaceChildren();
    const query=$('category-search').value.trim().toLocaleLowerCase();let visible=0;
    for(const name of names) {
      if(query&&!`${name} ${catalog[name].subtitle||''}`.toLocaleLowerCase().includes(query))continue;
      visible++;
      const row=element('div','category-row');row.classList.toggle('selected',state.selected.includes(name));row.classList.toggle('active',state.active===name);
      const input=element('input');input.type='checkbox';input.checked=state.selected.includes(name);input.setAttribute('aria-label',`Include ${name} in deck`);input.dataset.category=name;
      input.addEventListener('change',()=>selectCategory(name,input.checked));
      const button=element('button','category-button');button.type='button';button.append(glyph(name),element('span','',name));button.setAttribute('aria-pressed',String(state.active===name));
      button.addEventListener('click',()=>{state.active=name;persist();renderLibrary();renderFilters();});
      row.append(input,button);container.append(row);
    }
    if(!visible)container.append(element('div','no-results','No matching categories.'));
    $('selected-count').textContent=`${state.selected.length} selected`;
  }
  function displayValue(key,value) {
    if(key==='size')return {T:'Tiny',S:'Small',M:'Medium',L:'Large',H:'Huge',G:'Gargantuan',C:'Colossal'}[value]||value;
    if(key==='cr')return value;
    return labels[value]||String(value).charAt(0).toUpperCase()+String(value).slice(1);
  }
  function normalizedFilters(name) {
    const result={};
    for(const [key,values] of Object.entries(state.filters[name]||{})) {
      const allowed=catalog[name].filters?.[key]||[];
      const selected=values.filter(value=>allowed.includes(value));
      if(selected.length&&selected.length!==allowed.length)result[key]=selected;
    }
    return result;
  }
  function renderFilters() {
    const container=$('filter-panel');container.replaceChildren();const name=state.active;
    if(!name){container.append(element('h2','','Your library is empty.'),element('p','help','Open Data setup to install a compatible dataset.'));return;}
    const heading=element('div','editor-heading'),title=element('div');title.append(element('div','eyebrow','Content selection'),element('h2','',name));
    const reset=element('button','quiet small-button','Reset filters');reset.addEventListener('click',()=>{state.filters[name]={};persist();renderFilters();renderSummary();});heading.append(title,reset);
    const include=element('label','include-toggle'),checkbox=element('input');checkbox.type='checkbox';checkbox.checked=state.selected.includes(name);checkbox.addEventListener('change',()=>selectCategory(name,checkbox.checked));include.append(checkbox,document.createTextNode(`Include ${name} in this deck`));
    container.append(heading,include,element('p','editor-description',catalog[name].subtitle||'Leave a filter group empty to include every value.'));
    for(const [key,values] of Object.entries(catalog[name].filters||{})) {
      const group=element('fieldset','filter-group'),legend=element('legend','filter-legend');legend.append(document.createTextNode(filterNames[key]||pretty(key)),element('small','','Empty means all'));
      const controls=element('div','filter-controls'),selection=element('span','help');const resetGroup=element('button','group-reset','Reset group');resetGroup.type='button';resetGroup.setAttribute('aria-label',`Reset ${filterNames[key]||key} filter`);
      const chips=element('div','filter-chips');
      const update=()=>{const count=(state.filters[name]?.[key]||[]).length;selection.textContent=count&&count<values.length?`${count} selected`:'All values';};
      values.forEach((value,index)=>{
        const label=element('label','filter-chip'),input=element('input');input.type='checkbox';input.value=value;input.checked=(state.filters[name]?.[key]||[]).includes(value);input.dataset.datasetName=name;input.dataset.filterKey=key;
        label.classList.toggle('selected',input.checked);label.append(input,document.createTextNode(displayValue(key,value)));
        input.addEventListener('change',()=>{state.filters[name]||={};const current=new Set(state.filters[name][key]||[]);input.checked?current.add(value):current.delete(value);state.filters[name][key]=[...current];label.classList.toggle('selected',input.checked);persist();update();renderSummary();});
        chips.append(label);
      });
      resetGroup.addEventListener('click',()=>{state.filters[name]||={};state.filters[name][key]=[];chips.querySelectorAll('input').forEach(input=>{input.checked=false;input.parentElement.classList.remove('selected');});persist();update();renderSummary();});
      controls.append(selection,resetGroup);group.append(legend,controls,chips);container.append(group);update();
    }
    if(!Object.keys(catalog[name].filters||{}).length)container.append(element('p','help','This category includes all available entries.'));
  }
  function renderSummary() {
    const count=state.selected.length;$('summary-title').textContent=count?`${count} ${count===1?'category':'categories'}.`:'A fresh start.';
    $('summary-help').textContent=count?'Your selections are ready when you are.':'Select content from the library to begin.';
    const container=$('selection-summary');container.replaceChildren();
    names.filter(name=>state.selected.includes(name)).forEach(name=>{
      const entry=element('div','selection-entry'),remove=element('button','','×');remove.setAttribute('aria-label',`Remove ${name} from deck`);remove.addEventListener('click',()=>selectCategory(name,false));
      const filters=normalizedFilters(name),description=Object.entries(filters).map(([key,values])=>`${filterNames[key]||pretty(key)}: ${values.map(v=>displayValue(key,v)).join(', ')}`).join(' · ');
      entry.append(remove,element('strong','',name),element('span','',description||'All values included'));container.append(entry);
    });
    $('generateBtn').disabled=generating||!count;$('generateBacksBtn').disabled=generating;
    $('appearance-label').textContent=uploads.background?'Custom background':state.assets.background===defaults.background?'Classic parchment':state.assets.background==='Default'?'Automatic artwork':pretty(state.assets.background);
  }
  function showSection(name) {
    for(const section of ['content','appearance']) {
      const active=name===section;$(`${section}-section`).hidden=!active;$(`${section}-tab`).classList.toggle('active',active);$(`${section}-tab`).setAttribute('aria-selected',String(active));
    }
  }
  async function svgData(file) {
    if(!file.name.toLowerCase().endsWith('.svg'))throw new Error('Choose an SVG file for custom artwork.');
    const text=await file.text(),parsed=new DOMParser().parseFromString(text,'image/svg+xml');
    if(parsed.querySelector('parsererror')||parsed.documentElement.localName!=='svg')throw new Error('The selected file is not a valid SVG.');
    const bytes=new TextEncoder().encode(text);let binary='';for(let i=0;i<bytes.length;i+=4096)binary+=String.fromCharCode(...bytes.subarray(i,i+4096));
    return 'data:image/svg+xml;base64,'+btoa(binary);
  }
  function renderAppearance() {
    const container=$('appearance-controls');container.replaceChildren();
    for(const [key,title,options] of [['background','Background',config.assets.backgrounds],['watermark','Watermark',config.assets.watermarks],['cardBack','Card back',config.assets.cardBacks]]) {
      const section=element('section','asset-control'),heading=element('div','asset-heading'),label=element('label','',title),reset=element('button','small-button quiet','Clear upload');reset.type='button';reset.hidden=!uploads[key];reset.setAttribute('aria-label',`Clear ${title.toLowerCase()} upload`);
      const select=element('select');select.id=`asset-${key}`;label.htmlFor=select.id;const automatic=element('option','','Automatic');automatic.value='Default';select.append(automatic);
      (options||[]).forEach(name=>{const option=element('option','',pretty(name));option.value=name;select.append(option);});select.value=state.assets[key];
      const body=element('div','asset-body'),preview=element('div',`asset-preview ${key==='watermark'?'watermark':''}`),controls=element('div','asset-options'),file=element('input');file.type='file';file.accept='.svg,image/svg+xml';file.id=`upload-${key}`;file.setAttribute('aria-label',`Upload custom ${title.toLowerCase()} SVG`);
      const description=element('p','help',uploads[key]?uploads[key].name:key==='watermark'?'Transparent SVG emblem.':'Portrait SVG artwork.');
      const update=()=>{preview.style.backgroundImage=`url('${uploads[key]?.data||'/icons/'+encodeURIComponent(state.assets[key]==='Default'?defaults[key]:state.assets[key])}')`;};
      select.addEventListener('change',()=>{state.assets[key]=select.value;persist();update();renderSummary();});
      file.addEventListener('change',async()=>{if(!file.files[0])return;try{const chosen=file.files[0];uploads[key]={name:chosen.name,data:await svgData(chosen)};description.textContent=chosen.name;reset.hidden=false;update();renderSummary();setStatus(`${title} artwork loaded.`);}catch(error){file.value='';setStatus(error.message,true);}});
      reset.addEventListener('click',()=>{delete uploads[key];file.value='';description.textContent=key==='watermark'?'Transparent SVG emblem.':'Portrait SVG artwork.';reset.hidden=true;update();renderSummary();});
      heading.append(label,reset);controls.append(select,file,description);body.append(preview,controls);section.append(heading,body);container.append(section);update();
    }
  }
  function buildPayload(kind='Cards') {
    const payload={customAssets:{},selectedAssets:kind==='Backs'?{cardBack:state.assets.cardBack}:{...state.assets}};
    for(const key of kind==='Backs'?['cardBack']:['background','watermark'])if(uploads[key])payload.customAssets[key]=uploads[key].data;
    if(kind==='Backs')return payload;
    payload.datasets=[];
    for(const name of names.filter(n=>state.selected.includes(n))) {
      const data=catalog[name],filters=normalizedFilters(name),content=filters.playtest;delete filters.playtest;
      const official=!content||content.includes('Official'),playtest=!content||content.includes('Playtest');
      if(data.playtestFile&&official&&playtest) {
        payload.datasets.push({name,file:data.file,filters:{...filters}},{name,file:data.playtestFile,filters:{...filters}});
      } else payload.datasets.push({name,file:data.playtestFile&&playtest&&!official?data.playtestFile:data.file,filters});
    }
    return payload;
  }
  async function post(url,payload) {
    const response=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify(payload)});
    const type=response.headers.get('Content-Type')||'';
    const result=type.includes('application/json')?await response.json():{error:(await response.text()).replace(/<[^>]*>/g,' ').trim()};
    if(!response.ok||result.error)throw new Error(result.error||'The request could not be completed.');return result;
  }
  async function generate(kind) {
    if(generating)return;
    const payload=buildPayload(kind);if(kind==='Cards'&&!payload.datasets.length){setStatus('Select at least one content category.');return;}
    generating=true;renderSummary();setStatus(kind==='Cards'?'Generating your deck…':'Generating card backs…',false,true);
    $(kind==='Cards'?'result-panel':'backs-panel').hidden=true;
    try {
      const result=await post(kind==='Cards'?'/generate':'/generate_backs',payload);
      if(!result.card_count){setStatus('No cards matched these filters. Adjust the selection and try again.');return;}
      if(kind==='Backs'){$('backs-panel').hidden=false;$('backs-preview-link').href=result.preview;}
      else {
        $('result-panel').hidden=false;$('result-title').textContent=`${result.card_count.toLocaleString()} cards, ready to deal.`;
        $('result-detail').textContent=`${result.item_count.toLocaleString()} entries · ${result.sheet_count.toLocaleString()} sheets · Letter paper`;
        $('preview-link').href=result.preview;$('result-types').replaceChildren();
        Object.entries(result.type_counts||{}).sort((a,b)=>b[1]-a[1]).forEach(([name,count])=>$('result-types').append(element('span','',`${name} · ${count}`)));
      }
      setStatus(kind==='Backs'?'Card backs are ready to preview or export.':'Your deck is ready. Preview it or save a complete PDF.');
      $(kind==='Backs'?'backs-panel':'result-panel').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'nearest'});
    } catch(error){setStatus(error.message,true);}finally{generating=false;renderSummary();}
  }
  async function exportPdf(kind) {
    if(exporting){setStatus('A PDF export is already in progress.');return;}
    exporting=true;pdfResult=null;$('export-panel').hidden=false;$('pdf-download').hidden=true;$('pdf-share').hidden=true;$('export-heading').textContent='Preparing your PDF';$('export-message').textContent='You can keep this window open while the PDF is created.';$('export-progress').removeAttribute('value');
    $('export-cards').disabled=true;$('export-backs').disabled=true;
    try {
      const job=await post('/export-pdf',{kind});
      if(config.platform==='android'&&window.AndroidUI?.beginExport)window.AndroidUI.beginExport(job.id);
      let result;
      do {
        await new Promise(resolve=>setTimeout(resolve,700));
        const response=await fetch('/export-status?id='+encodeURIComponent(job.id));result=await response.json();
        if(!response.ok||result.state==='failed')throw new Error(result.error||'PDF export could not finish.');
        const total=result.total_sheets||0,complete=result.completed_sheets||0;
        $('export-progress-label').textContent=total?`${complete} / ${total} pages`:'';
        if(total){$('export-progress').max=total;$('export-progress').value=complete;}
        $('export-heading').textContent=result.phase==='assembling'?'Finishing your PDF':'Creating your PDF';
      } while(result.state!=='complete');
      pdfResult=result;$('export-heading').textContent='Your PDF is ready.';$('export-message').textContent=`One complete PDF · ${(result.bytes/1000000).toFixed(1)} MB · Print at 100% on Letter paper.`;
      $('pdf-download').href=result.download;$('pdf-download').download=result.download.split('/').pop();$('pdf-download').hidden=false;
      $('pdf-share').hidden=!(config.platform==='android'&&window.AndroidUI?.sharePdf);
      setStatus('PDF export complete.');
    } catch(error){$('export-heading').textContent='Export needs attention';$('export-message').textContent=error.message;setStatus(error.message,true);}finally{exporting=false;$('export-cards').disabled=false;$('export-backs').disabled=false;}
  }
  $('pdf-download').addEventListener('click',event=>{if(config.platform==='android'&&window.AndroidUI?.savePdf&&pdfResult){event.preventDefault();window.AndroidUI.savePdf(pdfResult.download.split('/').pop());}});
  $('pdf-share').addEventListener('click',()=>{if(pdfResult)window.AndroidUI?.sharePdf(pdfResult.download.split('/').pop());});
  $('category-search').addEventListener('input',renderLibrary);
  ['content','appearance'].forEach(name=>$(`${name}-tab`).addEventListener('click',()=>showSection(name)));
  document.querySelector('.section-tabs').addEventListener('keydown',event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();const next=event.key==='Home'?'content':event.key==='End'?'appearance':$('content-tab').getAttribute('aria-selected')==='true'?'appearance':'content';showSection(next);$(`${next}-tab`).focus();}});
  $('show-appearance').addEventListener('click',()=>{showSection('appearance');$('appearance-tab').focus();});
  $('reset-appearance').addEventListener('click',()=>{state.assets={...defaults};Object.keys(uploads).forEach(key=>delete uploads[key]);persist();renderAppearance();renderSummary();});
  $('reset-deck').addEventListener('click',()=>{state.selected=[];state.filters={};state.assets={...defaults};Object.keys(uploads).forEach(key=>delete uploads[key]);$('category-search').value='';persist();renderLibrary();renderFilters();renderAppearance();renderSummary();setStatus('Deck selections reset.');});
  $('generateBtn').addEventListener('click',()=>generate('Cards'));$('generateBacksBtn').addEventListener('click',()=>generate('Backs'));
  $('export-cards').addEventListener('click',()=>exportPdf('Cards'));$('export-backs').addEventListener('click',()=>exportPdf('Backs'));
  window.WorkbenchTools={buildPayload,getSelection:()=>JSON.parse(JSON.stringify(state))};
  if(config.platform==='android')document.querySelectorAll('a[target="_blank"]').forEach(link=>link.removeAttribute('target'));
  if(config.pdfExport===false){$('export-cards').hidden=true;$('export-backs').hidden=true;}
  renderLibrary();renderFilters();renderAppearance();renderSummary();
})();
