"""Installer integrity/rollback fixtures, not source-fidelity certification."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import re
import subprocess
import sys
import unittest
from unittest.mock import patch,Mock
import urllib.request
from urllib.response import addinfourl
from email.message import Message
import zipfile

import verified_srd as srd


def fixture():
    files={'data/class/index.json':b'{}\n','data/spells/index.json':b'{}\n',
           'ATTRIBUTION.md':b'Installer test fixture attribution.\n','DATA-LICENSE.md':b'Installer test fixture license.\n'}
    manifest={'srd':srd.SRD_VERSION,'source_id':srd.SOURCE_ID,'official_pdf_sha256':srd.OFFICIAL_PDF_SHA256,
              'note':'Synthetic installer fixture only; not published SRD data.',
              'sha256':{name:hashlib.sha256(raw).hexdigest() for name,raw in files.items() if name.startswith('data/')}}
    files['manifest.json']=json.dumps(manifest).encode()
    return files


def archive_bytes(files,prefix=''):
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,raw in files.items():archive.writestr(prefix+name,raw)
    return output.getvalue()


class VerifiedSrdInstallTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.destination=self.root/'generators/data'

    def install(self,files,prefix='',digest=None):
        raw=archive_bytes(files,prefix);path=self.root/'fixture.zip';path.write_bytes(raw)
        return srd.install_verified_srd_archive(path,self.destination,digest or hashlib.sha256(raw).hexdigest())

    def old_data(self):
        self.destination.mkdir(parents=True,exist_ok=True)
        (self.destination/'existing-custom.txt').write_bytes(b'Existing full/custom catalog must survive a failed import.\n')

    def assert_old_data_kept(self):
        self.assertEqual((self.destination/'existing-custom.txt').read_bytes(),b'Existing full/custom catalog must survive a failed import.\n')
        self.assertEqual(list(self.destination.iterdir()),[self.destination/'existing-custom.txt'])
        self.assertFalse(list(self.destination.parent.glob('.srd-*')))

    def test_fresh_and_single_wrapper_install_preserve_exact_bytes(self):
        for prefix in ('','srd-5.2.1/'):
            with self.subTest(prefix=prefix):
                files=fixture();result=self.install(files,prefix)
                self.assertEqual(result['source_id'],'SRD521');self.assertEqual(result['data_files'],2)
                for name,raw in files.items():self.assertEqual((self.destination/name).read_bytes(),raw)
                self.assertFalse(list(self.destination.parent.glob('.srd-*')))

    def test_successful_explicit_install_replaces_only_the_requested_tree(self):
        self.old_data();other=self.root/'generators/my-other-catalog';other.mkdir()
        (other/'keep.txt').write_bytes(b'Keep this separate custom choice.')
        self.install(fixture())
        self.assertFalse((self.destination/'existing-custom.txt').exists())
        self.assertEqual((other/'keep.txt').read_bytes(),b'Keep this separate custom choice.')

    def test_bad_archive_digest_keeps_existing_data(self):
        self.old_data()
        with self.assertRaisesRegex(ValueError,'archive checksum'):self.install(fixture(),digest='0'*64)
        self.assert_old_data_kept()

    def test_bad_file_hash_extra_payload_or_incomplete_license_keeps_existing_data(self):
        self.old_data()
        for action in ('file-hash','extra-json','extra-code','missing-license','invalid-json','wrong-srd','probe'):
            with self.subTest(action=action):
                files=fixture();manifest=json.loads(files['manifest.json'])
                if action=='file-hash':files['data/spells/index.json']=b'{"changed":true}'
                elif action=='extra-json':files['data/non-srd.json']=b'{}'
                elif action=='extra-code':files['tools/unexpected.py']=b'print("not a data-only release")'
                elif action=='missing-license':del files['DATA-LICENSE.md']
                elif action=='invalid-json':
                    files['data/spells/index.json']=b'not JSON';manifest['sha256']['data/spells/index.json']=hashlib.sha256(b'not JSON').hexdigest()
                elif action=='wrong-srd':manifest['srd']='5.1'
                else:manifest['provisional_probe']=True
                files['manifest.json']=json.dumps(manifest).encode()
                with self.assertRaises(ValueError):self.install(files)
                self.assert_old_data_kept()

    def test_unsafe_and_case_aliased_zip_paths_are_rejected(self):
        self.old_data()
        for name in ('../outside.txt','data/../manifest.json','data\\outside.txt','DATA/class/index.json'):
            with self.subTest(name=name):
                files=fixture();files[name]=b'{}'
                with self.assertRaises(ValueError):self.install(files)
                self.assert_old_data_kept();self.assertFalse((self.root/'outside.txt').exists())

    def test_outer_wrapper_siblings_are_rejected(self):
        self.old_data()
        for name in ('tools/unexpected.py','.git/config'):
            with self.subTest(name=name):
                files={'srd-5.2.1/'+name:raw for name,raw in fixture().items()}
                files[name]=b'Unexpected outer payload.'
                with self.assertRaisesRegex(ValueError,'outside its data-only package'):self.install(files)
                self.assert_old_data_kept()

    def test_pinned_stream_download_and_interruption(self):
        raw=archive_bytes(fixture());digest=hashlib.sha256(raw).hexdigest()
        opener=Mock();opener.open.return_value=io.BytesIO(raw)
        with patch.object(srd.urllib.request,'build_opener',return_value=opener):
            result=srd.download_verified_srd('https://example.test/srd.zip',digest,self.destination)
        self.assertEqual(result['archive_sha256'],digest)
        self.assertEqual(opener.open.call_args.args[0].full_url,'https://example.test/srd.zip')
        snapshot={p.relative_to(self.destination):p.read_bytes() for p in self.destination.rglob('*') if p.is_file()}
        opener.open.side_effect=OSError('Download interrupted')
        with patch.object(srd.urllib.request,'build_opener',return_value=opener):
            with self.assertRaises(OSError):srd.download_verified_srd('https://example.test/srd.zip',digest,self.destination)
        self.assertEqual(snapshot,{p.relative_to(self.destination):p.read_bytes() for p in self.destination.rglob('*') if p.is_file()})
        self.assertFalse(list(self.destination.parent.glob('.srd-*')))

    def test_https_redirects_work_and_http_downgrades_are_blocked_before_fetch(self):
        raw=archive_bytes(fixture());digest=hashlib.sha256(raw).hexdigest();build=urllib.request.build_opener
        class Transport(urllib.request.BaseHandler):
            handler_order=100
            def __init__(self,target):self.target=target;self.https_requests=[];self.http_requests=[]
            def https_open(self,request):
                self.https_requests.append(request.full_url);headers=Message()
                redirect=request.full_url=='https://example.test/start'
                if redirect:headers['Location']=self.target
                response=addinfourl(io.BytesIO(b'' if redirect else raw),headers,request.full_url,302 if redirect else 200)
                response.msg='Found' if redirect else 'OK'
                return response
            def http_open(self,request):
                self.http_requests.append(request.full_url)
                raise AssertionError('An insecure HTTP request must not be issued')
        for target in ('https://cdn.example.test/srd.zip','http://cdn.example.test/srd.zip'):
            with self.subTest(target=target):
                transport=Transport(target)
                with patch.object(srd.urllib.request,'build_opener',side_effect=lambda *handlers:build(urllib.request.ProxyHandler({}),*handlers,transport)):
                    if target.startswith('https:'):
                        srd.download_verified_srd('https://example.test/start',digest,self.destination)
                        self.assertEqual(transport.https_requests,['https://example.test/start',target])
                    else:
                        snapshot={p.relative_to(self.destination):p.read_bytes() for p in self.destination.rglob('*') if p.is_file()}
                        with self.assertRaisesRegex(ValueError,'redirect must use HTTPS'):
                            srd.download_verified_srd('https://example.test/start',digest,self.destination)
                        self.assertEqual(snapshot,{p.relative_to(self.destination):p.read_bytes() for p in self.destination.rglob('*') if p.is_file()})
                self.assertFalse(transport.http_requests)

    def test_replacement_failure_keeps_existing_tree(self):
        self.old_data()
        with patch.object(srd,'replace_tree',side_effect=OSError('Directory is in use')):
            with self.assertRaises(OSError):self.install(fixture())
        self.assert_old_data_kept()

    def test_missing_pin_and_insecure_url_fail_before_fetch(self):
        with patch.object(srd.urllib.request,'build_opener') as fetch:
            for url,digest in [('https://example.test/srd.zip',''),('http://example.test/srd.zip','a'*64)]:
                with self.assertRaises(ValueError):srd.download_verified_srd(url,digest,self.destination)
            fetch.assert_not_called()


    def test_real_bundle_installs_offline_and_contains_only_clean_data(self):
        with patch.object(srd.urllib.request,'urlopen',side_effect=AssertionError('Offline install used network')), \
             patch.object(srd.urllib.request,'build_opener',side_effect=AssertionError('Offline install used network')):
            result=srd.install_bundled_srd(self.destination)
        self.assertEqual(result['data_files'],40)
        manifest=srd.validate_srd_manifest(self.destination)
        self.assertFalse({'upstream','upstream_commit','selection_receipts','content_corrections'} & manifest.keys())
        for path in self.destination.rglob('*'):
            if path.is_file():
                raw=path.read_text('utf-8')
                decoded=json.dumps(json.loads(raw),ensure_ascii=False) if path.suffix=='.json' else raw
                self.assertIsNone(re.search(r'5e[. _-]?tools',path.name+decoded,re.I),str(path))

    def test_resource_can_install_from_a_zipped_python_package(self):
        package=self.root/'python-package.zip'
        source=Path(srd.__file__).parent
        with zipfile.ZipFile(package,'w') as archive:
            for path in (source/'bundled_srd').glob('*'):
                if path.is_file():archive.write(path,'bundled_srd/'+path.name)
        script="""import sys
sys.path[:0]=[sys.argv[1],sys.argv[2]]
import verified_srd
result=verified_srd.install_bundled_srd(sys.argv[3])
assert result['data_files']==40
"""
        subprocess.run([sys.executable,'-s','-c',script,str(package),str(source),str(self.destination)],check=True,capture_output=True)


if __name__=='__main__':unittest.main()
