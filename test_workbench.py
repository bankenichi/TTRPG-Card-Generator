"""Exercise selection contracts and the bounded viewer in an actual JS engine."""
import json
from pathlib import Path
import tempfile
import unittest

from deck_output import split_document, write_batches
from workbench_ui import render_workbench, render_viewer, render_setup, render_installer

ROOT = Path(__file__).resolve().parent


class WorkbenchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.driver = sync_playwright().start()
        cls.browser = cls.driver.chromium.launch(channel='chromium', headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.driver.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 1280, 'height': 900})
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.catalog = {'Items': {'file': 'items.json', 'playtestFile': ['pt.json'],
                                 'filters': {'rarity': ['common', 'rare'], 'playtest': ['Official', 'Playtest']}},
                        'Skills': {'file': 'skills.json', 'filters': {'ability': ['str', 'dex']}}}
        self.html = render_workbench(json.dumps(self.catalog), json.dumps({
            'backgrounds': ['parchment-background.svg'], 'watermarks': ['watermark-emblem.svg'], 'cardBacks': ['card-back.svg']}))
        self.context.route('**/*', self.route)

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])

    def route(self, route):
        from urllib.parse import urlsplit
        path = urlsplit(route.request.url).path
        if path == '/':
            route.fulfill(body=self.html, content_type='text/html')
        elif path.startswith(('/icons/', '/fonts/')) and (ROOT / path[1:]).is_file():
            route.fulfill(path=str(ROOT / path[1:]))
        elif path.endswith('.html'):
            route.fulfill(body='<html><body style="margin:0"><p>Original sheet</p></body></html>', content_type='text/html')
        else:
            route.fulfill(status=404, body='Not found')

    def open(self):
        self.page.goto('http://127.0.0.1:51999/')

    def payload(self):
        return self.page.evaluate('WorkbenchTools.buildPayload()')

    def test_empty_filters_keep_both_origins_and_all_selection_is_unrestricted(self):
        self.open()
        self.page.get_by_role('checkbox', name='Include Items in deck', exact=True).check()
        self.assertEqual(self.payload()['datasets'], [
            {'name': 'Items', 'file': 'items.json', 'filters': {}},
            {'name': 'Items', 'file': ['pt.json'], 'filters': {}}])
        self.page.locator('[data-filter-key="rarity"]').first.check()
        self.assertEqual(self.payload()['datasets'][0]['filters'], {'rarity': ['common']})
        self.page.locator('[data-filter-key="rarity"]').last.check()
        self.assertEqual(self.payload()['datasets'][0]['filters'], {})
        self.page.get_by_role('checkbox', name='Playtest', exact=True).check()
        self.assertEqual(self.payload()['datasets'], [{'name': 'Items', 'file': ['pt.json'], 'filters': {}}])
        self.page.get_by_role('checkbox', name='Official', exact=True).check()
        self.assertEqual(len(self.payload()['datasets']), 2)

    def test_restore_reset_and_custom_artwork_payloads(self):
        self.open()
        self.page.get_by_role('checkbox', name='Include Skills in deck', exact=True).check()
        self.page.reload()
        self.assertEqual(self.payload()['datasets'][0]['name'], 'Skills')
        self.page.get_by_role('tab', name='Appearance', exact=True).click()
        self.page.locator('#upload-background').set_input_files({'name': 'custom.svg', 'mimeType': 'image/svg+xml',
            'buffer': b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80"><circle r="3"/></svg>'})
        self.page.wait_for_function('!!WorkbenchTools.buildPayload().customAssets.background')
        self.assertTrue(self.payload()['customAssets']['background'].startswith('data:image/svg+xml;base64,'))
        self.assertEqual(self.page.evaluate("WorkbenchTools.buildPayload('Backs').customAssets"), {})
        self.page.get_by_role('button', name='Reset deck', exact=True).click()
        self.assertEqual(self.payload()['datasets'], [])
        self.assertTrue(self.page.locator('#generateBtn').is_disabled())

    def test_templates_phone_layout_and_keyboard_tabs(self):
        self.open()
        self.page.get_by_role('tab', name='Content', exact=True).focus()
        self.page.keyboard.press('ArrowRight')
        self.assertEqual(self.page.locator('#appearance-tab').get_attribute('aria-selected'), 'true')
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.assertFalse(self.page.evaluate('document.documentElement.scrollWidth > innerWidth'))
        self.page.get_by_role('tab', name='Content', exact=True).click()
        self.assertFalse(self.page.evaluate('document.documentElement.scrollWidth > innerWidth'))
        for html in (render_setup(False), render_setup(True, in_generator=True), render_installer()):
            self.html = html
            self.page.reload()
            self.assertNotIn('__BOOTSTRAP__', self.page.content())
            self.assertFalse(self.page.evaluate('document.documentElement.scrollWidth > innerWidth'))

    def test_viewer_bounds_live_frames_and_keeps_full_deck_navigation(self):
        self.html = render_viewer({'files': [f'Custom_Deck_Cards_sheet_{i:04d}.html' for i in range(1,266)],
                                  'sheet_count':265, 'kind':'Cards', 'platform':'desktop'})
        self.open()
        self.page.wait_for_selector('.sheet-frame')
        self.assertEqual(self.page.locator('.sheet-placeholder').count(), 265)
        self.assertLessEqual(self.page.locator('iframe').count(), 4)
        self.page.locator('#jump-sheet').fill('265')
        self.page.locator('#jump-sheet').press('Enter')
        self.page.locator('#jump-sheet').blur()
        self.page.wait_for_selector('#sheet-265 iframe')
        self.assertLessEqual(self.page.locator('iframe').count(), 4)
        self.assertEqual(self.page.locator('#sheet-265 iframe').evaluate('(el)=>[el.offsetWidth,el.offsetHeight]'), [856,1096])
        self.page.set_viewport_size({'width':390, 'height':844})
        self.page.wait_for_function('document.documentElement.scrollWidth === innerWidth')
        self.assertFalse(self.page.evaluate('document.documentElement.scrollWidth > innerWidth'))

    def test_sheet_packaging_preserves_every_original_byte_of_each_document(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, 'Custom_Deck_Cards.html')
            head = '<html><head><style>body{padding:20px}</style></head><body>'
            sheets = ['<div class="page"><b>Sheet %s</b></div>\n' % i for i in range(43)]
            tail = '<script>window.onload=()=>{originalFit();}</script></body></html>'
            path.write_text(head + ''.join(sheets) + tail, encoding='utf-8')
            manifest = write_batches(path)
            self.assertEqual(len(manifest['files']), 43)
            for name, sheet in zip(manifest['files'], sheets):
                self.assertEqual(Path(folder, name).read_text(encoding='utf-8'), head + sheet + tail)
            self.assertIn('window.DECK_VIEWER=', path.read_text(encoding='utf-8'))
            self.assertNotIn('Previous batch', path.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
