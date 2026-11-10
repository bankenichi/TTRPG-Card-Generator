"""Compact native Chromium PDFs of the existing fitted HTML card renderer."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent
JOBS = ROOT / '.pdf-jobs'
DPI = 300
# Chromium's masked pseudo-elements can paint opaque rectangles when one
# native print call spans several sheets. Isolate physical sheets internally.
PDF_BATCH_SHEETS = 1
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / "pdf-browser"))


def _pid_running(pid):
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle: return False
        try:
            code = wintypes.DWORD()
            return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _write_json(path, value):
    path = Path(path)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2), encoding='utf-8')
    os.replace(temp, path)


def start_export(kind):
    if kind not in ('Cards', 'Backs'):
        raise ValueError('Choose cards or backs')
    JOBS.mkdir(exist_ok=True)
    for status_path in JOBS.glob('*/status.json'):
        status = json.loads(status_path.read_text(encoding='utf-8'))
        if status.get('state') in ('queued', 'rendering'):
            pid_path = status_path.parent / 'pid'
            if not pid_path.exists() or not _pid_running(int(pid_path.read_text())):
                status['state'] = 'failed'
                status['error'] = 'Export process stopped; start a new export.'
                _write_json(status_path, status)
            else:
                raise ValueError('Another PDF export is running; wait for it to finish')
    source = ROOT / f'Custom_Deck_{kind}.html'
    if not source.is_file():
        raise ValueError('Generate the deck before exporting it')
    manifest_path = source.with_suffix('.manifest.json')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {'files': [source.name]}
    job_id = uuid.uuid4().hex
    directory = JOBS / job_id
    directory.mkdir()
    files = []
    for name in manifest['files']:
        if Path(name).name != name or not name.startswith(f'Custom_Deck_{kind}') or not name.endswith('.html'):
            raise ValueError('Invalid deck manifest')
        snapshot = directory / name
        snapshot.write_bytes((ROOT / name).read_bytes())
        files.append(str(snapshot))
    status_path = directory / 'status.json'
    _write_json(status_path, {'state': 'queued', 'completed_sheets': 0})
    job_path = directory / 'job.json'
    output = ROOT / f'Custom_Deck_{kind}_{job_id}.pdf'
    _write_json(job_path, {'files': files, 'output': str(output), 'status': str(status_path)})
    process = subprocess.Popen([sys.executable, '-s', str(Path(__file__).resolve()), '--job', str(job_path.resolve())],
                               cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    # The worker owns status updates; PID is separately recorded to avoid update races.
    (directory / 'pid').write_text(str(process.pid), encoding='ascii')
    return job_id


def export_status(job_id):
    if not isinstance(job_id, str) or len(job_id) != 32 or any(c not in '0123456789abcdef' for c in job_id):
        raise ValueError('Invalid export id')
    directory = JOBS / job_id
    status = json.loads((directory / 'status.json').read_text(encoding='utf-8'))
    if status.get('state') in ('queued', 'rendering') and (directory / 'pid').exists():
        if not _pid_running(int((directory / 'pid').read_text())):
            status.update(state='failed', error='Export process stopped; start a new export.')
    return status



def compact_pdf(writer):
    """Deduplicate nested masks, images, forms, and fonts to a fixed point.

    One pass only merges leaf resources. Their parents become identical in the
    next pass; stopping after one pass leaves thousands of duplicate textures.
    Pinned pypdf exposes its object table, so count live objects to convergence.
    """
    while True:
        before=sum(obj is not None for obj in writer._objects)
        writer.compress_identical_objects(remove_duplicates=True,remove_unreferenced=True)
        if sum(obj is not None for obj in writer._objects)==before:
            return writer


def _content_hash(page):
    contents=page.get_contents()
    return hashlib.sha256(contents.get_data() if contents is not None else b'').hexdigest()


def _verify_page(page, record):
    from pdf_layout import text_signature
    if tuple(map(float,page.mediabox)) != (0.0,0.0,612.0,792.0):
        raise ValueError('PDF sheet dimensions differ from Letter paper')
    if text_signature(page.extract_text()) != record['text_signature']:
        raise ValueError(f"PDF text differs from the fitted HTML on sheet {record['sheet']}")
    digest=_content_hash(page)
    if record.get('pdf_content_sha256',digest) != digest:
        raise ValueError('PDF drawing commands or sheet order changed during assembly')
    record['pdf_content_sha256']=digest


def _merge_parts(parts, output):
    from pypdf import PdfReader,PdfWriter
    writer=PdfWriter()
    for part in parts:
        with open(part,'rb') as stream:
            writer.append(PdfReader(stream),import_outline=False)
    compact_pdf(writer)
    count=len(writer.pages)
    writer.write(output);writer.close()
    return count


def write_pdf_batches(pdf_path, records=None, batch_size=5):
    """Optional small print jobs, with all native vector content retained."""
    from pypdf import PdfReader,PdfWriter
    if batch_size<1:raise ValueError('Batch size must be positive')
    pdf_path=Path(pdf_path);downloads=[]
    with pdf_path.open('rb') as source:
        reader=PdfReader(source)
        if len(reader.pages)<=batch_size:return downloads
        for start in range(0,len(reader.pages),batch_size):
            end=min(start+batch_size,len(reader.pages))
            destination=pdf_path.with_name(f'{pdf_path.stem}_sheets_{start+1:04d}-{end:04d}.pdf')
            writer=PdfWriter()
            for index in range(start,end):writer.add_page(reader.pages[index])
            compact_pdf(writer);writer.write(destination);writer.close()
            if records is not None:
                with destination.open('rb') as stream:
                    batch=PdfReader(stream)
                    for page,record in zip(batch.pages,records[start:end],strict=True):_verify_page(page,record)
            downloads.append({'download':'/'+destination.name,'first_sheet':start+1,'last_sheet':end,'bytes':destination.stat().st_size})
    return downloads


def _render_batch(job):
    """An isolated, short-lived process prints one physical sheet."""
    from playwright.sync_api import sync_playwright,Error as BrowserError
    from pypdf import PdfReader,PdfWriter
    from pdf_layout import CAPTURE_LAYOUT,CHECK_OVERFLOW,PRINT_SHEET_CSS,validate_layout,text_signature
    from render_assets import font_css
    from pdf_fills import coalesce_native_fills
    from deck_output import split_document
    document=Path(job['document']).read_text(encoding='utf-8')
    if len(split_document(document)[1]) != 1:
        raise ValueError('Native PDF mask rendering requires one sheet per job')
    for attempt in range(2):
        buffer=None
        try:
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch(channel='chromium',headless=True)
                try:
                    version=browser.version
                    context=browser.new_context(viewport={'width':816,'height':1056},device_scale_factor=DPI/96)
                    page=context.new_page()
                    page.route('**/*',lambda route:route.fulfill(status=200,content_type='text/css',body=font_css())
                               if route.request.url.startswith('https://fonts.googleapis.com/') else route.abort())
                    page.emulate_media(media='screen')
                    page.set_content(document,wait_until='load',timeout=120000)
                    page.add_style_tag(content=PRINT_SHEET_CSS)
                    page.evaluate("""async()=>{
                        await document.fonts.ready;
                        if(window.fitCards)await window.fitCards();
                        else if(typeof window.onload==='function')window.onload();
                        window.cardLayoutReady=true;
                    }""")
                    page.wait_for_function('window.cardLayoutReady === true',timeout=120000)
                    overflow=page.evaluate(CHECK_OVERFLOW)
                    if overflow:raise ValueError('Card content overflows its rendered bounds: '+', '.join(overflow[:5]))
                    before=page.evaluate(CAPTURE_LAYOUT,False);validate_layout(before)
                    buffer=page.pdf(format='Letter',print_background=True,prefer_css_page_size=True,
                        scale=1,margin={'top':'0','right':'0','bottom':'0','left':'0'},tagged=False,outline=False)
                    if before!=page.evaluate(CAPTURE_LAYOUT,False):raise ValueError('Printing changed the fitted HTML card layout')
                    reader=PdfReader(io.BytesIO(buffer))
                    if len(reader.pages)!=len(before):raise ValueError('PDF sheet count differs from the fitted HTML')
                    writer=PdfWriter();writer.append(reader,import_outline=False)
                    records=[]
                    for index,(native_page,pdf_page,layout) in enumerate(zip(reader.pages,writer.pages,before,strict=True)):
                        record={'sheet':job['first_sheet']+index,'cards':len(layout['cards']),
                            'text_signature':text_signature(''.join(card['text'] for card in layout['cards'])),
                            'layout_sha256':hashlib.sha256(json.dumps(layout,sort_keys=True).encode()).hexdigest(),'layout_unchanged':True}
                        _verify_page(native_page,record)
                        # Preserve native provenance, then freeze only the guarded
                        # fill union for the unchanged downstream drawing checks.
                        record['native_pdf_content_sha256']=record['pdf_content_sha256']
                        record['pdf_background_fill_joins']=coalesce_native_fills(pdf_page,writer)
                        if record['pdf_background_fill_joins']:
                            del record['pdf_content_sha256']
                            _verify_page(pdf_page,record)
                        records.append(record)
                    compact_pdf(writer);writer.write(job['pdf']);writer.close()
                    with open(job['pdf'],'rb') as stream:
                        compacted=PdfReader(stream)
                        for pdf_page,record in zip(compacted.pages,records,strict=True):_verify_page(pdf_page,record)
                    if job.get('evidence_dir'):
                        evidence=Path(job['evidence_dir']);evidence.mkdir(parents=True,exist_ok=True)
                        layouts=page.evaluate(CAPTURE_LAYOUT,True)
                        selected=job.get('evidence_sheets')
                        for layout,record,slot in zip(layouts,records,page.locator('.page').all(),strict=True):
                            (evidence/f"sheet-{record['sheet']:04d}.layout.json").write_text(json.dumps(layout,ensure_ascii=False),encoding='utf-8')
                            if selected is None or record['sheet'] in selected:
                                slot.screenshot(path=str(evidence/f"sheet-{record['sheet']:04d}.png"),animations='disabled',timeout=120000)
                    return {'state':'complete','chromium':version,'sheets':records}
                finally:
                    try:browser.close()
                    except BrowserError:pass
        except BrowserError:
            if attempt:raise
        except Exception:
            if buffer:Path(job['pdf']).with_suffix('.failed-native.pdf').write_bytes(buffer)
            raise


def _launch_batch(job_path):
    with job_path.with_suffix('.log').open('wb') as log:
        return subprocess.Popen([sys.executable,'-s',str(Path(__file__).resolve()),'--batch',str(job_path.resolve())],
            cwd=ROOT,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))


def render_pdf(files, output, progress=None, evidence_dir=None, evidence_sheets=None, max_workers=None, batch_timeout_seconds=300):
    from pypdf import PdfReader
    from deck_output import split_document
    if max_workers is None:max_workers=min(4,max(1,(os.cpu_count() or 2)//2))
    if not 1<=max_workers<=4:raise ValueError('Choose between one and four PDF workers')
    if batch_timeout_seconds<=0:raise ValueError('PDF batch timeout must be positive')
    started=time.monotonic();output=Path(output);documents=[]
    for filename in files:
        head,sheets,tail=split_document(Path(filename).read_text(encoding='utf-8'))
        documents.extend(head+''.join(sheets[i:i+PDF_BATCH_SHEETS])+tail for i in range(0,len(sheets),PDF_BATCH_SHEETS))
    total=sum(document.count('<div class="page">') for document in documents)
    if not total:raise ValueError('Deck has no sheets')
    work=output.parent/('.render-'+uuid.uuid4().hex);work.mkdir()
    jobs=[];first=1
    for index,document in enumerate(documents):
        source=work/f'{index:05d}.html';source.write_text(document,encoding='utf-8')
        config={'document':str(source.resolve()),'pdf':str((work/f'{index:05d}.pdf').resolve()),
            'result':str((work/f'{index:05d}.result.json').resolve()),'first_sheet':first,
            'evidence_dir':str(Path(evidence_dir).resolve()) if evidence_dir else None,
            'evidence_sheets':sorted(evidence_sheets) if evidence_sheets is not None else None}
        first+=document.count('<div class="page">')
        job_path=work/f'{index:05d}.job.json';_write_json(job_path,config);jobs.append((job_path,config))
    pending={};launched={};completed={};success=False;next_job=0
    def update(phase='rendering'):
        if progress:progress({'state':'rendering','phase':phase,'completed_sheets':sum(len(r['sheets']) for r in completed.values()),'total_sheets':total})
    update()
    try:
        while next_job<len(jobs) or pending:
            while next_job<len(jobs) and len(pending)<max_workers:
                path,config=jobs[next_job];pending[next_job]=_launch_batch(path);launched[next_job]=time.monotonic();next_job+=1
            for index,process in list(pending.items()):
                code=process.poll()
                if code is None:
                    if time.monotonic()-launched[index]>batch_timeout_seconds:
                        raise TimeoutError('PDF rendering timed out. Completed parts and diagnostic logs were retained; start a new export to retry.')
                    continue
                result_path=Path(jobs[index][1]['result'])
                result=json.loads(result_path.read_text(encoding='utf-8')) if result_path.exists() else {'state':'failed','error':'PDF batch process stopped unexpectedly; details were saved with the export job.'}
                if code or result['state']!='complete':raise ValueError(result.get('error','PDF batch failed'))
                completed[index]=result;del pending[index];update()
            if pending:time.sleep(0.1)
        records=[record for index in range(len(jobs)) for record in completed[index]['sheets']]
        if [r['sheet'] for r in records]!=list(range(1,total+1)):raise ValueError('Rendered PDF sheet sequence changed')
        update('assembling');temporary=work/'complete.pdf'
        if _merge_parts([config['pdf'] for _,config in jobs],temporary)!=total:raise ValueError('Merged PDF sheet count changed')
        with temporary.open('rb') as stream:
            reader=PdfReader(stream)
            for pdf_page,record in zip(reader.pages,records,strict=True):_verify_page(pdf_page,record)
        os.replace(temporary,output)
        result={'state':'complete','completed_sheets':total,'total_sheets':total,'download':'/'+output.name,
            'format':'native-vector','searchable_text':True,'layout_verified':True,'text_verified':True,
            'pixel_identical':False,'chromium':completed[0]['chromium'],'seconds':round(time.monotonic()-started,2),
            'bytes':output.stat().st_size,'sheets':records,'render_workers':max_workers}
        _write_json(output.with_suffix('.verification.json'),result)
        if progress:progress({k:v for k,v in result.items() if k!='sheets'})
        success=True;return result
    finally:
        for process in pending.values():
            if process.poll() is None:process.terminate()
        for process in pending.values():
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill();process.wait(timeout=10)
        # Failed jobs retain their completed parts, source snapshots, and logs.
        if success:
            import shutil
            shutil.rmtree(work)


def _run_job(path):
    job=json.loads(Path(path).read_text(encoding='utf-8'))
    try:
        render_pdf(job['files'],job['output'],progress=lambda value:_write_json(job['status'],value))
    except Exception as exc:
        message=str(exc)
        if 'Executable doesn' in message or 'No module named' in message:
            message='PDF renderer is missing. Run install.bat to install the pinned renderer. '+message
        _write_json(job['status'],{'state':'failed','error':message})
        raise


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--job':_run_job(sys.argv[2])
    elif len(sys.argv)==3 and sys.argv[1]=='--batch':
        job=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
        try:_write_json(job['result'],_render_batch(job))
        except Exception as exc:
            _write_json(job['result'],{'state':'failed','error':str(exc)})
            raise

