"""Compare every final PDF sheet with the original browser screenshot.

PDF and browser text antialiasing differ. Check the quiet regions away from
sharp edges for unexpected paint; the separate glyph verifier checks text and
positions. A separate contrast check also catches covered or missing text paint.
This catches solid mask rectangles that text checks cannot detect.
Development-only dependency: PyMuPDF.
"""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageMorph, ImageOps, ImageStat


def compare_sheet(expected, actual):
    if expected.size != actual.size:
        raise ValueError('PDF raster dimensions differ from the rendered sheet')
    difference = ImageChops.difference(expected, actual)
    channels = difference.split()
    maximum = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
    edges = expected.filter(ImageFilter.FIND_EDGES).split()
    edges = ImageChops.lighter(ImageChops.lighter(edges[0], edges[1]), edges[2])
    edges = edges.point(lambda value: 255 if value > 30 else 0)
    size = edges.size
    edges = ImageOps.expand(edges, border=3, fill=0)
    dilation = ImageMorph.MorphOp(op_name='dilation8')
    for _ in range(3):
        _, edges = dilation.apply(edges)
    edges = edges.crop((3, 3, size[0]+3, size[1]+3))
    stable = ImageChops.invert(edges)
    unexpected = ImageChops.multiply(maximum.point(lambda value: 255 if value > 16 else 0), stable)
    pixels = unexpected.histogram()[255]
    # Up to 0.001% isolated pixels permits rasterizer rounding near complex
    # glyphs; large flat paint regions are never covered by the edge exclusion.
    allowance = int(expected.width * expected.height * 0.00001)
    # Compare integrated ink over small tiles as well. Antialiasing differences
    # average out; a white overlay covering extracted text does not.
    tile_size = (max(1, expected.width//8), max(1, expected.height//8))
    contrast = ImageChops.difference(expected.resize(tile_size, Image.Resampling.BOX),
                                   actual.resize(tile_size, Image.Resampling.BOX)).split()
    contrast = ImageChops.lighter(ImageChops.lighter(contrast[0], contrast[1]), contrast[2])
    contrast_tiles = contrast.point(lambda value: 255 if value > 48 else 0).histogram()[255]
    return {'unexpected_background_pixels': pixels, 'allowed_pixels': allowance,
            'unexpected_bounds': unexpected.getbbox(), 'unexpected_contrast_tiles': contrast_tiles,
            'artifact_check_passed': pixels <= allowance and contrast_tiles <= 2,
            'mean_channel_error': round(sum(ImageStat.Stat(difference).mean) / 3, 5)}


def verify(pdf_path, reference_directory, report_path, renderer='mupdf', first_sheet=1, last_sheet=None):
    if renderer == 'pdfium':
        import pypdfium2
        open_pdf = pypdfium2.PdfDocument
    else:
        import fitz
        open_pdf = fitz.open
    pdf_path, reference_directory = Path(pdf_path), Path(reference_directory)
    records = []
    with open_pdf(pdf_path) as document:
        if len(list(reference_directory.glob('sheet-*.png'))) != len(document):
            raise ValueError('Every final PDF sheet needs an original screenshot')
        end = len(document) if last_sheet is None else last_sheet
        if not 1 <= first_sheet <= end <= len(document):
            raise ValueError('Invalid sheet range')
        for index in range(first_sheet-1, end):
            page = document[index]
            if renderer == 'pdfium':
                if tuple(page.get_size()) != (612, 792):
                    raise ValueError('PDF paper dimensions changed')
                # Avoid PDFium rounding an exact page edge up by one pixel.
                bitmap = page.render(scale=300/72-1e-9)
                actual = bitmap.to_pil().convert('RGB')
                bitmap.close(); page.close()
            else:
                if tuple(page.rect) != (0, 0, 612, 792):
                    raise ValueError('PDF paper dimensions changed')
                pixmap = page.get_pixmap(dpi=300, colorspace=fitz.csRGB, alpha=False)
                actual = Image.frombytes('RGB', (pixmap.width, pixmap.height), pixmap.samples)
            with Image.open(reference_directory / f'sheet-{index+1:04d}.png') as original:
                expected = original.convert('RGB')
            if actual.size != (2550, 3300):
                raise ValueError('PDF raster is not Letter at 300 DPI')
            record = {'sheet': index+1, **compare_sheet(expected, actual)}
            records.append(record)
            if not record['artifact_check_passed']:
                difference = ImageChops.difference(expected, actual)
                difference.save(Path(report_path).with_name(f'visual-difference-{index+1:04d}.png'))
            expected.close(); actual.close()
            if (index+1) % 25 == 0:
                print(f'Compared graphics on {index+1}/{len(document)} sheets', flush=True)
    report = {'pdf': str(pdf_path.resolve()), 'pdf_sha256': hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
              'renderer': renderer, 'dpi': 300, 'sheets': len(records), 'all_artifact_checks_passed': all(r['artifact_check_passed'] for r in records),
              'first_sheet': first_sheet, 'last_sheet': end,
              'pixel_identical': False, 'edge_exclusion_radius_px': 3, 'channel_difference_threshold': 16,
              'contrast_tile_size_px': 8, 'contrast_channel_threshold': 48, 'allowed_contrast_tiles': 2,
              'maximum_unexpected_background_pixels': max(r['unexpected_background_pixels'] for r in records),
              'results': records}
    Path(report_path).write_text(json.dumps(report, indent=2), encoding='utf-8')
    print({k: v for k, v in report.items() if k != 'results'}, flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf'); parser.add_argument('references'); parser.add_argument('--report', required=True)
    parser.add_argument('--renderer', choices=('mupdf', 'pdfium'), default='mupdf')
    parser.add_argument('--first-sheet', type=int, default=1); parser.add_argument('--last-sheet', type=int)
    args = parser.parse_args()
    result = verify(args.pdf, args.references, args.report, args.renderer, args.first_sheet, args.last_sheet)
    raise SystemExit(0 if result['all_artifact_checks_passed'] else 1)
