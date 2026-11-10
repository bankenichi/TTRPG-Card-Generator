import functools
import hashlib
import http.client
from http.server import HTTPServer
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch, Mock

from deck_output import split_document, write_batches
from local_http import LocalRequestHandler
from pdf_export import _verify_page, _merge_parts, write_pdf_batches


class HttpBoundaryTest(unittest.TestCase):
    def request(self, path, headers=None):
        with tempfile.TemporaryDirectory() as temp:
            Path(temp, 'Custom_Deck_Test.html').write_text('allowed', encoding='utf-8')
            Path(temp, 'private.txt').write_text('private', encoding='utf-8')
            server = HTTPServer(('127.0.0.1', 0), functools.partial(LocalRequestHandler, directory=temp))
            worker = threading.Thread(target=server.handle_request); worker.start()
            connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
            try:
                connection.request('GET', path, headers=headers or {})
                response = connection.getresponse(); result = response.status, response.read()
            finally:
                connection.close(); worker.join(timeout=5); server.server_close()
            return result

    def test_allowed_output_is_served(self):
        self.assertEqual(self.request('/Custom_Deck_Test.html'), (200, b'allowed'))

    def test_private_files_and_traversal_are_blocked(self):
        for path in ('/private.txt', '/.git/config', '/generators/data/../../../private.txt', '/generators/data/%2e%2e/%2e%2e/private.txt'):
            with self.subTest(path=path): self.assertEqual(self.request(path)[0], 404)

    def test_foreign_host_origin_and_navigation_are_blocked(self):
        for headers in ({'Host':'attacker.example'}, {'Origin':'https://attacker.example'}, {'Sec-Fetch-Site':'cross-site'}):
            with self.subTest(headers=headers): self.assertEqual(self.request('/Custom_Deck_Test.html', headers)[0], 403)


class PdfStructureTest(unittest.TestCase):
    def test_original_backs_document_without_script_can_be_exported(self):
        from card_engine import generate_backs_html
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp, 'backs.html')
            generate_backs_html({}, str(path))
            head, sheets, tail = split_document(path.read_text(encoding='utf-8'))
            self.assertEqual(len(sheets), 1)
            self.assertEqual(sheets[0].count('class="card-slot"'), 9)
            self.assertIn('.card-back', head)
            self.assertEqual(tail, '</body></html>')

    def test_transient_browser_launch_failure_gets_one_retry(self):
        from playwright.sync_api import Error
        from pdf_export import _render_batch
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp,'deck.html')
            source.write_text('<html><body><div class="page">test</div><script></script></body></html>',encoding='utf-8')
            with patch('playwright.sync_api.sync_playwright') as factory:
                driver=factory.return_value.__enter__.return_value
                driver.chromium.launch.side_effect=Error('temporary startup failure')
                with self.assertRaises(Error):_render_batch({'document':str(source),'pdf':str(Path(temp,'deck.pdf')),'first_sheet':1})
                self.assertEqual(driver.chromium.launch.call_count,2)

    def test_export_snapshots_inputs_before_background_worker_starts(self):
        import pdf_export
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'Custom_Deck_Cards.html'
            source.write_text('original deck',encoding='utf-8')
            with patch.object(pdf_export,'ROOT',root),patch.object(pdf_export,'JOBS',root/'.pdf-jobs'),patch.object(pdf_export.subprocess,'Popen',return_value=Mock(pid=999999)):
                identifier=pdf_export.start_export('Cards')
            source.write_text('replacement deck',encoding='utf-8')
            job=json.loads((root/'.pdf-jobs'/identifier/'job.json').read_text(encoding='utf-8'))
            self.assertEqual(Path(job['files'][0]).read_text(encoding='utf-8'),'original deck')

    def test_text_verification_rejects_missing_content(self):
        from test_compact_pdf import text_pdf
        from pdf_layout import text_signature
        from pypdf import PdfReader
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp,'sample.pdf');text_pdf(path,'Source content')
            page=PdfReader(path).pages[0]
            record={'sheet':1,'text_signature':text_signature('Source content')}
            _verify_page(page,record)
            self.assertIn('pdf_content_sha256',record)
            record['text_signature']=text_signature('Missing content')
            with self.assertRaises(ValueError):_verify_page(page,record)

    def test_batches_preserve_sheet_order_and_ignore_navigation(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp, 'Custom_Deck_Cards.html')
            sheets = ['<div class="page">sheet-%03d</div>' % i for i in range(43)]
            path.write_text('<html><head></head><body>' + ''.join(sheets) + '<script>ready=true</script></body></html>', encoding='utf-8')
            manifest = write_batches(path)
            self.assertEqual(manifest['sheet_count'], 43)
            combined = []
            for name in manifest['files']:
                _, batch, _ = split_document(Path(temp, name).read_text(encoding='utf-8'))
                self.assertLessEqual(len(batch), 20); combined.extend(batch)
            self.assertEqual(combined, sheets)

    def test_native_print_batches_preserve_text_and_order(self):
        from test_compact_pdf import text_pdf
        from pdf_layout import text_signature
        from pypdf import PdfReader
        with tempfile.TemporaryDirectory() as temp:
            paths=[Path(temp,'a.pdf'),Path(temp,'b.pdf')]
            records=[]
            for index,(path,text) in enumerate(zip(paths,['First','Second'])):
                text_pdf(path,text)
                records.append({'sheet':index+1,'text_signature':text_signature(text)})
            output=Path(temp,'merged.pdf')
            self.assertEqual(_merge_parts(paths,output),2)
            batches=write_pdf_batches(output,records,batch_size=1)
            self.assertEqual([(b['first_sheet'],b['last_sheet']) for b in batches],[(1,1),(2,2)])
            for batch,expected in zip(batches,['First','Second']):
                self.assertEqual(PdfReader(Path(temp,Path(batch['download']).name)).pages[0].extract_text(),expected)


if __name__ == '__main__': unittest.main()
