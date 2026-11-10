"""Exercise production setup handlers in isolated storage, never installed data."""
import argparse
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch
import urllib.request
from urllib.parse import quote, urlsplit


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform',choices=('desktop','android'),required=True)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();source=args.source.resolve();out=args.out.resolve()
    sys.path.insert(0,str(source))
    raw=(source/'bundled_srd/srd-5.2.1.zip').read_bytes()
    original_open=urllib.request.OpenerDirector.open
    def local_only(opener,request,*a,**kw):
        url=request.full_url if hasattr(request,'full_url') else request
        if urlsplit(url).hostname!='127.0.0.1':raise AssertionError('Unexpected network request: '+url)
        return original_open(opener,request,*a,**kw)

    with tempfile.TemporaryDirectory(prefix='bundled-srd-check-') as folder:
        scratch=Path(folder);destination=scratch/'generators'/('data' if args.platform=='desktop' else 'rpg_data')
        os.chdir(scratch)
        if args.platform=='desktop':
            import data_paths
            data_paths.GENERATORS_DIR=str(scratch/'generators');data_paths.DEFAULT_DATA_DIR=str(destination)
            import launcher
            launcher.GENERATORS_DIR=data_paths.GENERATORS_DIR;launcher.DATA_DIR=str(destination)
            handler=launcher.LauncherRequestHandler;setup='/';install='/setup?type=srd'
        else:
            import card_controller
            handler=card_controller.GeneratorRequestHandler;setup='/data-setup';install='/setup-srd'
        server=HTTPServer(('127.0.0.1',0),handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        base='http://127.0.0.1:'+str(server.server_port)
        def request(path,data=None,content_type=None):
            headers={'Content-Type':content_type} if content_type else {}
            with urllib.request.urlopen(urllib.request.Request(base+path,data=data,headers=headers),timeout=30) as response:
                return response.read().decode('utf-8')
        def finish(result):
            result=json.loads(result)
            if args.platform=='android':
                identifier=result['id'];deadline=time.monotonic()+30
                while True:
                    result=json.loads(request('/setup-status?id='+identifier))
                    if result['state']!='running':break
                    if time.monotonic()>deadline:raise TimeoutError('Import stalled')
                    time.sleep(.05)
                assert result['state']=='complete',result
            else:assert result['success'],result
        try:
            with patch.object(urllib.request.OpenerDirector,'open',local_only):
                page=request(setup)
                assert 'Use included SRD 5.2.1' in page and '"ready": false' in page
                finish(request(install,b''))
                from verified_srd import validate_srd_manifest
                manifest=validate_srd_manifest(destination)
                assert len(manifest['sha256'])==40
                assert not (destination/'prerelease').exists()
                marker=destination/'keep-existing-library';marker.write_bytes(b'kept')
                assert '"ready": true' in request(setup) and marker.read_bytes()==b'kept'
                privacy=request('/privacy');about=request('/about')
                assert 'We do not collect, sell, or track your data.' in privacy
                assert 'github.com/bankenichi/TTRPG-Card-Generator/issues' in privacy
                assert 'href="/privacy"' in about and 'href="/privacy"' in page
                if args.platform=='desktop':
                    # The generic clone path remains functional for user-selected repos.
                    repo=scratch/'custom-repository'
                    import zipfile
                    with zipfile.ZipFile(source/'bundled_srd/srd-5.2.1.zip') as archive:archive.extractall(repo)
                    for command in (['init'],['add','.'],['-c','user.name=Setup test','-c','user.email=setup@example.invalid','commit','-m','Local fixture']):
                        subprocess.run([launcher.get_git_cmd(),'-C',str(repo),*command],check=True,capture_output=True)
                    finish(request('/setup?type=git&url='+quote(str(repo)),b''))
                    boundary='BundledSrdSetupCheck'
                    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="zip"; filename="data.zip"\r\nContent-Type: application/zip\r\n\r\n'.encode()+raw+f'\r\n--{boundary}--\r\n'.encode())
                    finish(request('/setup-zip',body,'multipart/form-data; boundary='+boundary))
                else:
                    class ArchiveHandler(BaseHTTPRequestHandler):
                        def do_GET(self):
                            self.send_response(200);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
                    archive_server=HTTPServer(('127.0.0.1',0),ArchiveHandler)
                    threading.Thread(target=archive_server.serve_forever,daemon=True).start()
                    try:
                        url='http://127.0.0.1:'+str(archive_server.server_port)+'/custom-catalog.zip'
                        finish(request('/setup-url',json.dumps({'url':url}).encode(),'application/json'))
                    finally:archive_server.shutdown();archive_server.server_close()
                    finish(request('/setup-zip',raw,'application/zip'))
                assert not marker.exists()  # Only these explicit imports replace a library.
                validate_srd_manifest(destination)
                # Keep an isolated install for the rendering parity runner.
                import shutil
                installed=out/'installed'
                shutil.copytree(destination,installed)
        finally:
            server.shutdown();server.server_close()
            os.chdir(source)  # Windows cannot remove the process's working directory.
    report={'platform':args.platform,'default_offline_setup':True,'external_network_blocked':True,
            'existing_library_kept_until_explicit_import':True,'custom_repository_import':True,
            'custom_zip_import':True,'privacy_route_and_links':True,'data_files':40,
            'archive_sha256':hashlib.sha256(raw).hexdigest()}
    out.mkdir(parents=True,exist_ok=True)
    (out/'setup-check.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
