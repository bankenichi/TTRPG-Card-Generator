(() => {
  const config=window.SETUP,$=id=>document.getElementById(id);let busy=false;
  function status(message,error=false){$('setup-status').hidden=false;$('setup-status').textContent=message;$('setup-status').classList.toggle('error',error);$('setup-status').classList.toggle('busy',busy);}
  function setBusy(value){busy=value;document.querySelectorAll('button,input').forEach(e=>e.disabled=value);$('setup-status').classList.toggle('busy',value);}
  function ready(){config.ready=true;$('ready-panel').hidden=false;$('manage-button').hidden=false;$('import-panels').hidden=true;}
  function complete(success,message){setBusy(false);status(message|| (success?'Your data is ready.':'The import could not finish.'),!success);if(success)ready();}
  async function responseResult(response){const result=await response.json();if(!response.ok)throw new Error(result.message||result.error||'The request failed.');return result;}
  async function waitForImport(id){let current;do{await new Promise(r=>setTimeout(r,600));current=await responseResult(await fetch('/setup-status?id='+encodeURIComponent(id)));status(current.message||'Importing your data…');}while(current.state==='running');complete(current.state==='complete',current.message);}
  $('manage-button').addEventListener('click',()=>{$('import-panels').hidden=!$('import-panels').hidden;});
  $('launch-button').addEventListener('click',async()=>{
    if(config.inGenerator||config.platform==='android'){location.assign('/');return;}
    setBusy(true);status('Opening your workbench…');
    try{const response=await fetch('/launch',{method:'POST'});if(!response.ok)throw new Error('The workbench could not open.');status('The workbench is opening in a new window. You can close this setup tab.');}catch(error){complete(false,error.message);}
  });
  $('repository-form').addEventListener('submit',async event=>{
    event.preventDefault();if(busy)return;const url=$('repository-url').value.trim();if(!url)return;
    setBusy(true);status(config.platform==='android'?'Downloading your data archive…':'Importing your repository. This can take a few minutes…');
    try{
      if(config.platform==='android'){
        const result=await responseResult(await fetch('/setup-url',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})}));
        await waitForImport(result.id);
      }else{
        const result=await responseResult(await fetch('/setup?type=git&url='+encodeURIComponent(url),{method:'POST'}));complete(result.success,result.message);
      }
    }catch(error){complete(false,error.message);}
  });
  $('zip-form').addEventListener('submit',async event=>{
    event.preventDefault();if(busy)return;
    if(config.platform==='android'&&window.AndroidUI?.importDataset){setBusy(true);status('Choose a ZIP archive from your device.');window.AndroidUI.importDataset();return;}
    const file=$('dataset-zip').files[0];if(!file){status('Choose a ZIP archive first.',true);return;}
    setBusy(true);status('Importing your ZIP archive…');
    try{if(config.platform==='android'){const result=await responseResult(await fetch('/setup-zip',{method:'POST',headers:{'Content-Type':'application/zip'},body:file}));await waitForImport(result.id);}else{const data=new FormData();data.append('zip',file);const result=await responseResult(await fetch('/setup-zip',{method:'POST',body:data}));complete(result.success,result.message);}}catch(error){complete(false,error.message);}
  });
  window.WorkbenchSetup={onNativeImportProgress:message=>status(message),onNativeImportComplete:complete};
  if(config.platform==='android'){
    $('repository-title').textContent='Download your archive.';$('repository-help').textContent='Enter a direct ZIP archive URL for your repository.';$('repository-label').textContent='Repository ZIP URL';$('repository-url').placeholder='https://github.com/example/data/archive/refs/heads/main.zip';$('repository-button').textContent='Download and import';
    if(window.AndroidUI?.importDataset){$('dataset-zip').parentElement.hidden=true;}
  }
  if(config.ready)ready();
})();
