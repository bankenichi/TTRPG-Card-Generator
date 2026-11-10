"""Package reviewed SRD data, excluding development and upstream metadata.

Copies the data bytes unchanged. The only generated material is the small
distribution manifest and its README/license; no renderer is imported.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

README = """# Included SRD 5.2.1 library

The System Reference Document 5.2.1 (2024 rules), as structured JSON for
TTRPG Card Generator. This offline library contains 40 JSON files and 2,136
records, including 339 spells and 336 creature statblocks.

The manifest lists every data-file checksum and the official source PDF.
Source citations use SRD 5.2.1 page numbers. Six approved orientation settings
are stored in the data. Card rendering and splitting code are not included.

See ATTRIBUTION.md and DATA-LICENSE.md for attribution, licensing and changes.
"""
LICENSE = """# Rules data license

The SRD 5.2.1 text and rules are licensed under Creative Commons Attribution
4.0 International (CC BY 4.0):
https://creativecommons.org/licenses/by/4.0/legalcode

The required attribution is in ATTRIBUTION.md. The official source is:
https://www.dndbeyond.com/srd

Changes: the source is arranged as structured JSON, with SRD names and page
citations, compatible references, and six approved card orientation settings.
This is an independent app; Wizards of the Coast does not endorse it.
"""
MANIFEST_KEYS = ('srd', 'source_id', 'citation_model_sha256',
                 'layout_model_sha256', 'official_pdf', 'official_pdf_sha256',
                 'counts', 'sha256')


def package(source, destination):
    source=Path(source);destination=Path(destination)
    original=json.loads((source/'manifest.json').read_text('utf-8'))
    manifest={'format':'TTRPG Card Generator SRD data',
              **{key:original[key] for key in MANIFEST_KEYS}}
    files={name:(source/name).read_bytes() for name in manifest['sha256']}
    # Refuse to package changed rules or accidentally ship external references.
    for name,raw in files.items():
        if hashlib.sha256(raw).hexdigest()!=manifest['sha256'][name]:
            raise ValueError('Source data checksum mismatch: '+name)
    files.update({'manifest.json':(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode(),
                  'ATTRIBUTION.md':(source/'ATTRIBUTION.md').read_bytes(),
                  'DATA-LICENSE.md':LICENSE.encode(), 'README.md':README.encode()})
    for name,raw in files.items():
        if re.search(rb'5e[. _-]?tools',name.encode()+raw,re.I):
            raise ValueError('Unexpected distribution reference in '+name)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,raw in sorted(files.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,11,10,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644 << 16
            archive.writestr(info,raw,compresslevel=9)
    return hashlib.sha256(destination.read_bytes()).hexdigest()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    print(package(args.source,args.out))
