import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
import json

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject


def text_pdf(path, text):
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject('/Type'):NameObject('/Font'), NameObject('/Subtype'):NameObject('/Type1'), NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(f'BT /F1 12 Tf 48 720 Td ({text}) Tj ET'.encode('ascii'))
    page[NameObject('/Contents')] = writer._add_object(stream)
    writer.write(path)


class CompactPdfTest(unittest.TestCase):
    def test_native_mask_rendering_rejects_multi_sheet_jobs(self):
        from pdf_export import _render_batch
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp,'deck.html')
            source.write_text('<html><body><div class="page">one</div><div class="page">two</div><script></script></body></html>',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'one sheet per job'):
                _render_batch({'document':str(source),'pdf':str(Path(temp,'deck.pdf')),'first_sheet':1})

    def test_overflow_checks_visible_content_instead_of_empty_margins(self):
        from playwright.sync_api import sync_playwright
        from pdf_layout import CHECK_OVERFLOW
        with sync_playwright() as driver:
            browser = driver.chromium.launch(channel='chromium', headless=True)
            try:
                page = browser.new_page()
                page.set_content('''<div class="card"><div class="title">Test</div>
                    <div class="content-wrapper" style="height:40px;width:200px;overflow:hidden;position:relative">
                    <div class="content-inner"><p style="margin:0 0 100px">Visible rules.</p></div></div></div>''')
                self.assertEqual(page.evaluate(CHECK_OVERFLOW), [])
                page.locator('p').evaluate("e=>e.style.paddingTop='100px'")
                self.assertEqual(page.evaluate(CHECK_OVERFLOW), ['Test'])
                from card_engine import parse_entry_to_html
                for entry_type in ('bulleted_string', 'bulleted_header', 'indented_string'):
                    entry = {'type': entry_type, 'entry': 'Long text ' * 25, 'name': 'Long header ' * 25}
                    page.locator('.content-inner').evaluate('(e,html)=>e.innerHTML=html', parse_entry_to_html(entry))
                    self.assertEqual(page.evaluate(CHECK_OVERFLOW), ['Test'], entry_type)
            finally:
                browser.close()

    def test_visual_check_rejects_colored_boxes_without_text_changes(self):
        from PIL import Image, ImageDraw
        from verify_pdf_visuals import compare_sheet
        expected = Image.new('RGB', (300, 400), '#dfc882')
        self.assertTrue(compare_sheet(expected, expected)['artifact_check_passed'])
        actual = expected.copy()
        ImageDraw.Draw(actual).rectangle((40, 70, 260, 330), fill='#a6a58d')
        result = compare_sheet(expected, actual)
        self.assertFalse(result['artifact_check_passed'])
        self.assertGreater(result['unexpected_background_pixels'], 50000)

    def test_visual_check_rejects_covered_text_even_with_edge_exclusion(self):
        from PIL import Image, ImageDraw, ImageFont
        from verify_pdf_visuals import compare_sheet
        expected = Image.new('RGB', (300, 100), 'white')
        font = ImageFont.truetype(str(Path(__file__).with_name('fonts')/'OpenSans-normal-400.ttf'), 14)
        ImageDraw.Draw(expected).text((20, 30), 'Visible text must remain', fill='black', font=font)
        covered = Image.new('RGB', expected.size, 'white')
        result = compare_sheet(expected, covered)
        self.assertFalse(result['artifact_check_passed'])
        self.assertGreater(result['unexpected_contrast_tiles'], 2)

    def test_original_load_callback_refits_with_bundled_fonts(self):
        from card_engine import generate_html
        from pdf_export import _render_batch
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root/'fixture.json'; document = root/'deck.html'
            source.write_text(json.dumps({'item': [{'name': 'Focus', 'entries': ['Original rules.']}]}), encoding='utf-8')
            generate_html({'datasets': [{'file': str(source)}]}, str(document))
            html = document.read_text(encoding='utf-8')
            html = html.replace('</body>', '''<script>
                const originalFit=window.onload;let calls=0;
                window.onload=()=>{originalFit();document.querySelector('.title > span').textContent='Fitted '+(++calls);};
                </script></body>''')
            document.write_text(html, encoding='utf-8')
            output = root/'deck.pdf'
            _render_batch({'document': str(document), 'pdf': str(output), 'first_sheet': 1})
            reader = PdfReader(output)
            self.assertIn('FITTED 2', reader.pages[0].extract_text())
            fonts = reader.pages[0]['/Resources']['/Font'].values()
            self.assertTrue(any('OpenSans' in str(font.get_object().get('/BaseFont')) for font in fonts))

    def test_stalled_worker_is_stopped_and_retains_evidence(self):
        from pdf_export import render_pdf
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'deck.html'
            source.write_text('<html><body><div class="page">sheet</div><script></script></body></html>',encoding='utf-8')
            process=Mock(poll=Mock(return_value=None),wait=Mock(return_value=0))
            with patch('pdf_export._launch_batch',return_value=process),patch('pdf_export.time.monotonic',side_effect=[0,0,600]),self.assertRaises(TimeoutError):
                render_pdf([source],root/'deck.pdf',batch_timeout_seconds=300)
            process.terminate.assert_called_once();process.wait.assert_called_once_with(timeout=10)
            self.assertEqual(len(list(root.glob('.render-*'))),1)

    def test_out_of_order_batch_completion_keeps_sheet_order(self):
        from pdf_export import render_pdf,_verify_page
        from pdf_layout import text_signature
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'deck.html'
            source.write_text('<html><body>'+''.join('<div class="page">sheet</div>' for _ in range(6))+'<script></script></body></html>',encoding='utf-8')
            def launch(path):
                job=json.loads(path.read_text(encoding='utf-8'));writer=PdfWriter();records=[]
                count=Path(job['document']).read_text(encoding='utf-8').count('<div class="page">')
                self.assertEqual(count,1)
                for sheet in range(job['first_sheet'],job['first_sheet']+count):
                    single=root/f'sheet-{sheet}.pdf';text_pdf(single,f'Sheet {sheet}')
                    page=PdfReader(single).pages[0];record={'sheet':sheet,'text_signature':text_signature(f'Sheet {sheet}')}
                    _verify_page(page,record);records.append(record);writer.add_page(page)
                writer.write(job['pdf'])
                Path(job['result']).write_text(json.dumps({'state':'complete','chromium':'test','sheets':records}),encoding='utf-8')
                return Mock(poll=Mock(side_effect=[None,0,0] if job['first_sheet']==1 else [0,0]),wait=Mock(return_value=0))
            with patch('pdf_export._launch_batch',side_effect=launch):
                result=render_pdf([source],root/'deck.pdf',max_workers=2)
            self.assertEqual(result['total_sheets'],6)
            self.assertNotIn('batch_downloads',result)
            self.assertFalse(list(root.glob('deck_sheets_*.pdf')))
            self.assertEqual([p.extract_text() for p in PdfReader(root/'deck.pdf').pages],[f'Sheet {n}' for n in range(1,7)])
            self.assertFalse(list(root.glob('.render-*')))

    def test_failed_worker_preserves_job_evidence(self):
        from pdf_export import render_pdf
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'deck.html'
            source.write_text('<html><body><div class="page">sheet</div><script></script></body></html>',encoding='utf-8')
            def fail(path):
                job=json.loads(path.read_text(encoding='utf-8'))
                Path(job['result']).write_text(json.dumps({'state':'failed','error':'Missing source glyph'}),encoding='utf-8')
                return Mock(poll=Mock(return_value=1),wait=Mock(return_value=1))
            with patch('pdf_export._launch_batch',side_effect=fail),self.assertRaisesRegex(ValueError,'Missing source glyph'):
                render_pdf([source],root/'deck.pdf')
            work=list(root.glob('.render-*'));self.assertEqual(len(work),1)
            self.assertTrue(list(work[0].glob('*.html')))
            self.assertFalse((root/'deck.pdf').exists())

    def test_content_signature_retains_math_and_dice_symbols(self):
        from pdf_layout import text_signature
        self.assertNotEqual(text_signature('1d4 + 2'),text_signature('1d4 - 2'))
        self.assertNotEqual(text_signature('Speed ≤ 30'),text_signature('Speed ≥ 30'))

    def test_drawing_hash_is_nonempty_and_rejects_drawing_only_edits(self):
        from pdf_export import _content_hash, _verify_page
        from pdf_layout import text_signature
        import hashlib
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp,'text.pdf');text_pdf(path,'Same text')
            page=PdfReader(path).pages[0]
            record={'sheet':1,'text_signature':text_signature('Same text')}
            _verify_page(page,record)
            self.assertNotEqual(_content_hash(page),hashlib.sha256(b'').hexdigest())
            stream=DecodedStreamObject()
            stream.set_data(page.get_contents().get_data()+b'\n0 0 20 20 re f')
            page[NameObject('/Contents')]=stream
            self.assertEqual(page.extract_text(),'Same text')
            with self.assertRaises(ValueError):_verify_page(page,record)

    def test_merge_preserves_vector_text_and_sheet_order(self):
        from pdf_export import _merge_parts
        with tempfile.TemporaryDirectory() as temp:
            paths=[Path(temp,f'{i}.pdf') for i in range(2)]
            for path,text in zip(paths,['First sheet','Second sheet']): text_pdf(path,text)
            result=Path(temp,'merged.pdf')
            self.assertEqual(_merge_parts(paths,result),2)
            reader=PdfReader(result)
            self.assertEqual([page.extract_text() for page in reader.pages],['First sheet','Second sheet'])
            self.assertTrue(all(tuple(page.mediabox)==(0,0,612,792) for page in reader.pages))

    def test_compaction_merges_nested_repeated_image_resources(self):
        from pdf_export import compact_pdf
        from pypdf.generic import EncodedStreamObject, NumberObject
        import zlib
        writer=PdfWriter()
        for _ in range(3):
            page=writer.add_blank_page(width=612,height=792)
            mask=EncodedStreamObject(); mask._data=zlib.compress(b'\xff'*400)
            mask.update({NameObject('/Type'):NameObject('/XObject'),NameObject('/Subtype'):NameObject('/Image'),NameObject('/Width'):NumberObject(20),NameObject('/Height'):NumberObject(20),NameObject('/ColorSpace'):NameObject('/DeviceGray'),NameObject('/BitsPerComponent'):NumberObject(8),NameObject('/Filter'):NameObject('/FlateDecode')})
            image=EncodedStreamObject(); image._data=zlib.compress(bytes(range(200))*6)
            image.update({NameObject('/Type'):NameObject('/XObject'),NameObject('/Subtype'):NameObject('/Image'),NameObject('/Width'):NumberObject(20),NameObject('/Height'):NumberObject(20),NameObject('/ColorSpace'):NameObject('/DeviceRGB'),NameObject('/BitsPerComponent'):NumberObject(8),NameObject('/Filter'):NameObject('/FlateDecode'),NameObject('/SMask'):writer._add_object(mask)})
            page[NameObject('/Resources')]=DictionaryObject({NameObject('/XObject'):DictionaryObject({NameObject('/Texture'):writer._add_object(image)})})
        compact_pdf(writer)
        refs=[page['/Resources']['/XObject'].raw_get('/Texture').idnum for page in writer.pages]
        self.assertEqual(len(set(refs)),1)


if __name__=='__main__':unittest.main()
