"""Independent PDF raster comparison against saved Chromium sheet captures.

Development-only dependencies: Pillow and PyMuPDF (the app does not need PyMuPDF).
Example: python verify_print_export.py deck.pdf rendered-sheets --report result.json
"""
import argparse
import hashlib
import json
from pathlib import Path
import time


def verify(pdf_path, reference_directory, report_path):
    import fitz
    from PIL import Image, ImageChops
    start = time.monotonic()
    pdf_path, reference_directory = Path(pdf_path), Path(reference_directory)
    records = []
    with fitz.open(pdf_path) as document:
        for index, page in enumerate(document):
            source = reference_directory / f'sheet-{index+1:04d}.png'
            if tuple(page.mediabox) != (0.0, 0.0, 612.0, 792.0):
                raise ValueError(f'Sheet {index+1} is not Letter paper')
            pixmap = page.get_pixmap(dpi=300, colorspace=fitz.csRGB, alpha=False)
            actual = Image.frombytes('RGB', (pixmap.width, pixmap.height), pixmap.samples)
            with Image.open(source) as original:
                expected = original.convert('RGB')
            if actual.size != expected.size or actual.size != (2550, 3300):
                raise ValueError(f'Sheet {index+1} raster dimensions changed')
            difference = ImageChops.difference(actual, expected)
            bbox = difference.getbbox()
            records.append({'sheet': index+1, 'pixel_identical': bbox is None,
                            'maximum_channel_error': max(extrema[1] for extrema in difference.getextrema()),
                            'difference_bounds': bbox, 'rgb_sha256': hashlib.sha256(actual.tobytes()).hexdigest()})
            actual.close(); expected.close(); difference.close()
            if (index+1) % 25 == 0:
                print(f'Compared {index+1}/{len(document)} PDF sheets', flush=True)
    digest = hashlib.sha256()
    with pdf_path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): digest.update(block)
    report = {'pdf': str(pdf_path.resolve()), 'pdf_sha256': digest.hexdigest(),
              'bytes': pdf_path.stat().st_size, 'dpi':300, 'sheet_count':len(records),
              'all_pixel_identical': all(record['pixel_identical'] for record in records),
              'maximum_channel_error':max((record['maximum_channel_error'] for record in records), default=0),
              'seconds':round(time.monotonic()-start,2), 'sheets':records}
    Path(report_path).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print({key:value for key,value in report.items() if key != 'sheets'}, flush=True)
    if not report['all_pixel_identical']: raise ValueError('PDF pixels differ from rendered HTML sheets')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf'); parser.add_argument('reference_directory')
    parser.add_argument('--report', default='pixel-verification.json')
    args = parser.parse_args()
    verify(args.pdf, args.reference_directory, args.report)
