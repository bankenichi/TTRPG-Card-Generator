"""Bounded HTML previews; sheet order and card positions are never repacked."""
import json
from pathlib import Path
import re

BATCH_SHEETS = 20


def split_document(text):
    match = re.search(r'<body>(.*?)(?=<script>|</body>)', text, re.S | re.I)
    if not match:
        raise ValueError('Deck is missing printable sheet markup')
    sheets = [s for s in re.split(r'(?=<div class="page">)', match[1])
              if s.lstrip().startswith('<div class="page">')]
    return text[:match.start(1)], sheets, text[match.end(1):]


def write_batches(path, sheets_per_batch=BATCH_SHEETS, platform='desktop'):
    """Package immutable rendered sheets behind a bounded continuous viewer.

    Keep the old call signature for controllers. The manifest, rather than the
    viewer document, supplies source sheets to PDF export.
    """
    from workbench_ui import render_viewer
    path = Path(path)
    text = path.read_text(encoding='utf-8')
    head, sheets, tail = split_document(text)
    paths = [path.with_name(f'{path.stem}_sheet_{i+1:04d}.html') for i in range(len(sheets))]
    for output, sheet in zip(paths, sheets):
        output.write_text(head + sheet + tail, encoding='utf-8')
    manifest = {'files': [p.name for p in paths], 'sheet_count': len(sheets),
                'kind': 'Backs' if path.stem.endswith('Backs') else 'Cards', 'platform': platform}
    path.with_suffix('.manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    path.write_text(render_viewer(manifest), encoding='utf-8')
    return manifest
