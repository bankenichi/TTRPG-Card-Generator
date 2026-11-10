"""Install a pinned SRD data-only release without enriching or changing its data.

This module does no work on import and never replaces data until the downloaded
archive and every manifest-listed data file have passed verification.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
import urllib.request
from urllib.parse import urlsplit
import zipfile

from data_install import safe_extract, dataset_from_extraction, validate_dataset, replace_tree
from data_paths import is_within

SRD_VERSION='5.2.1'
SOURCE_ID='SRD521'
SRD_RELEASE_URL='https://github.com/bankenichi/5etools-srd/releases/download/srd-5.2.1-r1/srd-5.2.1.zip'
SRD_RELEASE_SHA256='a682b2a223d23afce40678c5821fea5dbe8ed05777c8134fb2c79a27c8a029e6'
OFFICIAL_PDF_SHA256='8974902d109d6e63672d7c490bde9ccf052410503d9cfa768237154fbc5e3d87'
REQUIRED_DOCUMENTS={'ATTRIBUTION.md','DATA-LICENSE.md'}
OPTIONAL_DOCUMENTS={'README.md'}
MAX_ARCHIVE_BYTES=128*1024*1024
MAX_EXPANDED_BYTES=512*1024*1024


class _HttpsRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,msg,headers,newurl):
        if urlsplit(newurl).scheme!='https':
            if fp is not None:fp.close()
            raise ValueError('SRD download redirect must use HTTPS')
        return super().redirect_request(request,fp,code,msg,headers,newurl)


def _sha256(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as source:
        while block:=source.read(1024*1024):digest.update(block)
    return digest.hexdigest()


def _expected_digest(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9a-f]{64}',value):
        raise ValueError('SRD release requires a pinned SHA-256 digest')
    return value


def validate_srd_manifest(root):
    """Check package integrity; the external archive digest supplies provenance."""
    root=Path(root).resolve()
    manifest_path=root/'manifest.json'
    if not manifest_path.is_file():raise ValueError('SRD release is missing its manifest')
    manifest=json.loads(manifest_path.read_text(encoding='utf8'))
    if manifest.get('srd')!=SRD_VERSION or manifest.get('source_id')!=SOURCE_ID or manifest.get('official_pdf_sha256')!=OFFICIAL_PDF_SHA256:
        raise ValueError('Archive is not the expected SRD 5.2.1 release')
    if manifest.get('provisional_probe'):raise ValueError('A provisional SRD projection cannot be installed as the verified release')
    inventory=manifest.get('sha256')
    if not isinstance(inventory,dict) or not inventory:raise ValueError('SRD release has no data file inventory')
    for name,digest in inventory.items():
        if not isinstance(name,str):raise ValueError('SRD manifest contains an unsafe data path')
        path=PurePosixPath(name)
        if path.is_absolute() or path.as_posix()!=name or '..' in path.parts or '\\' in name or ':' in name or len(path.parts)<2 or path.parts[0]!='data' or path.suffix!='.json':
            raise ValueError('SRD manifest contains an unsafe data path')
        _expected_digest(digest)
    files={path.relative_to(root).as_posix() for path in root.rglob('*') if path.is_file()}
    if (files & REQUIRED_DOCUMENTS)!=REQUIRED_DOCUMENTS:raise ValueError('SRD release is missing attribution or data license')
    expected=set(inventory)|{'manifest.json'}|REQUIRED_DOCUMENTS
    if files-expected-OPTIONAL_DOCUMENTS or expected-files:
        raise ValueError('SRD archive files differ from its data-only manifest')
    for name,digest in inventory.items():
        path=root/name
        if not is_within(path,root) or _sha256(path)!=digest:raise ValueError('SRD data file checksum failed: '+name)
    validate_dataset(root)
    return manifest


def install_verified_srd_archive(archive_path,destination,expected_sha256,progress=None):
    """Install only the exact reviewed archive, with rollback on replacement failure."""
    expected_sha256=_expected_digest(expected_sha256)
    archive_path=Path(archive_path);destination=Path(destination).resolve()
    if archive_path.stat().st_size>MAX_ARCHIVE_BYTES:raise ValueError('SRD archive exceeds the release size limit')
    if _sha256(archive_path)!=expected_sha256:raise ValueError('SRD archive checksum failed; existing data was kept')
    parent=destination.parent;parent.mkdir(parents=True,exist_ok=True)
    if progress:progress('Checking the SRD release…')
    with tempfile.TemporaryDirectory(prefix='.srd-install-',dir=parent) as folder:
        if not is_within(folder,parent):raise ValueError('SRD staging directory escapes its install parent')
        extracted=Path(folder)/'repository'
        with zipfile.ZipFile(archive_path) as archive:
            names=[]
            for entry in archive.infolist():
                name=entry.filename.rstrip('/') if entry.is_dir() else entry.filename
                if not name or PurePosixPath(name).as_posix()!=name or '..' in PurePosixPath(name).parts:
                    raise ValueError('SRD archive contains a noncanonical path')
                names.append(name.casefold())
            if len(names)!=len(set(names)):raise ValueError('SRD archive contains duplicate paths')
            if sum(entry.file_size for entry in archive.infolist())>MAX_EXPANDED_BYTES:raise ValueError('Expanded SRD release exceeds the size limit')
            safe_extract(archive,extracted)
        staged=dataset_from_extraction(extracted)
        if any(path.is_file() and not is_within(path,staged) for path in extracted.rglob('*')):
            raise ValueError('SRD archive contains files outside its data-only package')
        manifest=validate_srd_manifest(staged)
        if progress:progress('Installing the verified SRD release…')
        replace_tree(staged,destination)
    return {'srd':SRD_VERSION,'source_id':SOURCE_ID,'archive_sha256':expected_sha256,'data_files':len(manifest['sha256'])}


def download_verified_srd(url,expected_sha256,destination,progress=None):
    """Stream a pinned HTTPS release to staging, then verify and install it."""
    expected_sha256=_expected_digest(expected_sha256)
    if not isinstance(url,str) or urlsplit(url).scheme!='https':raise ValueError('SRD release URL must use HTTPS')
    parent=Path(destination).resolve().parent;parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.srd-download-',dir=parent) as folder:
        if not is_within(folder,parent):raise ValueError('SRD download directory escapes its install parent')
        archive=Path(folder)/'release.zip'
        if progress:progress('Downloading SRD 5.2.1…')
        request=urllib.request.Request(url,headers={'User-Agent':'TTRPG-Card-Generator'})
        opener=urllib.request.build_opener(_HttpsRedirectHandler())
        with opener.open(request,timeout=60) as response,archive.open('wb') as output:
            size=0
            while block:=response.read(65536):
                size+=len(block)
                if size>MAX_ARCHIVE_BYTES:raise ValueError('SRD archive exceeds the release size limit')
                output.write(block)
        return install_verified_srd_archive(archive,destination,expected_sha256,progress)
