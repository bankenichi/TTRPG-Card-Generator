"""The approved icon refresh must not change resolver rules or card geometry."""
import ast
import json
from pathlib import Path
import subprocess
import unittest
import xml.etree.ElementTree as ET

import icons

ROOT = Path(__file__).resolve().parent


class IconContractTest(unittest.TestCase):
    def test_all_mapped_icons_exist_and_are_safe_monochrome_geometry(self):
        catalog = json.loads((ROOT / 'icon_catalog.json').read_text())
        self.assertTrue(set(icons.ICON_MAP.values()) <= set(catalog))
        allowed = {'svg', 'path', 'circle', 'line', 'polyline', 'polygon', 'rect', 'ellipse', 'g'}
        for name in catalog:
            with self.subTest(icon=name):
                svg = ET.fromstring((ROOT / 'icons' / (name + '.svg')).read_text())
                self.assertEqual(svg.attrib['viewBox'], '0 0 80 80')
                self.assertEqual((svg.attrib['width'], svg.attrib['height']), ('80','80'))
                for node in svg.iter():
                    self.assertIn(node.tag.split('}')[-1], allowed)
                    self.assertFalse(any(key.lower().startswith('on') or key.endswith('href') for key in node.attrib))
                    self.assertNotIn('filter', node.attrib)
                    for key in ('fill', 'stroke'):
                        if key in node.attrib:
                            self.assertIn(node.attrib[key], ('none', 'black', '#5a4a2f'))

    def test_existing_mapping_entries_and_resolver_precedence_are_unchanged(self):
        original = ast.parse(subprocess.check_output(['git', 'show', 'HEAD:icons.py'], cwd=ROOT).decode())
        current = ast.parse((ROOT / 'icons.py').read_text())
        old_map = next(ast.literal_eval(node.value) for node in original.body
                       if isinstance(node, ast.Assign) and any(getattr(t, 'id', None)=='ICON_MAP' for t in node.targets))
        self.assertTrue(all(icons.ICON_MAP[key] == value for key,value in old_map.items()))
        old_resolver = next(node for node in original.body if isinstance(node, ast.FunctionDef) and node.name=='resolve_card_icon_name')
        new_resolver = next(node for node in current.body if isinstance(node, ast.FunctionDef) and node.name=='resolve_card_icon_name')
        self.assertEqual(ast.dump(old_resolver), ast.dump(new_resolver))

    def test_classes_only_changes_stroke_weights(self):
        old = ET.fromstring(subprocess.check_output(['git', 'show', 'HEAD:icons/classes.svg'], cwd=ROOT))
        new = ET.fromstring((ROOT / 'icons/classes.svg').read_text())
        def shape(root):
            return [(node.tag, {k:v for k,v in node.attrib.items() if k!='stroke-width'}) for node in root.iter()]
        self.assertEqual(shape(old), shape(new))

    def test_user_retained_originals_are_exact_original_svg_documents(self):
        originals = ('barbarian','bard','bestiary','classes','druid','feats',
                     'psionics','races','rogue','skills','warlock')
        for name in originals:
            with self.subTest(icon=name):
                original = subprocess.check_output(['git','show','HEAD:icons/'+name+'.svg'], cwd=ROOT)
                self.assertEqual((ROOT/'icons'/(name+'.svg')).read_bytes(), original)

    def test_new_coverage_and_existing_priority(self):
        for dtype, target in {'monster':'bestiary','card':'decks','diseases':'conditions-diseases',
                              'vehicleUpgrade':'vehicle-upgrades','optionalfeature':'optionalfeatures',
                              'supernatural gifts':'supernatural-gifts'}.items():
            self.assertEqual(icons.resolve_card_icon_name({'_data_type':dtype}, 'test.json'), target)
        for name in ('Psion', 'Mystic', 'Sidekick'):
            self.assertEqual(icons.resolve_card_icon_name({'_data_type':'class','name':name}, 'class.json'),name.lower())
        self.assertEqual(icons.resolve_card_icon_name({'_data_type':'monster','meta_left':'Maneuver'}, 'test.json'), 'maneuvers')
        self.assertEqual(icons.resolve_card_icon_name({'_data_type':'class','name':'Wizard','meta_left':'Maneuver'}, 'test.json'), 'wizard')

    def test_non_type_artwork_is_unchanged(self):
        for path in (ROOT/'icons').glob('*.svg'):
            if path.stem.startswith(('card-back','parchment-background','watermark-emblem')) or path.stem in ('ornamental-divider','favicon'):
                old = subprocess.check_output(['git','show','HEAD:icons/'+path.name], cwd=ROOT).decode().replace('\r\n','\n')
                self.assertEqual(path.read_text(encoding='utf-8').replace('\r\n','\n'), old, path.name)


if __name__ == '__main__':
    unittest.main()
